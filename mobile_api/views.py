import base64
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import NoReverseMatch, reverse
from django.db.models import Count, Sum
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal, InvalidOperation

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
    WorkProgress,
    WorkProgressPhoto,
    UserNotification,
)
from core.numbering import branch_for_claim, branch_for_user, next_claim_no, next_jobcard_no
from core.views import notify_reception_gate_in, notify_reception_gate_in_changed
from core.whatsapp import send_advisor_assigned_whatsapp
from rbac.models import Menu, RoleMenuPermission, UserMenuPermission

from .serializers import MobileLoginSerializer


VEHICLE_CONDITION_PHOTO_CAPTIONS = [
    "Front View",
    "Front Right Corner View",
    "Full Right View",
    "Rear Right Corner View",
    "Rear View",
    "Rear Left Corner View",
    "Full Left View",
    "Front Left Corner View",
    "Engine Compartment",
    "Windshield Glass",
    "Instrument Cluster Photo",
    "Full Dashboard Photo",
    "Interior View Photo",
    "Chassis No View",
    "Rear Glass View",
    "Dicky View",
    "Jack & Tools View",
    "Stepney View",
    "Other View 1",
    "Other View 2",
]


def generate_mobile_claim_no(branch=None):
    return next_claim_no(branch)


def generate_mobile_job_no(branch=None):
    return next_jobcard_no(branch)


def clean_text(value):
    return str(value or "").strip()


def decimal_or_zero(value):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def int_or_zero(value):
    try:
        return int(Decimal(str(value or "0")))
    except (InvalidOperation, TypeError, ValueError):
        return 0


def parse_mobile_date(value):
    value = clean_text(value)
    return parse_date(value) if value else None


def parse_mobile_datetime(value):
    value = clean_text(value)
    if not value:
        return None

    parsed = parse_datetime(value.replace(" ", "T"))
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def save_mobile_signature_data(job, field_name, data_url):
    data_url = clean_text(data_url)
    if not data_url:
        return False

    field = getattr(job, field_name)
    if data_url == "__clear__":
        if field:
            field.delete(save=False)
        setattr(job, field_name, None)
        return True

    if not data_url.startswith("data:image/png;base64,"):
        return False

    try:
        image_data = base64.b64decode(data_url.split(",", 1)[1])
    except (ValueError, IndexError):
        return False

    if field:
        field.delete(save=False)

    filename = f"{job.job_no}_{field_name}.png".replace("/", "_")
    setattr(job, field_name, ContentFile(image_data, name=filename))
    return True


def get_optional(model, pk):
    if not pk:
        return None
    return model.objects.filter(pk=pk).first()


def mobile_claim_payload(claim):
    vehicle = claim.vehicle if claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    stage_lookup = dict(Claim.CLAIM_STAGES)
    jobcard = JobCard.objects.filter(claim=claim).order_by("-id").first()
    allocation = getattr(jobcard, "allocation", None) if jobcard else None
    repair_progress_started = (
        WorkProgress.objects.filter(
            allocation=allocation,
            start_time__isnull=False,
        ).exists()
        if allocation
        else False
    )
    work_completed = bool(jobcard and jobcard.repair_status in ["Completed", "Closed"])

    return {
        "id": claim.id,
        "claim_no": claim.claim_no,
        "branch": claim.branch_id or "",
        "branch_name": claim.branch.name if claim.branch_id else "",
        "branch_code": claim.branch.code if claim.branch_id else "",
        "has_jobcard": bool(jobcard),
        "jobcard_id": jobcard.id if jobcard else "",
        "job_no": jobcard.job_no if jobcard else "",
        "jobcard_repair_status": jobcard.repair_status if jobcard else "",
        "work_allocation_created": bool(allocation),
        "repair_progress_started": repair_progress_started,
        "work_completed": work_completed,
        "registration_no": vehicle.registration_no if vehicle else "",
        "customer": customer.name if customer else "",
        "variant": vehicle.variant.name if vehicle and vehicle.variant_id else "",
        "advisor": claim.employee_id or "",
        "advisor_name": claim.employee.name if claim.employee_id else "",
        "insurance_company": claim.insurance_company_id or "",
        "policy_no": claim.policy_no or "",
        "ic_claim_no": claim.ic_claim_no or "",
        "claim_type": claim.claim_type or "",
        "accident_date": claim.accident_date.isoformat() if claim.accident_date else "",
        "intimation_date": claim.intimation_date.isoformat() if claim.intimation_date else "",
        "survey_date": claim.survey_date.isoformat() if claim.survey_date else "",
        "surveyor": claim.surveyor_id or "",
        "survey_status": claim.survey_status or "",
        "insurance_approval_date": claim.insurance_approval_date.isoformat() if claim.insurance_approval_date else "",
        "claim_stage": claim.claim_stage,
        "claim_stage_label": stage_lookup.get(claim.claim_stage, str(claim.claim_stage)),
        "status": claim.status,
        "pre_invoice_sent_at": claim.pre_invoice_sent_at.isoformat(sep=" ", timespec="minutes") if claim.pre_invoice_sent_at else "",
        "pre_invoice_part_amount": float(claim.pre_invoice_part_amount or 0),
        "pre_invoice_labour_amount": float(claim.pre_invoice_labour_amount or 0),
        "liability_received_at": claim.liability_received_at.isoformat(sep=" ", timespec="minutes") if claim.liability_received_at else "",
        "liability_do_amount": float(claim.liability_do_amount or 0),
        "invoice_datetime": claim.invoice_datetime.isoformat(sep=" ", timespec="minutes") if claim.invoice_datetime else "",
        "invoice_amount": float(claim.invoice_amount or 0),
        "invoice_parts_amount": float(claim.invoice_parts_amount or 0),
        "invoice_labour_amount": float(claim.invoice_labour_amount or 0),
        "payment_mode": claim.payment_mode or "",
        "payment_details": claim.payment_details or "",
        "delivery_datetime": claim.delivery_datetime.isoformat(sep=" ", timespec="minutes") if claim.delivery_datetime else "",
        "delivered_by": claim.delivered_by_id or "",
        "delivered_to": claim.delivered_to or "",
        "delivery_driver_name": claim.delivery_driver_name or "",
        "delivery_remarks": claim.delivery_remarks or "",
    }


