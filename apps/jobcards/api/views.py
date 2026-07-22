from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils.parser_utils import (
    clean_text,
    decimal_or_zero,
    generate_mobile_job_no,
    int_or_zero,
    parse_mobile_date,
    parse_mobile_datetime,
)
from apps.jobcards.api.payloads import (
    mobile_jobcard_action_payload,
    mobile_jobcard_payload,
    save_mobile_signature_data,
)
from apps.jobcards.constants import VEHICLE_CONDITION_PHOTO_CAPTIONS
from apps.jobcards.services.access import dashboard_querysets_for_user
from core.models import (
    Claim,
    ClaimStageCode,
    Employee,
    JobCard,
    JobCardInventory,
    JobCardLabour,
    JobCardPart,
    JobCardTyreInventory,
    JobCardVehicleConditionPhoto,
)
from core.numbering import branch_for_claim, branch_for_user


def get_optional(model, pk):
    if not pk:
        return None
    return model.objects.filter(pk=pk).first()


class MobileJobcardListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _, jobcards = dashboard_querysets_for_user(request.user)

        queue = (request.GET.get("queue") or "").strip().lower()
        repair_status = (request.GET.get("repair_status") or "").strip()
        search = (request.GET.get("q") or "").strip()

        # ---------------------------------------
        # Queue Filters
        # ---------------------------------------

        if queue == "allocation":
            jobcards = jobcards.filter(claim__isnull=False).filter(
                claim__claim_stage__gte=ClaimStageCode.WORK_ALLOCATION
            )

        elif queue == "repair":
            jobcards = jobcards.filter(
                allocation__isnull=False,
                allocation__progress__start_time__isnull=False,
                claim__claim_stage__gte=ClaimStageCode.REPAIR_IN_PROGRESS,
            ).distinct()

        elif queue == "qc":
            jobcards = jobcards.filter(
                qc_done=False,
                repair_status="Completed",
            )

        elif queue == "delivery":
            jobcards = jobcards.filter(
                ready_for_delivery=True,
            )

        # ---------------------------------------
        # Normal Status Filter
        # ---------------------------------------

        elif repair_status and repair_status.lower() != "all":
            jobcards = jobcards.filter(
                repair_status=repair_status
            )

        # ---------------------------------------
        # Search
        # ---------------------------------------

        if search:
            jobcards = jobcards.filter(
                Q(job_no__icontains=search)
                | Q(claim__claim_no__icontains=search)
                | Q(claim__vehicle__registration_no__icontains=search)
                | Q(claim__vehicle__customer__name__icontains=search)
            )

        return Response(
            {
                "jobcards": [
                    mobile_jobcard_payload(job, request)
                    for job in (
                        jobcards
                        .select_related(
                            "claim",
                            "claim__vehicle",
                            "claim__vehicle__customer",
                            "advisor",
                            "branch",
                        )
                        .order_by("-id")[:100]
                    )
                ]
            }
        )

class MobileJobcardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _, jobcards = dashboard_querysets_for_user(request.user)
        job = (
            jobcards.select_related("claim", "claim__vehicle", "claim__vehicle__customer", "advisor")
            .prefetch_related("parts", "labours", "vehicle_condition_photos")
            .filter(pk=pk)
            .first()
        )
        if not job:
            return Response({"detail": "Jobcard not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"jobcard": mobile_jobcard_payload(job, request),})

class MobileNextJobNoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claim = get_optional(Claim, request.GET.get("claim") or request.GET.get("claimId"))
        branch = branch_for_claim(claim) if claim else branch_for_user(request.user)
        return Response({"job_no": generate_mobile_job_no(branch)})

class MobileJobcardSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        data = request.data or {}
        errors = {}

        job = JobCard.objects.filter(pk=pk).first() if pk else None
        if pk and not job:
            return Response({"detail": "Jobcard not found."}, status=status.HTTP_404_NOT_FOUND)

        claim_id = data.get("claim") or data.get("claimId")
        claim = get_optional(Claim, claim_id) if claim_id else (job.claim if job else None)
        if not claim:
            errors["claim"] = "Select Claim."

        if claim and not job and JobCard.objects.filter(claim=claim).exists():
            errors["claim"] = "Jobcard already exists for this claim."
        if claim and job and JobCard.objects.filter(claim=claim).exclude(pk=job.pk).exists():
            errors["claim"] = "Jobcard already exists for this claim."

        advisor = get_optional(Employee, data.get("advisor"))
        if not advisor and claim and claim.employee_id:
            advisor = claim.employee
        if not advisor:
            errors["advisor"] = "Select Advisor."

        job_no = clean_text(data.get("jobNo")) or (
            job.job_no if job else generate_mobile_job_no(branch_for_claim(claim))
        )
        duplicate_no = JobCard.objects.filter(job_no__iexact=job_no)
        if job:
            duplicate_no = duplicate_no.exclude(pk=job.pk)
        if duplicate_no.exists():
            errors["jobNo"] = "Job No already exists."

        vehicle_inward_type = clean_text(data.get("vehicleInwardType")) or "Walk-in"
        if vehicle_inward_type not in dict(JobCard.INWARD_TYPE_CHOICES):
            errors["vehicleInwardType"] = "Select valid inward type."

        repair_status_value = clean_text(data.get("repairStatus")) or "Open"
        repair_statuses = dict(JobCard._meta.get_field("repair_status").choices)
        if repair_status_value not in repair_statuses:
            errors["repairStatus"] = "Select valid repair status."

        second_approval_status = clean_text(data.get("secondApprovalStatus"))
        approval_statuses = dict(JobCard._meta.get_field("second_approval_status").choices)
        if second_approval_status and second_approval_status not in approval_statuses:
            errors["secondApprovalStatus"] = "Select valid second approval status."

        gate_in_datetime = parse_mobile_datetime(data.get("gateInDateTime"))
        if not gate_in_datetime:
            errors["gateInDateTime"] = "Gate In Date & Time is required."
        elif gate_in_datetime.date() > timezone.localdate():
            errors["gateInDateTime"] = "Gate In Date & Time cannot be a future date."

        km_value = int_or_zero(data.get("km"))
        if km_value <= 0:
            errors["km"] = "Enter valid Current KM."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if not job:
                job = JobCard(claim=claim)

            job.claim = claim
            job.job_no = job_no
            job.advisor = advisor
            job.vehicle_inward_type = vehicle_inward_type
            job.vehicle_inward_by = clean_text(data.get("vehicleInwardBy"))
            job.gate_in_datetime = gate_in_datetime
            job.expected_delivery_datetime = parse_mobile_datetime(data.get("expectedDeliveryDateTime"))
            job.km = km_value
            if "fuelLevel" in data:
                job.fuel_level = clean_text(data.get("fuelLevel"))
            job.part_order_date = parse_mobile_date(data.get("partOrderDate"))
            job.part_order_no = clean_text(data.get("partOrderNo"))
            job.repair_status = repair_status_value
            if "estimatedDelivery" in data:
                job.estimated_delivery = parse_mobile_datetime(data.get("estimatedDelivery"))
            if "actualDelivery" in data:
                job.actual_delivery = parse_mobile_datetime(data.get("actualDelivery"))
            job.repair_instructions = clean_text(data.get("repairInstructions"))
            job.qc_done = bool(data.get("qcDone"))
            job.reinspection_done = bool(data.get("reinspectionDone"))
            job.reinspection_date = parse_mobile_datetime(data.get("reinspectionDate"))
            job.reinspection_done_by = clean_text(data.get("reinspectionDoneBy"))
            job.road_test_done = bool(data.get("roadTestDone"))
            job.washing_done = bool(data.get("washingDone"))
            job.ready_for_delivery = bool(data.get("readyForDelivery"))
            job.additional_approval_required = bool(data.get("additionalApprovalRequired"))
            job.second_approval_status = second_approval_status
            job.additional_approval_reason = clean_text(data.get("additionalApprovalReason"))
            signature_changed = False
            signature_changed = save_mobile_signature_data(
                job,
                "customer_signature",
                data.get("customerSignatureData"),
            ) or signature_changed
            signature_changed = save_mobile_signature_data(
                job,
                "advisor_signature",
                data.get("advisorSignatureData"),
            ) or signature_changed
            job.save()

            if "parts" in data:
                JobCardPart.objects.filter(job=job).delete()
                parts_total = Decimal("0")
                for part in data.get("parts") or []:
                    part_no = clean_text(part.get("partNo") or part.get("part_no"))
                    description = clean_text(part.get("description"))
                    qty = int(clean_text(part.get("qty")) or "0")
                    rate = decimal_or_zero(part.get("rate"))
                    if not part_no and not description:
                        continue
                    line = JobCardPart.objects.create(
                        job=job,
                        part_no=part_no or "-",
                        description=description or "-",
                        qty=qty or 1,
                        rate=rate,
                        amount=Decimal("0"),
                    )
                    parts_total += line.amount
            else:
                parts_total = decimal_or_zero(data.get("partsTotal"))

            if "labours" in data:
                JobCardLabour.objects.filter(job=job).delete()
                labour_total = Decimal("0")
                for labour in data.get("labours") or []:
                    job_code = clean_text(labour.get("jobCode") or labour.get("job_code"))
                    description = clean_text(labour.get("description"))
                    hrs = decimal_or_zero(labour.get("labourHrs") or labour.get("labour_hrs"))
                    rate = decimal_or_zero(labour.get("rate"))
                    panel_type = clean_text(labour.get("paintPanelType") or labour.get("paint_panel_type"))
                    if panel_type not in ["New", "Repair"]:
                        panel_type = ""
                    if not job_code and not description:
                        continue
                    line = JobCardLabour.objects.create(
                        job=job,
                        job_code=job_code or "-",
                        description=description or "-",
                        labour_hrs=hrs,
                        rate=rate,
                        amount=Decimal("0"),
                        paint_panel_type=panel_type,
                    )
                    labour_total += line.amount
            else:
                labour_total = decimal_or_zero(data.get("labourTotal"))

            job.parts_total = parts_total
            job.labour_total = labour_total
            job.grand_total = parts_total + labour_total
            job.save(update_fields=["parts_total", "labour_total", "grand_total"])

            inventory = data.get("inventory") or {}
            damage_marks = inventory.get("damageMarks")
            if not isinstance(damage_marks, list):
                damage_marks = []
            JobCardInventory.objects.update_or_create(
                job=job,
                defaults={
                    "mud_flap_count": int_or_zero(inventory.get("mudFlapCount")),
                    "floor_mat_count": int_or_zero(inventory.get("floorMatCount")),
                    "lh_mirror": bool(inventory.get("lhMirror")),
                    "rh_mirror": bool(inventory.get("rhMirror")),
                    "center_mirror": bool(inventory.get("centerMirror")),
                    "frt_wiper": bool(inventory.get("frontWiper")),
                    "rr_wiper": bool(inventory.get("rearWiper")),
                    "accessories": bool(inventory.get("accessories")),
                    "spare_wheel": bool(inventory.get("spareWheel")),
                    "jack": bool(inventory.get("jack")),
                    "tool_kit": bool(inventory.get("toolKit")),
                    "stereo": bool(inventory.get("stereo")),
                    "battery": bool(inventory.get("battery")),
                    "number_plate": bool(inventory.get("numberPlate")),
                    "fuel_percent": int_or_zero(inventory.get("fuelPercent")),
                    "cng_percent": int_or_zero(inventory.get("cngPercent")),
                    "damage_marks": damage_marks,
                    "remarks": clean_text(inventory.get("remarks")),
                },
            )

            for tyre in data.get("tyres") or []:
                position = clean_text(tyre.get("position"))
                if position not in dict(JobCardTyreInventory.POSITION_CHOICES):
                    continue
                JobCardTyreInventory.objects.update_or_create(
                    job=job,
                    position=position,
                    defaults={
                        "make": clean_text(tyre.get("make")),
                        "size": clean_text(tyre.get("size")),
                        "depth": decimal_or_zero(tyre.get("depth")) if clean_text(tyre.get("depth")) else None,
                        "wheel_cap": clean_text(tyre.get("wheelCap")) or "N",
                    },
                )

            if claim.employee_id and claim.claim_stage < ClaimStageCode.INTIMATION:
                claim.claim_stage = ClaimStageCode.INTIMATION
                claim.save(update_fields=["claim_stage"])

        return Response(
            {
                "message": "Jobcard saved successfully.",
                "jobcard": mobile_jobcard_payload(
    request,
    JobCard.objects.prefetch_related(
        "parts",
        "labours",
        "vehicle_condition_photos"
    ).get(pk=job.pk),
),
            }
        )

class MobileJobcardSignatureSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        _, jobcards = dashboard_querysets_for_user(request.user)
        job = jobcards.filter(pk=pk).first()
        if not job:
            return Response({"detail": "Jobcard not found."}, status=status.HTTP_404_NOT_FOUND)

        signature_changed = False
        signature_changed = save_mobile_signature_data(
            job,
            "customer_signature",
            request.data.get("customerSignatureData"),
        ) or signature_changed
        signature_changed = save_mobile_signature_data(
            job,
            "advisor_signature",
            request.data.get("advisorSignatureData"),
        ) or signature_changed

        if signature_changed:
            job.save()

        return Response(
            {
                "message": "Signatures saved successfully.",
                "jobcard": mobile_jobcard_payload(
    request,
    JobCard.objects.prefetch_related(
        "parts",
        "labours",
        "vehicle_condition_photos"
    ).get(pk=job.pk),
),
                "actions": mobile_jobcard_action_payload(request, job),
            }
        )

class MobileJobcardActionLinksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _, jobcards = dashboard_querysets_for_user(request.user)
        job = jobcards.select_related("claim", "claim__vehicle", "claim__vehicle__customer").filter(pk=pk).first()
        if not job:
            return Response({"detail": "Jobcard not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"actions": mobile_jobcard_action_payload(request, job)})

class MobileJobcardVehiclePhotoUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    def post(self, request, pk):
        _, jobcards = dashboard_querysets_for_user(request.user)
        job = jobcards.filter(pk=pk).first()
        if not job:
            return Response({"detail": "Jobcard not found."}, status=status.HTTP_404_NOT_FOUND)

        image = request.FILES.get("vehicle_condition_photo")
        if not image:
            return Response({"errors": {"photo": "Capture or select a photo."}}, status=status.HTTP_400_BAD_REQUEST)

        caption = clean_text(request.data.get("caption"))
        index = int_or_zero(request.data.get("index"))
        if not caption and 1 <= index <= len(VEHICLE_CONDITION_PHOTO_CAPTIONS):
            caption = VEHICLE_CONDITION_PHOTO_CAPTIONS[index - 1]
        if caption not in VEHICLE_CONDITION_PHOTO_CAPTIONS:
            return Response({"errors": {"caption": "Select valid vehicle photo view."}}, status=status.HTTP_400_BAD_REQUEST)

        photo = JobCardVehicleConditionPhoto.objects.filter(job=job, caption=caption).first()
        if photo and photo.image:
            photo.image.delete(save=False)

        if photo:
            photo.image = image
            photo.save()
        else:
            photo = JobCardVehicleConditionPhoto.objects.create(
                job=job,
                caption=caption,
                image=image,
            )

        return Response(
            {
                "message": f"{caption} photo uploaded.",
                "photo": {
                    "id": photo.id,
                    "caption": photo.caption,
                    "url": photo.image.url if photo.image else "",
                    "uploaded_at": photo.uploaded_at.isoformat(sep=" ", timespec="minutes"),
                },
            }
        )
