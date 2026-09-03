from decimal import Decimal
import json

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
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
from apps.accounts.services.user_context import branch_filter_queryset
from core.models import (
    Claim,
    ClaimStageCode,
    Employee,
    JobCard,
    JobCardType,
    JobCardInventory,
    JobCardLabour,
    JobCardPart,
    JobCardTyreInventory,
    JobCardVehicleConditionPhoto,
    GateInEntry,
    JobCardPhotoAnnotation,
    Vehicle,
)
from core.numbering import branch_for_claim, branch_for_user
from core.views import send_jobcard_whatsapp, jobcard_tracking_url


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
                claim__claim_stage=ClaimStageCode.WORK_ALLOCATION
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
        created_job = job is None
        if pk and not job:
            return Response({"detail": "Jobcard not found."}, status=status.HTTP_404_NOT_FOUND)

        claim_id = data.get("claim") or data.get("claimId")

        if claim_id and str(claim_id) != "0":
            claim = get_optional(Claim, claim_id)
        else:
            claim = None

        # A direct mobile Job Card must start from an unused Gate In entry in
        # the current user's branch. Claim-linked cards retain their claim
        # vehicle and existing Gate In workflow.
        direct_vehicle = None
        direct_gate_entry = None
        if not claim and not job:
            vehicle_id = data.get("vehicleId") or data.get("vehicle_id")
            direct_vehicle = get_optional(Vehicle, vehicle_id)
            if not direct_vehicle:
                errors["vehicleId"] = "Select a vehicle from pending Gate In entries."
            else:
                direct_gate_entry = branch_filter_queryset(
                    GateInEntry.objects.filter(
                        vehicle=direct_vehicle,
                        status="Pending",
                        jobcard__isnull=True,
                    ),
                    request.user,
                ).order_by("-gate_in_datetime").first()
                if not direct_gate_entry:
                    errors["vehicleId"] = "Vehicle must have a pending Gate In entry for this branch."

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
        # The pending Gate In record is authoritative for a direct mobile
        # Job Card. Use it when the client did not copy the date/KM into the
        # form (for example after a rotation or screen recreation).
        if direct_gate_entry:
            gate_in_datetime = gate_in_datetime or direct_gate_entry.gate_in_datetime
        if not gate_in_datetime:
            errors["gateInDateTime"] = "Gate In Date & Time is required."
        elif gate_in_datetime.date() > timezone.localdate():
            errors["gateInDateTime"] = "Gate In Date & Time cannot be a future date."

        km_value = int_or_zero(data.get("km"))
        if direct_gate_entry and km_value <= 0:
            km_value = direct_gate_entry.current_km
        if km_value <= 0:
            errors["km"] = "Enter valid Current KM."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if not job:
                job = JobCard(claim=claim)

            job.claim = claim
            if direct_vehicle is not None:
                job.vehicle = direct_vehicle
                job.branch = direct_gate_entry.branch if direct_gate_entry and direct_gate_entry.branch_id else branch_for_user(request.user)
            jobcard_type_id = data.get("jobCardType") or data.get("jobcard_type")

            if not jobcard_type_id:
                errors["jobCardType"] = "Select Job Type."
            else:
                try:
                    jobcard_type_id = int(jobcard_type_id)
                except (TypeError, ValueError):
                    jobcard_type_id = None

                if not jobcard_type_id:
                    errors["jobCardType"] = "Select valid Job Type."
                else:
                    jobcard_type = JobCardType.objects.filter(
                        pk=jobcard_type_id,
                        is_active=True,
                    ).first()

                    if not jobcard_type:
                        errors["jobCardType"] = "Select valid Job Type."
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
            job.jobcard_type_id = jobcard_type_id
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

            # Link the mobile-created Job Card to its pending Gate-In entry so
            # the Gate-In register shows Converted status and the Job Card No.
            linked_vehicle = job.vehicle or (claim.vehicle if claim and claim.vehicle_id else None)
            if linked_vehicle:
                gate_entry_query = GateInEntry.objects.select_for_update().filter(
                    Q(vehicle=linked_vehicle) | Q(registration_no__iexact=linked_vehicle.registration_no),
                    status="Pending",
                    jobcard__isnull=True,
                )
                if direct_gate_entry is not None:
                    gate_entry_query = gate_entry_query.filter(pk=direct_gate_entry.pk)
                gate_entry = gate_entry_query.order_by("-gate_in_datetime").first()
                if gate_entry:
                    gate_entry.jobcard = job
                    gate_entry.status = "Converted"
                    gate_entry.save(update_fields=["jobcard", "status", "updated_at"])

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



        if created_job:
            # WhatsApp delivery is best-effort; saving the Job Card must not
            # fail when Meta credentials or customer contact details are absent.
            try:
                send_jobcard_whatsapp(job)
            except Exception:
                pass

        return Response(
            {
                "message": "Jobcard saved successfully.",
                "tracking_url": jobcard_tracking_url(job),
                "jobcard": mobile_jobcard_payload(
    JobCard.objects.prefetch_related(
        "parts",
        "labours",
        "vehicle_condition_photos"
    ).get(pk=job.pk),
    request,
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
    JobCard.objects.prefetch_related(
        "parts",
        "labours",
        "vehicle_condition_photos"
    ).get(pk=job.pk),
    request,
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
class MobileJobcardPhotoAnnotationSaveView(APIView):
    """
    Save manual annotations for one vehicle-condition photo.

    Supported:
        circle
        rectangle
        arrow
        text

    Coordinates are normalized:
        0.0 -> 1.0
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, job_id, photo_id):

        # ---------------------------------------------------------
        # Verify the jobcard belongs to the current user's scope
        # ---------------------------------------------------------

        _, jobcards = dashboard_querysets_for_user(request.user)

        job = jobcards.filter(
            pk=job_id
        ).first()

        if not job:
            return Response(
                {
                    "detail": "Jobcard not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------------------------------------
        # Find the photo AND make sure it belongs to this JobCard
        # ---------------------------------------------------------

        photo = (
            JobCardVehicleConditionPhoto.objects
            .filter(
                pk=photo_id,
                job=job,
            )
            .first()
        )

        if not photo:
            return Response(
                {
                    "detail": "Vehicle condition photo not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ---------------------------------------------------------
        # Read annotations
        # ---------------------------------------------------------

        annotations = request.data.get("annotations")

        if annotations is None:
            annotations = []

        if not isinstance(annotations, list):
            return Response(
                {
                    "errors": {
                        "annotations": (
                            "annotations must be a list."
                        )
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_types = {
            "circle",
            "rectangle",
            "arrow",
            "text",
        }

        validated = []

        # ---------------------------------------------------------
        # Validate each annotation
        # ---------------------------------------------------------

        for index, item in enumerate(annotations):

            if not isinstance(item, dict):
                return Response(
                    {
                        "errors": {
                            "annotations": (
                                f"Annotation {index + 1} "
                                "must be an object."
                            )
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            annotation_type = clean_text(
                item.get("type")
            ).lower()

            if annotation_type not in allowed_types:
                return Response(
                    {
                        "errors": {
                            "annotations": (
                                f"Invalid annotation type "
                                f"'{annotation_type}'. "
                                f"Allowed: "
                                f"{', '.join(sorted(allowed_types))}."
                            )
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # -----------------------------------------------------
            # Coordinates
            # -----------------------------------------------------

            # ---------------------------------------------------------
            # Coordinates
            # Flutter sends:
            #
            # "start": {"x": 0.31, "y": 0.42}
            # "end":   {"x": 0.47, "y": 0.58}
            # ---------------------------------------------------------

            start = item.get("start") or {}
            end = item.get("end")

            if not isinstance(start, dict):
                return Response(
                    {
                        "errors": {
                            "annotations": (
                                f"Invalid start position "
                                f"for annotation {index + 1}."
                            )
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if end is not None and not isinstance(end, dict):
                return Response(
                    {
                        "errors": {
                            "annotations": (
                                f"Invalid end position "
                                f"for annotation {index + 1}."
                            )
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                start_x = float(start.get("x", 0.0))
                start_y = float(start.get("y", 0.0))

                end_x = (
                    float(end["x"])
                    if end is not None and "x" in end
                    else None
                )

                end_y = (
                    float(end["y"])
                    if end is not None and "y" in end
                    else None
                )

            except (TypeError, ValueError, KeyError):
                return Response(
                    {
                        "errors": {
                            "annotations": (
                                f"Invalid coordinates "
                                f"for annotation {index + 1}."
                            )
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # -----------------------------------------------------
            # Normalized coordinate validation
            # -----------------------------------------------------

            coordinates = [
                ("start_x", start_x),
                ("start_y", start_y),
            ]

            if end_x is not None:
                coordinates.append(
                    ("end_x", end_x)
                )

            if end_y is not None:
                coordinates.append(
                    ("end_y", end_y)
                )

            invalid_coordinate = False

            for _, value in coordinates:
                if value < 0.0 or value > 1.0:
                    invalid_coordinate = True
                    break

            if invalid_coordinate:
                return Response(
                    {
                        "errors": {
                            "annotations": (
                                f"Coordinates for annotation "
                                f"{index + 1} must be between "
                                "0.0 and 1.0."
                            )
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # -----------------------------------------------------
            # Text
            # -----------------------------------------------------

            text = clean_text(
                item.get("text")
            )

            if annotation_type == "text" and not text:
                return Response(
                    {
                        "errors": {
                            "annotations": (
                                f"Text annotation "
                                f"{index + 1} cannot be empty."
                            )
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # -----------------------------------------------------
            # Appearance
            # -----------------------------------------------------

            color = clean_text(
                item.get("color")
            ) or "#FF0000"

            try:
                stroke_width = float(
                    item.get("strokeWidth", 4.0)
                )
            except (
                    TypeError,
                    ValueError,
            ):
                stroke_width = 4.0

            try:
                font_size = float(
                    item.get("font_size", 18.0)
                )
            except (
                TypeError,
                ValueError,
            ):
                font_size = 18.0

            # -----------------------------------------------------
            # Store validated data temporarily
            # -----------------------------------------------------

            validated.append(
                {
                    "annotation_type": annotation_type,
                    "start_x": start_x,
                    "start_y": start_y,
                    "end_x": end_x,
                    "end_y": end_y,
                    "text": text,
                    "color": color,
                    "stroke_width": stroke_width,
                    "font_size": font_size,
                    "display_order": index,
                }
            )

        # ---------------------------------------------------------
        # Replace annotations for this photo
        #
        # This is intentional.
        #
        # Flutter sends the complete current drawing.
        # Therefore the database becomes an exact copy of the
        # current annotation canvas.
        # ---------------------------------------------------------

        JobCardPhotoAnnotation.objects.filter(
            photo=photo
        ).delete()

        created = []

        for item in validated:

            annotation = (
                JobCardPhotoAnnotation.objects.create(
                    photo=photo,
                    **item,
                )
            )

            created.append(
                {
                    "id": annotation.id,
                    "type": annotation.annotation_type,
                    "start_x": annotation.start_x,
                    "start_y": annotation.start_y,
                    "end_x": annotation.end_x,
                    "end_y": annotation.end_y,
                    "text": annotation.text,
                    "color": annotation.color,
                    "stroke_width": annotation.stroke_width,
                    "font_size": annotation.font_size,
                    "display_order": annotation.display_order,
                }
            )

        return Response(
            {
                "message": (
                    "Photo annotations saved successfully."
                ),
                "photo": {
                    "id": photo.id,
                    "caption": photo.caption,
                    "url": (
                        photo.image.url
                        if photo.image
                        else ""
                    ),
                },
                "annotations": created,
                "count": len(created),
            },
            status=status.HTTP_200_OK,
        )

    @require_POST
    @login_required
    def save_jobcard_photo_annotations(request, pk, photo_id):
        """
        Save custom annotations drawn on a JobCard vehicle-condition photo.

        Expected JSON:
        {
            "annotations": [
                {
                    "type": "circle",
                    "start": {"x": 0.20, "y": 0.30},
                    "end": {"x": 0.45, "y": 0.50},
                    "text": "",
                    "color": "#FF0000",
                    "strokeWidth": 4.0,
                    "fontSize": 18.0
                }
            ]
        }
        """

        job = get_object_or_404(
            JobCard,
            pk=pk,
        )

        photo = get_object_or_404(
            JobCardVehicleConditionPhoto,
            pk=photo_id,
            job=job,
        )

        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid JSON payload.",
                },
                status=400,
            )

        annotations = payload.get("annotations")

        if not isinstance(annotations, list):
            return JsonResponse(
                {
                    "success": False,
                    "error": "annotations must be a list.",
                },
                status=400,
            )

        # Replace the existing annotations for this photo.
        photo.annotations.all().delete()

        objects = []

        for index, item in enumerate(annotations):
            if not isinstance(item, dict):
                continue

            annotation_type = str(
                item.get("type", "")
            ).strip().lower()

            if annotation_type not in {
                "circle",
                "rectangle",
                "arrow",
                "text",
            }:
                continue

            start = item.get("start") or {}
            end = item.get("end")

            try:
                start_x = float(start.get("x", 0.0))
                start_y = float(start.get("y", 0.0))
            except (TypeError, ValueError):
                start_x = 0.0
                start_y = 0.0

            end_x = None
            end_y = None

            if isinstance(end, dict):
                try:
                    end_x = float(end.get("x"))
                except (TypeError, ValueError):
                    end_x = None

                try:
                    end_y = float(end.get("y"))
                except (TypeError, ValueError):
                    end_y = None

            text = str(
                item.get("text", "")
            ).strip()

            color = str(
                item.get("color", "#FF0000")
            ).strip()

            try:
                stroke_width = float(
                    item.get("strokeWidth", 4.0)
                )
            except (
                    TypeError,
                    ValueError,
            ):
                stroke_width = 4.0

            try:
                font_size = float(
                    item.get("fontSize", 18.0)
                )
            except (
                    TypeError,
                    ValueError,
            ):
                font_size = 18.0

            # Keep normalized coordinates safely inside the image.
            start_x = max(0.0, min(1.0, start_x))
            start_y = max(0.0, min(1.0, start_y))

            if end_x is not None:
                end_x = max(0.0, min(1.0, end_x))

            if end_y is not None:
                end_y = max(0.0, min(1.0, end_y))

            objects.append(
                JobCardPhotoAnnotation(
                    photo=photo,
                    annotation_type=annotation_type,
                    start_x=start_x,
                    start_y=start_y,
                    end_x=end_x,
                    end_y=end_y,
                    text=text,
                    color=color,
                    stroke_width=stroke_width,
                    font_size=font_size,
                    display_order=index,
                )
            )

        if objects:
            JobCardPhotoAnnotation.objects.bulk_create(objects)

        saved = photo.annotations.order_by(
            "display_order",
            "id",
        )

        return JsonResponse(
            {
                "success": True,
                "photo_id": photo.id,
                "annotation_count": saved.count(),
                "annotations": [
                    {
                        "id": annotation.id,
                        "type": annotation.annotation_type,
                        "start": {
                            "x": annotation.start_x,
                            "y": annotation.start_y,
                        },
                        "end": (
                            None
                            if annotation.end_x is None
                               or annotation.end_y is None
                            else {
                                "x": annotation.end_x,
                                "y": annotation.end_y,
                            }
                        ),
                        "text": annotation.text,
                        "color": annotation.color,
                        "strokeWidth": annotation.stroke_width,
                        "fontSize": annotation.font_size,
                        "displayOrder": annotation.display_order,
                    }
                    for annotation in saved
                ],
            }
        )
# core/views.py

def mobile_jobcard_types(request):
    types = JobCardType.objects.filter(
        is_active=True
    ).order_by("display_order", "name")

    return JsonResponse({
        "jobCardTypes": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description or "",
            }
            for item in types
        ]
    })
