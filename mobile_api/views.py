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
    Employee,
    InsuranceCompany,
    JobCard,
    Surveyor,
    Customer,
    Vehicle,
    VehicleModel,
    VehicleVariant,
    WorkProgress,
    WorkProgressPhoto,
    UserNotification,
)
from rbac.models import Menu, RoleMenuPermission, UserMenuPermission

from .serializers import MobileLoginSerializer


def generate_mobile_claim_no():
    year = timezone.localdate().year
    last = Claim.objects.order_by("-id").first()
    number = (last.id + 1) if last else 1
    return f"CLM-{year}-{number:04d}"


def clean_text(value):
    return str(value or "").strip()


def decimal_or_zero(value):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


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
        "has_jobcard": bool(jobcard),
        "jobcard_id": jobcard.id if jobcard else "",
        "job_no": jobcard.job_no if jobcard else "",
        "jobcard_repair_status": jobcard.repair_status if jobcard else "",
        "work_allocation_created": bool(allocation),
        "repair_progress_started": repair_progress_started,
        "work_completed": work_completed,
        "registration_no": vehicle.registration_no if vehicle else "",
        "customer": customer.name if customer else "",
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
        },
        "roles": list(user.groups.values_list("name", flat=True)),
    }


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
    employee = Employee.objects.filter(user=user).first()

    if user.is_superuser:
        return Claim.objects.all(), JobCard.objects.all()

    if employee and employee.employee_type in ["MANAGER", "ADMIN"]:
        return Claim.objects.all(), JobCard.objects.all()

    if employee and employee.employee_type == "Advisor":
        return (
            Claim.objects.filter(employee=employee),
            JobCard.objects.filter(advisor=employee),
        )

    if employee and employee.employee_type in ["STAFF", "RECEPTION"]:
        return Claim.objects.filter(employee__isnull=True), JobCard.objects.none()

    return Claim.objects.none(), JobCard.objects.none()


def is_mobile_repair_resource(employee):
    if not employee:
        return False

    role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
    return any(
        keyword in role_text
        for keyword in ["TECHNICIAN", "DENTER", "PAINTER"]
    )


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
            claims.select_related("vehicle", "vehicle__customer", "employee")
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


class MobileNextClaimNoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"claim_no": generate_mobile_claim_no()})


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

        insurance_company = get_optional(InsuranceCompany, data.get("insuranceCompany"))
        advisor = get_optional(Employee, data.get("advisor"))
        surveyor = get_optional(Surveyor, data.get("surveyor"))
        delivered_by = get_optional(Employee, data.get("deliveredBy"))

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
                        else generate_mobile_claim_no()
                    ),
                    vehicle=vehicle,
                )
            else:
                claim.vehicle = vehicle

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

            claim.claim_stage = derive_claim_stage(claim)
            claim.status = "Closed" if claim.claim_stage == ClaimStageCode.CLOSED else "Open"
            claim.save()

        return Response(
            {
                "message": "Claim saved successfully.",
                "claim": mobile_claim_payload(claim),
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


class MobileClaimEntryOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        advisors = Employee.objects.filter(
            employee_type="Advisor",
            is_active=True,
        ).order_by("name")

        employees = Employee.objects.filter(
            is_active=True,
        ).order_by("name")

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
                        "label": f"{customer.name} | {customer.mobile_no or '-'}",
                    }
                    for customer in customers
                ]
            }
        )


def mobile_customer_payload(customer):
    return {
        "id": customer.id,
        "name": customer.name,
        "mobile_no": customer.mobile_no or "",
        "email": customer.email or "",
        "city": customer.city or "",
        "state": customer.state or "",
        "address": customer.address or "",
        "gst_no": customer.gst_no or "",
        "pin_code": customer.pin_code or "",
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
        customer = Customer.objects.filter(pk=pk).first() if pk else None
        errors = {}

        if pk and not customer:
            return Response({"detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        if not name:
            errors["name"] = "Customer Name required."
        mobile_qs = Customer.objects.filter(mobile_no=mobile_no) if mobile_no else Customer.objects.none()
        if customer:
            mobile_qs = mobile_qs.exclude(pk=customer.pk)
        if mobile_no and mobile_qs.exists():
            errors["mobileNo"] = "Customer Mobile already exists."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        if not customer:
            customer = Customer()

        customer.name = name
        customer.mobile_no = mobile_no or None
        customer.email = clean_text(data.get("email")) or None
        customer.city = clean_text(data.get("city")) or None
        customer.state = clean_text(data.get("state")) or None
        customer.address = clean_text(data.get("address")) or None
        customer.gst_no = clean_text(data.get("gstNo")) or None
        customer.pin_code = clean_text(data.get("pinCode")) or None
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