def mobile_jobcard_payload(job):
    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    stage_lookup = dict(Claim.CLAIM_STAGES)
    inventory = getattr(job, "inventory", None)
    allocation = getattr(job, "allocation", None)
    work_completed = (
        job.repair_status in ["Completed", "Closed"]
        or (claim and int(claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED)
    )
    ri_done = bool(job.reinspection_done) or (
        claim and int(claim.claim_stage or 0) >= ClaimStageCode.LIABILITY
    )
    close_ready = {
        "work_completed": bool(work_completed),
        "qc_done": bool(job.qc_done),
        "ri_done": bool(ri_done),
        "part_entry_complete": bool(allocation and allocation.part_entry_complete),
    }

    return {
        "id": job.id,
        "claim": claim.id if claim else "",
        "claim_no": claim.claim_no if claim else "",
        "claim_stage": claim.claim_stage if claim else "",
        "claim_stage_label": stage_lookup.get(claim.claim_stage, "") if claim else "",
        "job_no": job.job_no,
        "job_date": job.job_date.isoformat(sep=" ", timespec="minutes") if job.job_date else "",
        "registration_no": vehicle.registration_no if vehicle else "",
        "customer": customer.name if customer else "",
        "model": str(vehicle.model) if vehicle and vehicle.model_id else "",
        "variant": vehicle.variant.name if vehicle and vehicle.variant_id else "",
        "advisor": job.advisor_id or "",
        "advisor_name": job.advisor.name if job.advisor_id else "",
        "vehicle_inward_type": job.vehicle_inward_type or "",
        "vehicle_inward_by": job.vehicle_inward_by or "",
        "gate_in_datetime": job.gate_in_datetime.isoformat(sep=" ", timespec="minutes") if job.gate_in_datetime else "",
        "expected_delivery_datetime": job.expected_delivery_datetime.isoformat(sep=" ", timespec="minutes") if job.expected_delivery_datetime else "",
        "km": job.km or "",
        "fuel_level": job.fuel_level or "",
        "part_order_date": job.part_order_date.isoformat() if job.part_order_date else "",
        "part_order_no": job.part_order_no or "",
        "repair_status": job.repair_status or "",
        "estimated_delivery": job.estimated_delivery.isoformat(sep=" ", timespec="minutes") if job.estimated_delivery else "",
        "actual_delivery": job.actual_delivery.isoformat(sep=" ", timespec="minutes") if job.actual_delivery else "",
        "repair_instructions": job.repair_instructions or "",
        "road_test_done": job.road_test_done,
        "washing_done": job.washing_done,
        "ready_for_delivery": job.ready_for_delivery,
        "additional_approval_required": job.additional_approval_required,
        "second_approval_status": job.second_approval_status or "",
        "additional_approval_reason": job.additional_approval_reason or "",
        "advisor_signature_url": job.advisor_signature.url if job.advisor_signature else "",
        "customer_signature_url": job.customer_signature.url if job.customer_signature else "",
        "qc_done": job.qc_done,
        "reinspection_done": job.reinspection_done,
        "reinspection_date": job.reinspection_date.isoformat(sep=" ", timespec="minutes") if job.reinspection_date else "",
        "reinspection_done_by": job.reinspection_done_by or "",
        "parts_total": float(job.parts_total or 0),
        "labour_total": float(job.labour_total or 0),
        "grand_total": float(job.grand_total or 0),
        "close_ready": close_ready,
        "close_pending": [
            label
            for key, label in {
                "work_completed": "Work Completed",
                "qc_done": "QC Done",
                "ri_done": "RI Done",
                "part_entry_complete": "Part Entry Complete",
            }.items()
            if not close_ready[key]
        ],
        "inventory": {
            "mud_flap_count": inventory.mud_flap_count if inventory else 0,
            "floor_mat_count": inventory.floor_mat_count if inventory else 0,
            "lh_mirror": bool(inventory and inventory.lh_mirror),
            "rh_mirror": bool(inventory and inventory.rh_mirror),
            "center_mirror": bool(inventory and inventory.center_mirror),
            "frt_wiper": bool(inventory and inventory.frt_wiper),
            "rr_wiper": bool(inventory and inventory.rr_wiper),
            "accessories": bool(inventory and inventory.accessories),
            "spare_wheel": bool(inventory and inventory.spare_wheel),
            "jack": bool(inventory and inventory.jack),
            "tool_kit": bool(inventory and inventory.tool_kit),
            "stereo": bool(inventory and inventory.stereo),
            "battery": bool(inventory and inventory.battery),
            "number_plate": bool(inventory and inventory.number_plate),
            "fuel_percent": inventory.fuel_percent if inventory else 0,
            "cng_percent": inventory.cng_percent if inventory else 0,
            "damage_marks": inventory.damage_marks if inventory else [],
            "remarks": inventory.remarks if inventory else "",
        },
        "tyres": [
            {
                "position": tyre.position,
                "label": dict(JobCardTyreInventory.POSITION_CHOICES).get(tyre.position, tyre.position),
                "make": tyre.make,
                "size": tyre.size,
                "depth": float(tyre.depth or 0),
                "wheel_cap": tyre.wheel_cap,
            }
            for tyre in job.tyres.all().order_by("id")
        ],
        "vehicle_condition_photos": [
            {
                "index": index,
                "caption": caption,
                "id": photo.id if photo else "",
                "url": photo.image.url if photo and photo.image else "",
                "uploaded_at": photo.uploaded_at.isoformat(sep=" ", timespec="minutes") if photo else "",
            }
            for index, caption in enumerate(VEHICLE_CONDITION_PHOTO_CAPTIONS, start=1)
            for photo in [
                next(
                    (
                        item
                        for item in job.vehicle_condition_photos.all()
                        if item.caption == caption
                    ),
                    None,
                )
            ]
        ],
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "actions": mobile_jobcard_action_payload(None, job),
        "parts": [
            {
                "id": part.id,
                "part_no": part.part_no,
                "description": part.description,
                "qty": part.qty,
                "rate": float(part.rate or 0),
                "amount": float(part.amount or 0),
            }
            for part in job.parts.all().order_by("id")
        ],
        "labours": [
            {
                "id": labour.id,
                "job_code": labour.job_code,
                "description": labour.description,
                "labour_hrs": float(labour.labour_hrs or 0),
                "rate": float(labour.rate or 0),
                "amount": float(labour.amount or 0),
                "paint_panel_type": labour.paint_panel_type or "",
            }
            for labour in job.labours.all().order_by("id")
        ],
    }


def mobile_jobcard_action_payload(request, job):
    pdf_path = reverse("jobcard_print", args=[job.id, settings.PDF_SECRET_TOKEN])
    preview_path = reverse("jobcard_print_preview", args=[job.id, settings.PDF_SECRET_TOKEN])

    if request is not None:
        pdf_url = request.build_absolute_uri(pdf_path)
        preview_url = request.build_absolute_uri(preview_path)
    else:
        site_url = getattr(settings, "SITE_URL", "").rstrip("/")
        pdf_url = f"{site_url}{pdf_path}" if site_url else pdf_path
        preview_url = f"{site_url}{preview_path}" if site_url else preview_path

    whatsapp_url = ""
    whatsapp_message = ""
    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    mobile_no = (customer.mobile_no if customer else "") or ""
    if mobile_no:
        mobile = "91" + mobile_no[-10:]
        whatsapp_message = (
            f"Dear {customer.name},\n"
            f"Your Job Card {job.job_no} has been created.\n"
            f"Vehicle: {vehicle.registration_no if vehicle else ''}\n\n"
            f"JobCard PDF:\n{pdf_url}"
        )
        whatsapp_url = f"https://wa.me/{mobile}?text={quote(whatsapp_message)}"

    return {
        "print_preview_url": preview_url,
        "print_pdf_url": pdf_url,
        "whatsapp_url": whatsapp_url,
        "whatsapp_message": whatsapp_message,
    }


def derive_claim_stage(claim):
    if claim.delivery_datetime and claim.delivered_by_id and claim.delivered_to:
        return ClaimStageCode.CLOSED
    if claim.invoice_datetime or claim.invoice_amount:
        return ClaimStageCode.INVOICED
    if claim.liability_received_at or claim.liability_do_amount:
        return ClaimStageCode.LIABILITY
    if claim.insurance_approval_date or claim.assessment_file:
        return ClaimStageCode.INSURANCE_APPROVAL
    if claim.survey_date or claim.surveyor_id:
        return ClaimStageCode.SURVEY
    if claim.intimation_date or claim.policy_no or claim.ic_claim_no:
        return ClaimStageCode.INTIMATION
    if claim.employee_id:
        return ClaimStageCode.ADVISOR_ASSIGNED
    return ClaimStageCode.CLAIM_CREATED


def user_payload(user):
    employee = Employee.objects.filter(user=user).first()
    employee_type = employee.employee_type if employee else ""
    branch = employee.branch if employee and employee.branch_id else None

    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_superuser": user.is_superuser,
        "employee": {
            "id": employee.id if employee else None,
            "name": employee.name if employee else user.get_full_name() or user.username,
            "employee_code": employee.employee_code if employee else "",
            "employee_type": employee_type,
            "designation": employee.designation if employee else "",
            "department": employee.department if employee else "",
            "profile_photo_url": employee.profile_photo.url if employee and employee.profile_photo else "",
            "branch": branch.id if branch else "",
            "branch_name": branch.name if branch else "",
            "branch_code": branch.code if branch else "",
        },
        "roles": list(user.groups.values_list("name", flat=True)),
    }


