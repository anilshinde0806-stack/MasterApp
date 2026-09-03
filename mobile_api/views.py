import base64
from urllib.parse import quote

from apps.claims.services.claim_helpers import (
    derive_claim_stage as shared_derive_claim_stage,
    mobile_claim_payload as shared_mobile_claim_payload,
)
from apps.claims.services.repair_workflow_service import (
    RepairWorkflowBlocked,
    RepairWorkflowService,
)
from apps.accounts.services.user_context import (
    branch_filter_queryset,
    employee_can_view_all_branches,
    user_branch,
)
from apps.notifications.services.notification_service import (
    create_user_notification as mobile_create_user_notification,
    notify_jobcard_advisor as mobile_notify_jobcard_advisor,
    notify_work_progress_change as mobile_notify_work_progress_change,
)
from apps.jobcards.api.payloads import (
    mobile_employee_list,
    mobile_jobcard_payload,
    mobile_stage_list,
)
from apps.jobcards.services.access import dashboard_querysets_for_user
from apps.common.utils.parser_utils import clean_text, parse_mobile_date, generate_mobile_claim_no, parse_mobile_datetime, \
    decimal_or_zero, generate_mobile_job_no, int_or_zero
from mobile_api.utils.branch_filter import resolve_branch, filter_branch

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
    JSONParser,
)
from decimal import Decimal, InvalidOperation
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import (
    Claim,
    ClaimStageCode,
    Branch,
    Employee,
    InsuranceCompany,
    JobCard,
    JobCardInventory,
    JobCardLabour,
    JobCardPart,
    JobCardTyreInventory,
    JobCardVehicleConditionPhoto,
    GateInEntry,
    Surveyor,
    Customer,
    Vehicle,
    VehicleModel,
    VehicleVariant,
    WorkAllocation,
    WorkProgress,
    WorkProgressPhoto,
    UserNotification,
    PartOrderHeader,

)
from core.numbering import branch_for_claim, branch_for_user, next_claim_no, next_jobcard_no
from core.views import notify_reception_gate_in, notify_reception_gate_in_changed
from core.validators import VEHICLE_NUMBER_ERROR, is_valid_vehicle_number, normalize_vehicle_number
from core.whatsapp import send_advisor_assigned_whatsapp
from mobile_api.utils.branch_filter import filter_branch

from .serializers import RepairProgressPhotoSerializer






def get_optional(model, pk):
    if not pk:
        return None
    return model.objects.filter(pk=pk).first()


class MobilePartsManagerDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = Employee.objects.filter(user=request.user).first()
        from core.views import is_parts_manager

        if not request.user.is_superuser and not is_parts_manager(employee):
            return Response(
                {"detail": "Parts Manager access is required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.localdate()
        month_start = today.replace(day=1)
        headers = PartOrderHeader.objects.select_related(
            "job",
            "job__claim",
            "job__claim__vehicle",
            "job__claim__vehicle__customer",
            "vehicle",
            "vehicle__customer",
        ).prefetch_related("lines")

        if employee and employee.branch_id:
            headers = headers.filter(
                Q(job__branch_id=employee.branch_id)
                | Q(job__claim__branch_id=employee.branch_id)
                | Q(job__isnull=True)
            ).distinct()

        open_headers = headers.exclude(status__in=["Received", "Cancelled"])
        overdue_headers = open_headers.filter(expected_date__lt=today)

        def order_payload(header):
            job = header.job
            claim = job.claim if job else None
            vehicle = claim.vehicle if claim and claim.vehicle else header.vehicle
            lines = list(header.lines.all())
            ordered_qty = sum(
                (line.ordered_qty or Decimal("0")) for line in lines
            )
            received_qty = sum(
                (line.received_qty or Decimal("0")) for line in lines
            )
            progress = (
                int((received_qty / ordered_qty) * 100)
                if ordered_qty else 0
            )
            line_payload = []
            for line in lines:
                part = line.part
                line_payload.append({
                    "id": line.id,
                    "part_no": part.part_no if part else line.manual_part_no,
                    "description": (
                        part.description if part else line.manual_description
                    ),
                    "unit": "Nos",
                    "rate": str(part.rate if part else 0),
                    "ordered_qty": str(line.ordered_qty or 0),
                    "received_qty": str(line.received_qty or 0),
                    "pending_qty": str(
                        max((line.ordered_qty or 0) - (line.received_qty or 0), 0)
                    ),
                    "status": line.status,
                    "supplier": line.supplier or header.supplier or "",
                    "expected_date": (
                        line.expected_date.isoformat() if line.expected_date else None
                    ),
                })
            return {
                "id": header.id,
                "order_no": header.order_no or f"Order #{header.id}",
                "order_date": header.order_date.isoformat() if header.order_date else None,
                "expected_date": header.expected_date.isoformat() if header.expected_date else None,
                "supplier": header.supplier or "",
                "status": header.status,
                "job_id": job.id if job else None,
                "job_no": job.job_no if job else "",
                "registration_no": vehicle.registration_no if vehicle else "",
                "customer": (
                    vehicle.customer.name
                    if vehicle and vehicle.customer_id else ""
                ),
                "line_count": len(lines),
                "ordered_qty": str(ordered_qty),
                "received_qty": str(received_qty),
                "progress": min(progress, 100),
                "is_overdue": bool(
                    header.expected_date
                    and header.expected_date < today
                    and header.status not in ["Received", "Cancelled"]
                ),
                "lines": line_payload,
            }

        return Response({
            "manager_name": employee.name if employee else request.user.username,
            "as_of_date": today.isoformat(),
            "summary": {
                "open": open_headers.count(),
                "overdue": overdue_headers.count(),
                "back_order": headers.filter(status="Back Order").count(),
                "received_this_month": headers.filter(
                    status="Received",
                    updated_at__date__gte=month_start,
                    updated_at__date__lte=today,
                ).count(),
            },
            "overdue_orders": [
                order_payload(header)
                for header in overdue_headers.order_by("expected_date")[:10]
            ],
            "recent_orders": [
                order_payload(header)
                for header in headers.order_by("-updated_at")[:20]
            ],
        })













































def is_mobile_security_employee(employee):
    if not employee:
        return False

    role_text = " ".join([
        employee.employee_type or "",
        employee.designation or "",
        employee.department or "",
    ]).upper()
    return "SECURITY" in role_text or "GATE" in role_text


def mobile_gate_in_payload(entry):
    vehicle = entry.vehicle if entry.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    claim = entry.jobcard.claim if entry.jobcard_id and entry.jobcard.claim_id else None
    has_open_claim = gate_in_has_open_claim(entry)
    can_gate_out = gate_in_can_gate_out(entry)
    can_edit = entry.status == "Pending" and not has_open_claim
    return {
        "id": entry.id,
        "registration_no": entry.registration_no,
        "customer": customer.name if customer else "",
        "current_km": entry.current_km,
        "out_km": entry.out_km or "",
        "service_type": entry.service_type,
        "service_type_label": entry.get_service_type_display(),
        "gate_in_datetime": timezone.localtime(entry.gate_in_datetime).isoformat(timespec="minutes"),
        "gate_in_display": timezone.localtime(entry.gate_in_datetime).strftime("%d/%m/%Y %H:%M"),
        "branch": entry.branch_id or "",
        "branch_name": entry.branch.name if entry.branch_id else "",
        "entered_by": entry.entered_by.username if entry.entered_by_id else "",
        "status": entry.status,
        "job_no": entry.jobcard.job_no if entry.jobcard_id else "",
        "claim_no": claim.claim_no if claim else "",
        "remarks": entry.remarks or "",
        "cancellation_remark": entry.cancellation_remark or "",
        "gate_out_datetime": timezone.localtime(entry.gate_out_datetime).isoformat(timespec="minutes") if entry.gate_out_datetime else "",
        "gate_out_display": timezone.localtime(entry.gate_out_datetime).strftime("%d/%m/%Y %H:%M") if entry.gate_out_datetime else "",
        "has_open_claim": has_open_claim,
        "can_edit": can_edit,
        "can_cancel": can_edit,
        "can_gate_out": can_gate_out,
        "lock_reason": "Claim created. Gate In cannot be edited." if has_open_claim and entry.status == "Pending" else "",
    }


def gate_in_has_open_claim(entry):
    vehicle_filter = Q(vehicle=entry.vehicle) if entry.vehicle_id else Q(vehicle__registration_no__iexact=entry.registration_no)
    return Claim.objects.filter(vehicle_filter).exclude(claim_stage=ClaimStageCode.CLOSED).exclude(status="Closed").exists()


def gate_in_can_gate_out(entry):
    if entry.status != "Converted" or not entry.jobcard_id:
        return False

    job = entry.jobcard
    claim = job.claim if job.claim_id else None
    if not claim:
        return False

    claim_closed = claim.claim_stage == ClaimStageCode.CLOSED or claim.status == "Closed"
    job_closed = job.repair_status == "Closed"
    return claim_closed and job_closed


class MobileGateInEntryView(APIView):
    permission_classes = [IsAuthenticated]

    def _security_employee(self, request):
        employee = Employee.objects.filter(user=request.user).select_related("branch").first()
        if not is_mobile_security_employee(employee):
            return None
        return employee

    def _base_queryset(self, employee):
        entries = GateInEntry.objects.select_related(
            "vehicle",
            "vehicle__customer",
            "branch",
            "entered_by",
            "jobcard",
        )
        if employee and employee.branch_id:
            entries = entries.filter(Q(branch=employee.branch) | Q(branch__isnull=True))
        return entries

    def get(self, request):
        employee = self._security_employee(request)
        if not employee:
            return Response({"detail": "Gate In Entry is allowed only for Security login."}, status=status.HTTP_403_FORBIDDEN)

        status_filter = clean_text(request.GET.get("status")) or "actionable"
        service_type = clean_text(request.GET.get("service_type"))
        entries = self._base_queryset(employee).order_by("-gate_in_datetime")

        if status_filter.lower() == "actionable":
            entries = entries.filter(status__in=["Pending", "Converted"])
        elif status_filter.lower() != "all":
            entries = entries.filter(status=status_filter)
        if service_type:
            entries = entries.filter(service_type=service_type)

        return Response({
            "service_types": [
                {"id": value, "label": label}
                for value, label in GateInEntry.SERVICE_TYPE_CHOICES
            ],
            "entries": [
                mobile_gate_in_payload(entry)
                for entry in entries[:100]
            ],
        })

    def post(self, request, pk=None):
        employee = self._security_employee(request)
        if not employee:
            return Response({"detail": "Gate In Entry is allowed only for Security login."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        action = clean_text(data.get("action") or "save").lower()
        entry = None
        if pk:
            entry = self._base_queryset(employee).filter(pk=pk).first()
            if not entry:
                return Response({"detail": "Gate In entry not found."}, status=status.HTTP_404_NOT_FOUND)
            if entry.status not in ["Pending", "Converted"]:
                return Response({"errors": {"entry": f"{entry.status} Gate In entry cannot be edited."}}, status=status.HTTP_400_BAD_REQUEST)

        if action == "gate_out":
            if not entry:
                return Response({"detail": "Gate In entry not found."}, status=status.HTTP_404_NOT_FOUND)
            if not gate_in_can_gate_out(entry):
                return Response({
                    "errors": {
                        "entry": "Gate Out is allowed only after both Claim and Jobcard are closed."
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                out_km = int(request.data.get("outKm") or request.data.get("out_km") or 0)
            except (TypeError, ValueError):
                out_km = 0
            if out_km <= 0:
                return Response({"errors": {"outKm": "Enter valid Out KM."}}, status=status.HTTP_400_BAD_REQUEST)

            entry.status = "Gate Out"
            entry.out_km = out_km
            entry.gate_out_datetime = timezone.now()
            entry.gate_out_by = request.user
            entry.save(update_fields=["status", "out_km", "gate_out_datetime", "gate_out_by", "updated_at"])
            return Response({
                "message": f"Gate Out completed for {entry.registration_no}.",
                "entry": mobile_gate_in_payload(entry),
            })

        if action == "cancel":
            if not entry:
                return Response({"detail": "Gate In entry not found."}, status=status.HTTP_404_NOT_FOUND)
            if entry.status != "Pending":
                return Response({"errors": {"entry": "Only pending Gate In entry can be cancelled."}}, status=status.HTTP_400_BAD_REQUEST)
            if gate_in_has_open_claim(entry):
                return Response({"errors": {"entry": "Claim created. Gate In cannot be cancelled."}}, status=status.HTTP_400_BAD_REQUEST)
            cancellation_remark = clean_text(data.get("cancellationRemark"))
            if not cancellation_remark:
                return Response({"errors": {"cancellationRemark": "Cancel remark is required."}}, status=status.HTTP_400_BAD_REQUEST)

            entry.status = "Cancelled"
            entry.cancellation_remark = cancellation_remark
            entry.cancelled_at = timezone.now()
            entry.cancelled_by = request.user
            entry.save(update_fields=["status", "cancellation_remark", "cancelled_at", "cancelled_by", "updated_at"])
            notify_reception_gate_in_changed(entry, cancelled=True)
            return Response({
                "message": f"Gate In cancelled for {entry.registration_no}.",
                "entry": mobile_gate_in_payload(entry),
            })

        registration_no = normalize_vehicle_number(data.get("registrationNo"))
        service_type = clean_text(data.get("serviceType"))
        current_km = int_or_zero(data.get("currentKm"))
        remarks = clean_text(data.get("remarks"))

        errors = {}
        if not registration_no:
            errors["registrationNo"] = "Vehicle No is required."
        if current_km <= 0:
            errors["currentKm"] = "Enter valid Current KM."
        if service_type not in dict(GateInEntry.SERVICE_TYPE_CHOICES):
            errors["serviceType"] = "Select valid Service Type."
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        if entry and entry.status != "Pending":
            return Response({"errors": {"entry": "Only pending Gate In entry can be edited."}}, status=status.HTTP_400_BAD_REQUEST)

        if entry and gate_in_has_open_claim(entry):
            return Response({"errors": {"entry": "Claim created. Gate In cannot be edited."}}, status=status.HTTP_400_BAD_REQUEST)

        duplicate = GateInEntry.objects.filter(
            registration_no__iexact=registration_no,
            status="Pending",
        )
        if entry:
            duplicate = duplicate.exclude(pk=entry.pk)
        duplicate_entry = duplicate.first()
        if duplicate_entry:
            duplicate_time = timezone.localtime(duplicate_entry.gate_in_datetime).strftime("%d/%m/%Y %H:%M")
            return Response({
                "errors": {
                    "registrationNo": f"{registration_no} already has a pending Gate In entry from {duplicate_time}."
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        vehicle = Vehicle.objects.filter(registration_no__iexact=registration_no).first()
        created = entry is None
        if created:
            entry = GateInEntry(
                gate_in_datetime=timezone.now(),
                branch=branch_for_user(request.user),
                entered_by=request.user,
            )

        entry.registration_no = registration_no
        entry.current_km = current_km
        entry.service_type = service_type
        entry.vehicle = vehicle
        entry.remarks = remarks
        if entry.status == "Cancelled":
            entry.status = "Pending"
            entry.cancellation_remark = ""
            entry.cancelled_at = None
            entry.cancelled_by = None
        entry.save()

        if created:
            notify_reception_gate_in(entry)
            message = f"Gate In saved for {entry.registration_no}."
        else:
            notify_reception_gate_in_changed(entry, cancelled=False)
            message = f"Gate In updated for {entry.registration_no}."

        return Response({
            "message": message,
            "entry": mobile_gate_in_payload(entry),
        })








class MobileDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims, jobcards = dashboard_querysets_for_user(request.user)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        employee = Employee.objects.filter(
            user=request.user
        ).select_related("branch").first()
        month_claims = claims.filter(created_at__date__gte=month_start)
        month_jobcards = jobcards.filter(created_at__date__gte=month_start)
        vehicles_inside = jobcards.exclude(
            repair_status="Closed"
        ).count()

        delivery_today = jobcards.filter(
            expected_delivery_datetime__date=today
        ).count()

        qc_pending = jobcards.filter(
            qc_done=False,
            repair_status="Open",
        ).count()

        ready_delivery = jobcards.filter(
            ready_for_delivery=True,
            repair_status="Open",
        ).count()

        washing_pending = jobcards.filter(
            washing_done=False,
            repair_status="Open",
        ).count()

        reinspection_pending = jobcards.filter(
            reinspection_done=False,
            repair_status="Open",
        ).count()
        stage_lookup = dict(Claim.CLAIM_STAGES)
        stage_counts = [
            {
                "stage": item["claim_stage"],
                "label": stage_lookup.get(item["claim_stage"], str(item["claim_stage"])),
                "total": item["total"],
            }
            for item in claims.exclude(claim_stage=ClaimStageCode.CLOSED)
            .values("claim_stage")
            .annotate(total=Count("id"))
            .order_by("claim_stage")
        ]

        recent_jobs = []
        for job in (
            jobcards.select_related("claim", "claim__vehicle", "advisor")
            .order_by("-id")[:10]
        ):
            vehicle = job.claim.vehicle if job.claim_id and job.claim else None
            recent_jobs.append(
                {
                    "id": job.id,
                    "job_no": job.job_no,
                    "claim_no": job.claim.claim_no if job.claim_id else "",
                    "registration_no": vehicle.registration_no if vehicle else "",
                    "model": str(vehicle.model) if vehicle and vehicle.model_id else "",
                    "advisor": job.advisor.name if job.advisor_id else "",
                    "repair_status": job.repair_status,
                    "grand_total": float(job.grand_total or 0),
                }
            )
        employee_data = {
            "id": employee.id if employee else 0,
            "name": employee.name if employee else "",
            "designation": employee.designation or "" if employee else "",
            "employee_type": employee.employee_type if employee else "",
            "department": employee.department or "" if employee else "",
            "branch_name": (
                employee.branch.name
                if employee and employee.branch
                else ""
            ),
        }
        return Response(
            {
                "summary":{

    "total_claims": claims.count(),

    "pending_claims":
        claims.exclude(
            claim_stage=ClaimStageCode.CLOSED
        ).count(),

    "closed_claims":
        claims.filter(
            claim_stage=ClaimStageCode.CLOSED
        ).count(),

    "total_jobcards":
        jobcards.count(),

    "open_jobcards":
        jobcards.filter(
            repair_status="Open"
        ).count(),

    "closed_jobcards":
        jobcards.filter(
            repair_status="Closed"
        ).count(),

    "month_claims":
        month_claims.count(),

    "month_jobcards":
        month_jobcards.count(),

    "estimate_value":
        float(
            jobcards.aggregate(
                total=Sum("grand_total")
            )["total"] or 0
        ),

    "vehicles_inside": vehicles_inside,
"delivery_today": delivery_today,
"qc_pending": qc_pending,
"ready_delivery": ready_delivery,
"washing_pending": washing_pending,
"reinspection_pending": reinspection_pending,
},
                "stage_counts": stage_counts,
                "recent_jobs": recent_jobs,
                "employee": employee_data,
                "permissions": mobile_permissions(employee),
                "quick_actions": dashboard_quick_actions(employee),
            }
        )
def mobile_quick_actions(permissions):
    actions = []

    if "job.create" in permissions:
        actions.append("jobcard")

    if "customer.create" in permissions:
        actions.append("customer")

    if "vehicle.create" in permissions:
        actions.append("vehicle")

    if "claim.create" in permissions:
        actions.append("claim")

    if "inventory.issue" in permissions:
        actions.append("inventory")

    return actions
def dashboard_quick_actions(employee):
    if not employee:
        return []

    emp_type = (employee.employee_type or "").upper()

    if emp_type == "ADMIN":
        return [
            "jobcard",
            "customer",
            "vehicle",
            "claim",
            "inventory",
            "reports",
        ]

    elif emp_type == "MANAGER":
        return [
            "jobcard",
            "inventory",
            "reports",
        ]

    elif emp_type == "ADVISOR":
        return [
            "jobcard",
            "customer",
            "vehicle",
            "claim",
        ]

    elif emp_type == "STAFF":
        return [
            "jobcard",
        ]

    elif emp_type == "FLOOR SUPERVISOR":
        return [
            "jobcard",
            "reports",
        ]

    elif emp_type == "GATE SECURITY":
        return []

    elif emp_type == "RECEPTION":
        return [
            "customer",
            "vehicle",
        ]

    return []
def mobile_permissions(employee):
    permissions = []

    if not employee:
        return permissions

    emp_type = (employee.employee_type or "").upper()

    if emp_type == "ADMIN":
        permissions = [
            "job.create",
            "job.view",
            "customer.create",
            "vehicle.create",
            "claim.create",
            "inventory.view",
            "inventory.issue",
            "report.view",
        ]

    elif emp_type == "MANAGER":
        permissions = [
            "job.view",
            "inventory.view",
            "inventory.issue",
            "report.view",
        ]

    elif emp_type == "ADVISOR":
        permissions = [
            "job.create",
            "job.view",
            "customer.create",
            "vehicle.create",
            "claim.create",
        ]

    elif emp_type == "STAFF":
        permissions = [
            "job.view",
        ]

    elif emp_type == "FLOOR SUPERVISOR":
        permissions = [
            "job.view",
            "report.view",
        ]

    elif emp_type == "RECEPTION":
        permissions = [
            "customer.create",
            "vehicle.create",
        ]

    return permissions




class MobileClaimVehicleCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        registration_no = clean_text(request.GET.get("registration_no")).upper()
        claim_id = clean_text(request.GET.get("claim_id"))
        if not registration_no:
            return Response({"exists": False})

        vehicle = Vehicle.objects.filter(registration_no__iexact=registration_no).first()
        if not vehicle:
            return Response({"exists": False, "vehicle_found": False})

        open_claims = Claim.objects.filter(vehicle=vehicle).exclude(claim_stage=ClaimStageCode.CLOSED)
        if claim_id:
            open_claims = open_claims.exclude(pk=claim_id)
        open_claim = open_claims.order_by("-id").first()
        if open_claim:
            return Response({
                "exists": True,
                "vehicle_found": True,
                "type": "claim",
                "claim_id": open_claim.id,
                "claim_no": open_claim.claim_no,
                "message": f"Open claim already exists for {registration_no}: {open_claim.claim_no}",
            })

        open_jobcards = JobCard.objects.filter(
            Q(claim__vehicle=vehicle) | Q(vehicle=vehicle)
        ).exclude(repair_status__iexact="Closed")
        if claim_id:
            open_jobcards = open_jobcards.exclude(claim_id=claim_id)
        open_jobcard = open_jobcards.order_by("-id").first()
        if open_jobcard:
            return Response({
                "exists": True,
                "vehicle_found": True,
                "type": "jobcard",
                "jobcard_id": open_jobcard.id,
                "job_no": open_jobcard.job_no,
                "message": f"Open jobcard already exists for {registration_no}: {open_jobcard.job_no}",
            })

        
        return Response({"exists": False, "vehicle_found": True})


class MobileNextClaimNoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"claim_no": generate_mobile_claim_no(branch_for_user(request.user))})


class MobileClaimSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        data = request.data or {}
        errors = {}

        registration_no = clean_text(data.get("registrationNo")).upper()
        if not registration_no:
            errors["registrationNo"] = "Vehicle Registration No required."

        vehicle = None
        if registration_no:
            vehicle = Vehicle.objects.filter(registration_no__iexact=registration_no).first()
            if not vehicle:
                errors["registrationNo"] = "Vehicle not found in Master data. Create vehicle first."

        posted_claim_id = clean_text(data.get("id") or data.get("claimId") or data.get("claim_id"))
        claim_lookup_id = pk or posted_claim_id
        claim = Claim.objects.filter(pk=claim_lookup_id).first() if claim_lookup_id else None
        if claim_lookup_id and not claim:
            return Response(
                {"detail": "Claim not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        old_advisor_id = claim.employee_id if claim and claim.employee_id else None
        old_claim_stage = int(claim.claim_stage or 0) if claim else 0

        if vehicle:
            open_claims = Claim.objects.filter(vehicle=vehicle).exclude(claim_stage=ClaimStageCode.CLOSED)
            if claim:
                open_claims = open_claims.exclude(pk=claim.pk)
            open_claim = open_claims.order_by("-id").first()
            if open_claim:
                errors["registrationNo"] = (
                    f"Open claim already exists for this vehicle: {open_claim.claim_no}."
                )

            open_jobcard = (
                JobCard.objects.filter(Q(claim__vehicle=vehicle) | Q(vehicle=vehicle))
                .exclude(repair_status__iexact="Closed")
                .order_by("-id")
                .first()
            )
            if open_jobcard and (not claim or open_jobcard.claim_id != claim.id):
                errors["registrationNo"] = (
                    f"Open jobcard already exists for this vehicle: {open_jobcard.job_no}."
                )

        insurance_company = get_optional(InsuranceCompany, data.get("insuranceCompany"))
        advisor = get_optional(Employee, data.get("advisor"))
        surveyor = get_optional(Surveyor, data.get("surveyor"))
        delivered_by = get_optional(Employee, data.get("deliveredBy"))
        logged_employee = Employee.objects.filter(user=request.user).select_related("branch").first()
        claim_branch = (
            advisor.branch
            if advisor and advisor.branch_id
            else logged_employee.branch
            if logged_employee and logged_employee.branch_id
            else Branch.objects.filter(is_head_office=True).first()
        )

        claim_type = clean_text(data.get("claimType")) or "Cashless"
        if claim_type not in dict(Claim.CLAIM_TYPE_CHOICES):
            errors["claimType"] = "Select valid Claim Type."

        survey_status = clean_text(data.get("surveyStatus")) or "Pending"
        if survey_status and survey_status not in dict(Claim.SURVEY_STATUS_CHOICES):
            errors["surveyStatus"] = "Select valid Survey Status."

        payment_mode = clean_text(data.get("paymentMode"))
        if payment_mode and payment_mode not in dict(Claim.PAYMENT_MODE_CHOICES):
            errors["paymentMode"] = "Select valid Payment Mode."

        delivered_to = clean_text(data.get("deliveredTo"))
        if delivered_to and delivered_to not in dict(Claim.DELIVERY_TO_CHOICES):
            errors["deliveredTo"] = "Select valid Delivered To option."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        has_intimation_data = any(
            [
                clean_text(data.get("intimationDate")),
                clean_text(data.get("policyNo")),
                clean_text(data.get("icClaimNo")),
            ]
        )
        if has_intimation_data:
            existing_claim = claim
            if existing_claim and not JobCard.objects.filter(claim=existing_claim).exists():
                return Response(
                    {
                        "errors": {
                            "jobcard": "Create Jobcard before moving to Claim Intimation stage."
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not existing_claim:
                return Response(
                    {
                        "errors": {
                            "jobcard": "Save claim and create Jobcard before Claim Intimation stage."
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            if not claim:
                requested_claim_no = clean_text(data.get("claimNo"))
                claim = Claim(
                    claim_no=(
                        requested_claim_no
                        if requested_claim_no and requested_claim_no.lower() != "auto"
                        else generate_mobile_claim_no(claim_branch)
                    ),
                    vehicle=vehicle,
                )
            else:
                claim.vehicle = vehicle

            if not claim.branch_id:
             claim.branch = claim_branch
            claim.employee = advisor
            claim.insurance_company = insurance_company
            claim.policy_no = clean_text(data.get("policyNo"))
            claim.ic_claim_no = clean_text(data.get("icClaimNo"))
            claim.claim_type = claim_type
            claim.accident_date = parse_mobile_date(data.get("accidentDate"))
            claim.intimation_date = parse_mobile_date(data.get("intimationDate"))
            claim.survey_date = parse_mobile_date(data.get("surveyDate"))
            claim.surveyor = surveyor
            claim.survey_status = survey_status
            claim.insurance_approval_date = parse_mobile_date(data.get("insuranceApprovalDate"))

            claim.pre_invoice_sent_at = parse_mobile_datetime(data.get("preInvoiceSentAt"))
            claim.pre_invoice_part_amount = decimal_or_zero(data.get("preInvoicePart"))
            claim.pre_invoice_labour_amount = decimal_or_zero(data.get("preInvoiceLabour"))
            claim.pre_invoice_total_amount = (
                claim.pre_invoice_part_amount + claim.pre_invoice_labour_amount
            )

            claim.liability_received_at = parse_mobile_datetime(data.get("liabilityReceivedAt"))
            claim.liability_do_amount = decimal_or_zero(data.get("liabilityDoAmount"))

            claim.invoice_datetime = parse_mobile_datetime(data.get("invoiceDateTime"))
            claim.invoice_amount = decimal_or_zero(data.get("invoiceAmount"))
            claim.invoice_parts_amount = decimal_or_zero(data.get("invoicePartsAmount"))
            claim.invoice_labour_amount = decimal_or_zero(data.get("invoiceLabourAmount"))
            claim.customer_difference_amount = claim.invoice_amount - claim.liability_do_amount
            claim.payment_mode = payment_mode
            claim.payment_details = clean_text(data.get("paymentDetails"))

            claim.delivery_datetime = parse_mobile_datetime(data.get("deliveryDateTime"))
            claim.delivered_by = delivered_by
            claim.delivered_to = delivered_to
            claim.delivery_driver_name = clean_text(data.get("driverName"))
            claim.delivery_remarks = clean_text(data.get("deliveryRemarks"))

            derived_stage = shared_derive_claim_stage(claim)
            if (
                old_claim_stage >= ClaimStageCode.INTIMATION
                and JobCard.objects.filter(claim=claim).exists()
                and derived_stage < ClaimStageCode.INTIMATION
            ):
                derived_stage = old_claim_stage
            elif (
                claim.employee_id
                and JobCard.objects.filter(claim=claim).exists()
                and derived_stage < ClaimStageCode.INTIMATION
            ):
                derived_stage = ClaimStageCode.INTIMATION
            claim.claim_stage = derived_stage
            claim.status = "Closed" if claim.claim_stage == ClaimStageCode.CLOSED else "Open"
            claim.save()

        whatsapp_result = None
        if old_advisor_id != claim.employee_id and claim.employee_id:
            whatsapp_result = send_advisor_assigned_whatsapp(claim)

        message = "Claim saved successfully."
        if whatsapp_result and not whatsapp_result.get("success"):
            message = (
                "Claim saved, but WhatsApp advisor message was not sent: "
                + str(whatsapp_result.get("response", ""))[:180]
            )
        return Response(
            {
                "message": message,
                "claim": shared_mobile_claim_payload(claim),
                "whatsapp": whatsapp_result or {},
            }
        )

class MobileClaimEntryOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        advisors = branch_filter_queryset(
            Employee.objects.filter(
                employee_type="Advisor",
                is_active=True,
            ),
            request.user,
        ).order_by("name")

        employees = branch_filter_queryset(
            Employee.objects.filter(
                is_active=True,
            ),
            request.user,
        ).order_by("name")

        open_claims = branch_filter_queryset(
            Claim.objects.select_related("vehicle", "vehicle__variant", "employee")
            .filter(status="Open")
            .exclude(jobcard__isnull=False),
            request.user,
        )

        pending_gate_entries = branch_filter_queryset(
            GateInEntry.objects.select_related("vehicle", "vehicle__customer", "vehicle__model")
            .filter(status="Pending", jobcard__isnull=True, vehicle__isnull=False),
            request.user,
        ).order_by("-gate_in_datetime")
        pending_gate_vehicles = []
        seen_vehicle_ids = set()
        for entry in pending_gate_entries[:300]:
            if entry.vehicle_id in seen_vehicle_ids:
                continue
            seen_vehicle_ids.add(entry.vehicle_id)
            vehicle = entry.vehicle
            customer = vehicle.customer.name if vehicle.customer_id else ""
            model = vehicle.model.name if vehicle.model_id else ""
            pending_gate_vehicles.append({
                "id": vehicle.id,
                "label": " | ".join(
                    value for value in (vehicle.registration_no, customer, model) if value
                ),
                "registration_no": vehicle.registration_no,
                "gate_entry_id": entry.id,
                "gate_in_datetime": timezone.localtime(entry.gate_in_datetime).isoformat(timespec="minutes"),
                "gate_in_display": timezone.localtime(entry.gate_in_datetime).strftime("%d/%m/%Y %H:%M"),
                "current_km": entry.current_km,
            })

        return Response(
            {
                "insurance_companies": [
                    {"id": item.id, "label": item.ins_co_name}
                    for item in InsuranceCompany.objects.all().order_by("ins_co_name")
                ],
                "advisors": [
                    {"id": item.id, "label": item.name}
                    for item in advisors
                ],
                "surveyors": [
                    {"id": item.id, "label": item.name}
                    for item in Surveyor.objects.all().order_by("name")
                ],
                "employees": [
                    {"id": item.id, "label": item.name}
                    for item in employees
                ],
                "branches": [
                    {"id": item.id, "label": f"{item.code} - {item.name}", "code": item.code}
                    for item in Branch.objects.filter(is_active=True).order_by("name")
                ],
                "claim_types": [
                    {"id": value, "label": label}
                    for value, label in Claim.CLAIM_TYPE_CHOICES
                ],
                "survey_statuses": [
                    {"id": value, "label": label}
                    for value, label in Claim.SURVEY_STATUS_CHOICES
                ],
                "payment_modes": [
                    {"id": value, "label": label}
                    for value, label in Claim.PAYMENT_MODE_CHOICES
                ],
                "delivery_to_options": [
                    {"id": value, "label": label}
                    for value, label in Claim.DELIVERY_TO_CHOICES
                ],
                "delivered_to_choices": [
                    {"id": value, "label": label}
                    for value, label in Claim.DELIVERY_TO_CHOICES
                ],
                "vehicle_models": [
                    {"id": item.id, "label": item.name}
                    for item in VehicleModel.objects.all().order_by("name")
                ],
                "vehicle_variants": [
                    {"id": item.id, "label": item.name, "model_id": item.model_id}
                    for item in VehicleVariant.objects.select_related("model").order_by("model__name", "name")
                ],
                "vehicle_types": [
                    {"id": value, "label": label}
                    for value, label in Vehicle.VEHICLE_TYPE_CHOICES
                ],
                "open_claims": [
                    {
                        "id": claim.id,
                        "label": f"{claim.claim_no} - {claim.vehicle.registration_no if claim.vehicle_id else ''}",
                        "advisor": claim.employee_id or "",
                        "variant": claim.vehicle.variant.name if claim.vehicle_id and claim.vehicle.variant_id else "",
                        "claim_stage": claim.claim_stage,
                        "claim_stage_label": dict(Claim.CLAIM_STAGES).get(claim.claim_stage, str(claim.claim_stage)),
                    }
                    for claim in open_claims.order_by("-id")[:100]
                ],
                "pending_gate_in_vehicles": pending_gate_vehicles,
                "jobcard_inward_types": [
                    {"id": value, "label": label}
                    for value, label in JobCard.INWARD_TYPE_CHOICES
                ],
                "jobcard_repair_statuses": [
                    {"id": value, "label": label}
                    for value, label in JobCard._meta.get_field("repair_status").choices
                ],
                "jobcard_second_approval_statuses": [
                    {"id": value, "label": label}
                    for value, label in JobCard._meta.get_field("second_approval_status").choices
                ],
                "labour_paint_panel_types": [
                    {"id": value, "label": label}
                    for value, label in JobCardLabour.PAINT_PANEL_TYPE_CHOICES
                ],
                "tyre_positions": [
                    {"id": value, "label": label}
                    for value, label in JobCardTyreInventory.POSITION_CHOICES
                ],
            }
        )




