def employee_can_view_all_branches(user, employee=None):
    if user.is_superuser:
        return True
    employee = employee or Employee.objects.filter(user=user).first()
    if not employee:
        return False
    role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
    return employee.employee_type in ["MANAGER", "ADMIN"] or "HEAD OFFICE" in role_text or "HO" == (employee.branch.code if employee.branch_id else "")


def user_branch(user):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    return employee.branch if employee and employee.branch_id else None


def branch_filter_queryset(queryset, user, branch_lookup="branch"):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    if employee_can_view_all_branches(user, employee):
        return queryset
    if employee and employee.branch_id:
        return queryset.filter(**{f"{branch_lookup}_id": employee.branch_id})
    return queryset.filter(**{f"{branch_lookup}__isnull": True})


def allowed_menus_for_user(user):
    if user.is_superuser:
        menus = list(Menu.objects.all().order_by("order", "name"))
    else:
        user_permissions = UserMenuPermission.objects.filter(
            user=user
        ).select_related("menu", "menu__parent")

        if user_permissions.exists():
            menus = [perm.menu for perm in user_permissions if perm.can_view]
        elif user.groups.exists():
            role_permissions = RoleMenuPermission.objects.filter(
                group__in=user.groups.all(),
                can_view=True,
            ).select_related("menu", "menu__parent")
            menus = [perm.menu for perm in role_permissions]
        else:
            menus = []

        all_menus = {menu.id: menu for menu in menus}
        for menu in list(menus):
            parent = menu.parent
            while parent:
                all_menus[parent.id] = parent
                parent = parent.parent

        menus = list(all_menus.values())

    return list({menu.id: menu for menu in menus}.values())


def menu_href(menu):
    if not menu.url:
        return "#"

    try:
        return reverse(menu.url)
    except NoReverseMatch:
        return "/" + menu.url.strip("/")


def build_menu_tree(menus):
    menu_map = {}

    for menu in menus:
        menu_map[menu.id] = {
            "id": menu.id,
            "title": menu.name,
            "url": menu.url,
            "href": menu_href(menu),
            "icon": menu.icon,
            "parent_id": menu.parent_id,
            "children": [],
        }

    tree = []
    for item in menu_map.values():
        parent_id = item["parent_id"]
        if parent_id and parent_id in menu_map:
            menu_map[parent_id]["children"].append(item)
        else:
            tree.append(item)

    return tree


def mobile_notification_payload(notification):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "url": notification.url or "",
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(sep=" ", timespec="minutes"),
    }


def mobile_create_user_notification(user, title, message, url=""):
    if not user:
        return

    UserNotification.objects.create(
        user=user,
        title=title,
        message=message,
        url=url or "",
    )


def mobile_notify_jobcard_advisor(job, title, message):
    if not job:
        return

    advisor_user = None
    if job.advisor_id and job.advisor and job.advisor.user_id:
        advisor_user = job.advisor.user
    elif job.claim_id and job.claim and job.claim.employee_id and job.claim.employee.user_id:
        advisor_user = job.claim.employee.user

    mobile_create_user_notification(
        advisor_user,
        title,
        message,
        f"/jobCard/{job.id}/edit/",
    )


def mobile_notify_work_progress_change(progress, action_label):
    job = progress.allocation.job if progress and progress.allocation_id else None
    if not job:
        return

    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    registration_no = vehicle.registration_no if vehicle else "-"
    mobile_notify_jobcard_advisor(
        job,
        "Repair Work Progress Updated",
        f"Jobcard {job.job_no} {progress.get_stage_display()} {action_label} for {registration_no}",
    )


class MobileLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = MobileLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_payload(user),
            }
        )


class MobileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": user_payload(request.user)})


class MobileProfilePhotoUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        employee = Employee.objects.filter(user=request.user).first()
        if not employee:
            return Response({"errors": {"profilePhoto": "Employee profile not found."}}, status=status.HTTP_400_BAD_REQUEST)

        image = request.FILES.get("profile_photo")
        if not image:
            return Response({"errors": {"profilePhoto": "Select profile photo."}}, status=status.HTTP_400_BAD_REQUEST)

        if employee.profile_photo:
            employee.profile_photo.delete(save=False)
        employee.profile_photo = image
        employee.save(update_fields=["profile_photo"])

        return Response({
            "message": "Profile photo updated successfully.",
            "user": user_payload(request.user),
        })


class MobileMenuView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        menus = allowed_menus_for_user(request.user)
        return Response({"menus": build_menu_tree(menus)})


class MobileNotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = UserNotification.objects.filter(
            user=request.user,
            is_read=False,
        ).order_by("-created_at")
        notifications = queryset[:20]

        return Response({
            "count": queryset.count(),
            "notifications": [
                mobile_notification_payload(notification)
                for notification in notifications
            ],
        })


class MobileNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        UserNotification.objects.filter(
            id=pk,
            user=request.user,
        ).update(is_read=True)

        return Response({"status": "success"})


def dashboard_querysets_for_user(user):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    all_claims = branch_filter_queryset(Claim.objects.all(), user)
    all_jobcards = branch_filter_queryset(JobCard.objects.all(), user, "claim__branch")

    if employee_can_view_all_branches(user, employee):
        return all_claims, all_jobcards

    if employee and employee.employee_type in ["MANAGER", "ADMIN"]:
        return all_claims, all_jobcards

    if employee and employee.employee_type == "Advisor":
        return (
            Claim.objects.filter(employee=employee),
            JobCard.objects.filter(advisor=employee),
        )

    if employee and employee.employee_type in ["STAFF", "RECEPTION"]:
        return all_claims.filter(employee__isnull=True), JobCard.objects.none()

    return Claim.objects.none(), JobCard.objects.none()


def is_mobile_repair_resource(employee):
    if not employee:
        return False

    role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
    return any(
        keyword in role_text
        for keyword in ["TECHNICIAN", "DENTER", "PAINTER"]
    )


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

            entry.status = "Gate Out"
            entry.gate_out_datetime = timezone.now()
            entry.gate_out_by = request.user
            entry.save(update_fields=["status", "gate_out_datetime", "gate_out_by", "updated_at"])
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

        registration_no = clean_text(data.get("registrationNo")).upper()
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


def mobile_work_progress_payload(progress):
    job = progress.allocation.job if progress.allocation_id else None
    claim = job.claim if job and job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None

    return {
        "id": progress.id,
        "stage": progress.stage,
        "stage_label": progress.get_stage_display(),
        "start_time": progress.start_time.isoformat() if progress.start_time else "",
        "finish_time": progress.finish_time.isoformat() if progress.finish_time else "",
        "remarks": progress.remarks or "",
        "photo_count": progress.photos.count(),
        "job_id": job.id if job else "",
        "job_no": job.job_no if job else "",
        "claim_no": claim.claim_no if claim else "",
        "registration_no": vehicle.registration_no if vehicle else "",
        "model": vehicle.model.name if vehicle and vehicle.model_id else "",
        "customer": customer.name if customer else "",
    }


def mobile_my_work_queryset(employee, from_date=None, to_date=None):
    progress = (
        WorkProgress.objects
        .select_related(
            "allocation",
            "allocation__job",
            "allocation__job__claim",
            "allocation__job__claim__vehicle",
            "allocation__job__claim__vehicle__customer",
            "allocation__job__claim__vehicle__model",
            "employee",
        )
        .prefetch_related("photos")
        .filter(employee=employee)
    )

    if from_date:
        progress = progress.filter(allocation__job__created_at__date__gte=from_date)
    if to_date:
        progress = progress.filter(allocation__job__created_at__date__lte=to_date)

    return progress


def mobile_apply_my_work_status(progress, status_filter):
    if status_filter == "wip":
        return progress.filter(start_time__isnull=False, finish_time__isnull=True)
    if status_filter == "completed":
        return progress.filter(finish_time__isnull=False)
    return progress.filter(start_time__isnull=True)


class MobileDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims, jobcards = dashboard_querysets_for_user(request.user)
        today = timezone.localdate()
        month_start = today.replace(day=1)

        month_claims = claims.filter(created_at__date__gte=month_start)
        month_jobcards = jobcards.filter(created_at__date__gte=month_start)

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

        return Response(
            {
                "summary": {
                    "total_claims": claims.count(),
                    "pending_claims": claims.exclude(
                        claim_stage=ClaimStageCode.CLOSED
                    ).count(),
                    "closed_claims": claims.filter(
                        claim_stage=ClaimStageCode.CLOSED
                    ).count(),
                    "total_jobcards": jobcards.count(),
                    "open_jobcards": jobcards.filter(repair_status="Open").count(),
                    "closed_jobcards": jobcards.filter(repair_status="Closed").count(),
                    "month_claims": month_claims.count(),
                    "month_jobcards": month_jobcards.count(),
                    "estimate_value": float(
                        jobcards.aggregate(total=Sum("grand_total")).get("total") or 0
                    ),
                },
                "stage_counts": stage_counts,
                "recent_jobs": recent_jobs,
            }
        )


class MobileMyWorkListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = Employee.objects.filter(user=request.user).first()
        if not is_mobile_repair_resource(employee):
            return Response(
                {"detail": "Only Technician, Denter or Painter can access My Work."},
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.localdate()
        month_start = today.replace(day=1)
        from_date = parse_mobile_date(request.GET.get("from_date")) or month_start
        to_date = parse_mobile_date(request.GET.get("to_date")) or today
        status_filter = clean_text(request.GET.get("status")) or "new"

        base_progress = mobile_my_work_queryset(employee, from_date, to_date)
        rows = mobile_apply_my_work_status(base_progress, status_filter).order_by(
            "start_time",
            "allocation__job__job_no",
            "id",
        )

        return Response({
            "filters": {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "status": status_filter,
            },
            "counts": {
                "new": base_progress.filter(start_time__isnull=True).count(),
                "wip": base_progress.filter(start_time__isnull=False, finish_time__isnull=True).count(),
                "completed": base_progress.filter(finish_time__isnull=False).count(),
            },
            "jobs": [
                mobile_work_progress_payload(progress)
                for progress in rows
            ],
        })


class MobileMyWorkActionView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, progress_id):
        employee = Employee.objects.filter(user=request.user).first()
        if not is_mobile_repair_resource(employee):
            return Response(
                {"detail": "Only Technician, Denter or Painter can update My Work."},
                status=status.HTTP_403_FORBIDDEN,
            )

        progress = (
            WorkProgress.objects
            .select_related(
                "allocation",
                "allocation__job",
                "allocation__job__advisor",
                "allocation__job__advisor__user",
                "allocation__job__claim",
                "allocation__job__claim__employee",
                "allocation__job__claim__employee__user",
                "allocation__job__claim__vehicle",
            )
            .filter(id=progress_id, employee=employee)
            .first()
        )
        if not progress:
            return Response({"detail": "Work progress not found."}, status=status.HTTP_404_NOT_FOUND)

        action = clean_text(request.data.get("action"))
        old_start_time = progress.start_time
        old_finish_time = progress.finish_time

        if action == "start" and not progress.start_time:
            progress.start_time = timezone.now()
            progress.save(update_fields=["start_time"])
        elif action == "finish":
            if not progress.start_time:
                progress.start_time = timezone.now()
            if not progress.finish_time:
                progress.finish_time = timezone.now()
            progress.save(update_fields=["start_time", "finish_time"])

        for image in request.FILES.getlist("progress_photos"):
            WorkProgressPhoto.objects.create(
                progress=progress,
                image=image,
            )

        if action == "start" and not old_start_time and progress.start_time:
            mobile_notify_work_progress_change(progress, "started")
        elif action == "finish" and not old_finish_time and progress.finish_time:
            mobile_notify_work_progress_change(progress, "finished")

        return Response({
            "message": "My Work updated successfully.",
            "job": mobile_work_progress_payload(progress),
        })


class MobileClaimListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims, _ = dashboard_querysets_for_user(request.user)
        status = request.GET.get("status") or "open"

        if status == "open":
            claims = claims.exclude(claim_stage=ClaimStageCode.CLOSED)
        elif status == "closed":
            claims = claims.filter(claim_stage=ClaimStageCode.CLOSED)

        stage_lookup = dict(Claim.CLAIM_STAGES)
        rows = []
        for claim in (
            claims.select_related("vehicle", "vehicle__customer", "vehicle__variant", "employee")
            .order_by("-id")[:100]
        ):
            row = mobile_claim_payload(claim)
            row.update(
                {
                    "advisor_name": claim.employee.name if claim.employee_id else "",
                    "created_at": claim.created_at.isoformat() if claim.created_at else "",
                    "pending_days": (
                        timezone.localdate() - claim.created_at.date()
                    ).days
                    if claim.created_at
                    else 0,
                }
            )
            rows.append(row)

        return Response({"claims": rows})


class MobileClaimDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        claim = (
            Claim.objects.select_related(
                "vehicle",
                "vehicle__customer",
                "employee",
                "insurance_company",
                "surveyor",
                "delivered_by",
            )
            .filter(pk=pk)
            .first()
        )
        if not claim:
            return Response({"detail": "Claim not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"claim": mobile_claim_payload(claim)})


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

        open_jobcard = (
            JobCard.objects.filter(claim__vehicle=vehicle)
            .exclude(repair_status="Closed")
            .order_by("-id")
            .first()
        )
        if open_jobcard:
            return Response({
                "exists": True,
                "vehicle_found": True,
                "type": "jobcard",
                "jobcard_id": open_jobcard.id,
                "job_no": open_jobcard.job_no,
                "claim_no": open_jobcard.claim.claim_no if open_jobcard.claim_id else "",
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

        claim = Claim.objects.filter(pk=pk).first() if pk else None
        if pk and not claim:
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
                JobCard.objects.filter(claim__vehicle=vehicle)
                .exclude(repair_status="Closed")
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

            derived_stage = derive_claim_stage(claim)
            if (
                old_claim_stage >= ClaimStageCode.INTIMATION
                and JobCard.objects.filter(claim=claim).exists()
                and derived_stage < ClaimStageCode.INTIMATION
            ):
                derived_stage = old_claim_stage
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
                "claim": mobile_claim_payload(claim),
                "whatsapp": whatsapp_result or {},
            }
        )


class MobileJobcardListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _, jobcards = dashboard_querysets_for_user(request.user)
        repair_status = request.GET.get("repair_status") or "Open"

        if repair_status and repair_status.lower() != "all":
            jobcards = jobcards.filter(repair_status=repair_status)

        rows = []
        for job in (
            jobcards.select_related("claim", "claim__vehicle", "advisor")
            .order_by("-id")[:100]
        ):
            vehicle = job.claim.vehicle if job.claim_id and job.claim else None
            rows.append(
                {
                    "id": job.id,
                    "job_no": job.job_no,
                    "claim_no": job.claim.claim_no if job.claim_id else "",
                    "registration_no": vehicle.registration_no if vehicle else "",
                    "model": str(vehicle.model) if vehicle and vehicle.model_id else "",
                    "advisor": job.advisor.name if job.advisor_id else "",
                    "repair_status": job.repair_status,
                    "created_at": job.created_at.isoformat() if job.created_at else "",
                    "grand_total": float(job.grand_total or 0),
                }
            )

        return Response({"jobcards": rows})


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
        return Response({"jobcard": mobile_jobcard_payload(job)})


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
                    JobCard.objects.prefetch_related("parts", "labours", "vehicle_condition_photos").get(pk=job.pk)
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
                    JobCard.objects.prefetch_related("parts", "labours", "vehicle_condition_photos").get(pk=job.pk)
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
    parser_classes = [MultiPartParser, FormParser]

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


class MobileVehicleSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        if len(query) < 2:
            return Response({"vehicles": []})

        vehicles = (
            Vehicle.objects.select_related("customer", "model", "variant")
            .filter(
                Q(registration_no__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(customer__mobile_no__icontains=query)
            )
            .order_by("registration_no")[:15]
        )

        return Response(
            {
                "vehicles": [
                    {
                        "id": vehicle.id,
                        "registration_no": vehicle.registration_no,
                        "customer": vehicle.customer.name if vehicle.customer_id else "",
                        "mobile_no": vehicle.customer.mobile_no if vehicle.customer_id else "",
                        "model": vehicle.model.name if vehicle.model_id else "",
                        "variant": vehicle.variant.name if vehicle.variant_id else "",
                        "label": (
                            f"{vehicle.registration_no} | "
                            f"{vehicle.customer.name if vehicle.customer_id else ''} | "
                            f"{vehicle.model.name if vehicle.model_id else ''}"
                        ),
                    }
                    for vehicle in vehicles
                ]
            }
        )


def mobile_vehicle_payload(vehicle):
    return {
        "id": vehicle.id,
        "registration_no": vehicle.registration_no,
        "customer_id": vehicle.customer_id,
        "customer": vehicle.customer.name if vehicle.customer_id else "",
        "customer_mobile": vehicle.customer.mobile_no if vehicle.customer_id else "",
        "model_id": vehicle.model_id,
        "model": vehicle.model.name if vehicle.model_id else "",
        "variant_id": vehicle.variant_id,
        "variant": vehicle.variant.name if vehicle.variant_id else "",
        "chassis_no": vehicle.chassis_no or "",
        "engine_no": vehicle.engine_no or "",
        "color": vehicle.color or "",
        "sale_date": vehicle.sale_date.isoformat() if vehicle.sale_date else "",
        "vehicle_type": vehicle.vehicle_type or "",
    }


class MobileVehicleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        vehicles = Vehicle.objects.select_related("customer", "model", "variant")
        if query:
            vehicles = vehicles.filter(
                Q(registration_no__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(customer__mobile_no__icontains=query)
                | Q(model__name__icontains=query)
                | Q(variant__name__icontains=query)
            )

        return Response(
            {
                "vehicles": [
                    mobile_vehicle_payload(vehicle)
                    for vehicle in vehicles.order_by("registration_no")[:100]
                ]
            }
        )


class MobileVehicleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        vehicle = (
            Vehicle.objects.select_related("customer", "model", "variant")
            .filter(pk=pk)
            .first()
        )
        if not vehicle:
            return Response({"detail": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"vehicle": mobile_vehicle_payload(vehicle)})


class MobileCustomerSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        if len(query) < 2:
            return Response({"customers": []})

        customers = (
            Customer.objects.filter(
                Q(name__icontains=query)
                | Q(mobile_no__icontains=query)
                | Q(email__icontains=query)
                | Q(customer_code__icontains=query)
                | Q(whatsapp_no__icontains=query)
                | Q(company_name__icontains=query)
            )
            .order_by("name")[:15]
        )

        return Response(
            {
                "customers": [
                    {
                        "id": customer.id,
                        "name": customer.name,
                        "mobile_no": customer.mobile_no or "",
                        "email": customer.email or "",
                        "city": customer.city or "",
                        "customer_code": customer.customer_code or "",
                        "customer_type": customer.customer_type or "",
                        "label": f"{customer.name} | {customer.mobile_no or '-'}",
                    }
                    for customer in customers
                ]
            }
        )


def mobile_customer_payload(customer):
    return {
        "id": customer.id,
        "customer_code": customer.customer_code or "",
        "customer_type": customer.customer_type or "Individual",
        "salutation": customer.salutation or "",
        "name": customer.name,
        "gender": customer.gender or "",
        "date_of_birth": customer.date_of_birth.isoformat() if customer.date_of_birth else "",
        "anniversary_date": customer.anniversary_date.isoformat() if customer.anniversary_date else "",
        "gst_registered": customer.gst_registered,
        "pan_no": customer.pan_no or "",
        "aadhaar_no": customer.aadhaar_no or "",
        "mobile_no": customer.mobile_no or "",
        "alternate_mobile_no": customer.alternate_mobile_no or "",
        "whatsapp_no": customer.whatsapp_no or "",
        "email": customer.email or "",
        "preferred_contact_method": customer.preferred_contact_method or "Mobile",
        "address_line_1": customer.address_line_1 or "",
        "address_line_2": customer.address_line_2 or "",
        "city": customer.city or "",
        "state": customer.state or "",
        "address": customer.address or "",
        "gst_no": customer.gst_no or "",
        "pin_code": customer.pin_code or "",
        "country": customer.country or "India",
        "company_name": customer.company_name or "",
        "contact_person": customer.contact_person or "",
        "designation": customer.designation or "",
        "company_gst_no": customer.company_gst_no or "",
        "is_active": customer.is_active,
    }


class MobileCustomerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        customers = Customer.objects.all()
        if query:
            customers = customers.filter(
                Q(name__icontains=query)
                | Q(mobile_no__icontains=query)
                | Q(email__icontains=query)
                | Q(city__icontains=query)
                | Q(customer_code__icontains=query)
                | Q(whatsapp_no__icontains=query)
                | Q(company_name__icontains=query)
            )

        return Response(
            {
                "customers": [
                    mobile_customer_payload(customer)
                    for customer in customers.order_by("name")[:100]
                ]
            }
        )


class MobileCustomerSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        data = request.data or {}
        name = clean_text(data.get("name"))
        mobile_no = clean_text(data.get("mobileNo"))
        customer_type = clean_text(data.get("customerType")) or "Individual"
        gst_registered = bool(data.get("gstRegistered"))
        customer = Customer.objects.filter(pk=pk).first() if pk else None
        errors = {}

        if pk and not customer:
            return Response({"detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        if not name:
            errors["name"] = "Customer Name required."
        if customer_type not in dict(Customer.CUSTOMER_TYPE_CHOICES):
            errors["customerType"] = "Invalid Customer Type."
        if gst_registered and not clean_text(data.get("gstNo")):
            errors["gstNo"] = "GST No required when GST Registered is Yes."
        mobile_qs = Customer.objects.filter(mobile_no=mobile_no) if mobile_no else Customer.objects.none()
        if customer:
            mobile_qs = mobile_qs.exclude(pk=customer.pk)
        if mobile_no and mobile_qs.exists():
            errors["mobileNo"] = "Customer Mobile already exists."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        if not customer:
            customer = Customer()

        customer.customer_type = customer_type
        customer.salutation = clean_text(data.get("salutation"))
        customer.name = name
        customer.gender = clean_text(data.get("gender"))
        customer.date_of_birth = parse_date(clean_text(data.get("dateOfBirth"))) if clean_text(data.get("dateOfBirth")) else None
        customer.anniversary_date = parse_date(clean_text(data.get("anniversaryDate"))) if clean_text(data.get("anniversaryDate")) else None
        customer.gst_registered = gst_registered
        customer.pan_no = clean_text(data.get("panNo")) or None
        customer.aadhaar_no = clean_text(data.get("aadhaarNo")) or None
        customer.mobile_no = mobile_no or None
        customer.alternate_mobile_no = clean_text(data.get("alternateMobileNo")) or None
        customer.whatsapp_no = clean_text(data.get("whatsappNo")) or None
        customer.email = clean_text(data.get("email")) or None
        customer.preferred_contact_method = clean_text(data.get("preferredContactMethod")) or "Mobile"
        customer.address_line_1 = clean_text(data.get("addressLine1")) or None
        customer.address_line_2 = clean_text(data.get("addressLine2")) or None
        customer.city = clean_text(data.get("city")) or None
        customer.state = clean_text(data.get("state")) or None
        customer.address = clean_text(data.get("address")) or None
        customer.gst_no = clean_text(data.get("gstNo")) or None
        customer.pin_code = clean_text(data.get("pinCode")) or None
        customer.country = clean_text(data.get("country")) or "India"
        customer.company_name = clean_text(data.get("companyName")) or None
        customer.contact_person = clean_text(data.get("contactPerson")) or None
        customer.designation = clean_text(data.get("designation")) or None
        customer.company_gst_no = clean_text(data.get("companyGstNo")) or None
        customer.save()

        return Response(
            {
                "message": "Customer saved successfully.",
                "customer": mobile_customer_payload(customer),
            },
            status=status.HTTP_201_CREATED if not pk else status.HTTP_200_OK,
        )


class MobileVehicleModelCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = clean_text((request.data or {}).get("name"))
        if not name:
            return Response(
                {"errors": {"name": "Model Name required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = VehicleModel.objects.filter(name__iexact=name).first()
        created = False
        if not model:
            model = VehicleModel.objects.create(name=name)
            created = True
        return Response(
            {
                "message": "Vehicle model created successfully." if created else "Vehicle model already exists.",
                "model": {"id": model.id, "label": model.name},
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MobileVehicleVariantCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        name = clean_text(data.get("name"))
        model = get_optional(VehicleModel, data.get("model"))
        errors = {}

        if not model:
            errors["model"] = "Select Vehicle Model first."
        if not name:
            errors["name"] = "Variant Name required."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        variant = VehicleVariant.objects.filter(
            model=model,
            name__iexact=name,
        ).first()
        created = False
        if not variant:
            variant = VehicleVariant.objects.create(model=model, name=name)
            created = True
        return Response(
            {
                "message": "Vehicle variant created successfully." if created else "Vehicle variant already exists.",
                "variant": {
                    "id": variant.id,
                    "label": variant.name,
                    "model_id": variant.model_id,
                },
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MobileVehicleCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        errors = {}

        registration_no = clean_text(data.get("registrationNo")).upper()
        customer_name = clean_text(data.get("customerName"))
        customer_mobile = clean_text(data.get("customerMobile"))
        customer_id = data.get("customerId")
        chassis_no = clean_text(data.get("chassisNo")).upper()
        engine_no = clean_text(data.get("engineNo")).upper()
        color = clean_text(data.get("color"))
        sale_date = parse_mobile_date(data.get("saleDate"))
        vehicle_type = clean_text(data.get("vehicleType")) or "PV"
        model = get_optional(VehicleModel, data.get("model"))
        variant = get_optional(VehicleVariant, data.get("variant"))

        if not registration_no:
            errors["registrationNo"] = "Vehicle Registration No required."
        elif Vehicle.objects.filter(registration_no__iexact=registration_no).exists():
            errors["registrationNo"] = "Vehicle Registration No already exists."

        selected_customer = get_optional(Customer, customer_id)

        if not selected_customer and not customer_name:
            errors["customerName"] = "Customer Name required."
        if not chassis_no:
            errors["chassisNo"] = "Chassis No required."
        elif Vehicle.objects.filter(chassis_no__iexact=chassis_no).exists():
            errors["chassisNo"] = "Chassis No already exists."

        if not engine_no:
            errors["engineNo"] = "Engine No required."
        elif Vehicle.objects.filter(engine_no__iexact=engine_no).exists():
            errors["engineNo"] = "Engine No already exists."

        if not model:
            errors["model"] = "Vehicle Model required."
        if not variant:
            errors["variant"] = "Vehicle Variant required."
        if not color:
            errors["color"] = "Color required."
        if not sale_date:
            errors["saleDate"] = "Sale Date required."
        if vehicle_type not in dict(Vehicle.VEHICLE_TYPE_CHOICES):
            errors["vehicleType"] = "Select valid Vehicle Type."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            customer = selected_customer
            if not customer and customer_mobile:
                customer = Customer.objects.filter(mobile_no=customer_mobile).first()
            if not customer:
                customer = Customer.objects.create(
                    name=customer_name,
                    mobile_no=customer_mobile or None,
                )

            vehicle = Vehicle.objects.create(
                registration_no=registration_no,
                chassis_no=chassis_no,
                engine_no=engine_no,
                model=model,
                variant=variant,
                color=color,
                sale_date=sale_date,
                vehicle_type=vehicle_type,
                customer=customer,
            )

        return Response(
            {
                "message": "Vehicle created successfully.",
                "vehicle": {
                    "id": vehicle.id,
                    "registration_no": vehicle.registration_no,
                    "customer": customer.name,
                    "mobile_no": customer.mobile_no or "",
                    "model": model.name,
                    "variant": variant.name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MobileVehicleSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        data = request.data or {}
        errors = {}

        vehicle = Vehicle.objects.filter(pk=pk).first() if pk else None
        if pk and not vehicle:
            return Response({"detail": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND)

        registration_no = clean_text(data.get("registrationNo")).upper()
        customer_name = clean_text(data.get("customerName"))
        customer_mobile = clean_text(data.get("customerMobile"))
        customer_id = data.get("customerId")
        chassis_no = clean_text(data.get("chassisNo")).upper()
        engine_no = clean_text(data.get("engineNo")).upper()
        color = clean_text(data.get("color"))
        sale_date = parse_mobile_date(data.get("saleDate"))
        vehicle_type = clean_text(data.get("vehicleType")) or "PV"
        model = get_optional(VehicleModel, data.get("model"))
        variant = get_optional(VehicleVariant, data.get("variant"))
        selected_customer = get_optional(Customer, customer_id)

        registration_qs = Vehicle.objects.filter(registration_no__iexact=registration_no) if registration_no else Vehicle.objects.none()
        chassis_qs = Vehicle.objects.filter(chassis_no__iexact=chassis_no) if chassis_no else Vehicle.objects.none()
        engine_qs = Vehicle.objects.filter(engine_no__iexact=engine_no) if engine_no else Vehicle.objects.none()
        if vehicle:
            registration_qs = registration_qs.exclude(pk=vehicle.pk)
            chassis_qs = chassis_qs.exclude(pk=vehicle.pk)
            engine_qs = engine_qs.exclude(pk=vehicle.pk)

        if not registration_no:
            errors["registrationNo"] = "Vehicle Registration No required."
        elif registration_qs.exists():
            errors["registrationNo"] = "Vehicle Registration No already exists."

        if not selected_customer and not customer_name:
            errors["customerName"] = "Customer Name required."
        if not chassis_no:
            errors["chassisNo"] = "Chassis No required."
        elif chassis_qs.exists():
            errors["chassisNo"] = "Chassis No already exists."

        if not engine_no:
            errors["engineNo"] = "Engine No required."
        elif engine_qs.exists():
            errors["engineNo"] = "Engine No already exists."

        if not model:
            errors["model"] = "Vehicle Model required."
        if not variant:
            errors["variant"] = "Vehicle Variant required."
        elif model and variant.model_id != model.id:
            errors["variant"] = "Select variant for selected model."
        if not color:
            errors["color"] = "Color required."
        if not sale_date:
            errors["saleDate"] = "Sale Date required."
        if vehicle_type not in dict(Vehicle.VEHICLE_TYPE_CHOICES):
            errors["vehicleType"] = "Select valid Vehicle Type."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            customer = selected_customer
            if not customer and customer_mobile:
                customer = Customer.objects.filter(mobile_no=customer_mobile).first()
            if not customer:
                customer = Customer.objects.create(
                    name=customer_name,
                    mobile_no=customer_mobile or None,
                )

            if not vehicle:
                vehicle = Vehicle()
            vehicle.registration_no = registration_no
            vehicle.chassis_no = chassis_no
            vehicle.engine_no = engine_no
            vehicle.model = model
            vehicle.variant = variant
            vehicle.color = color
            vehicle.sale_date = sale_date
            vehicle.vehicle_type = vehicle_type
            vehicle.customer = customer
            vehicle.save()

        return Response(
            {
                "message": "Vehicle saved successfully.",
                "vehicle": mobile_vehicle_payload(vehicle),
            },
            status=status.HTTP_201_CREATED if not pk else status.HTTP_200_OK,
        )
