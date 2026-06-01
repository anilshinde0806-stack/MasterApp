import math
import os
import zipfile
import base64
from datetime import datetime, time as datetime_time
from io import BytesIO

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from django.contrib.sites import requests
from django.db import IntegrityError
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from psycopg import rows
from xhtml2pdf import pisa

from config import settings
from .forms import VehicleForm, InsuranceCompanyForm, CustomerForm, SurveyorForm, EmployeeForm, JobCardForm
from .models import InsuranceCompany, VehicleModel, Customer, ColumnPreference, Surveyor, JobCardPart, \
    JobCardLabour, JobCardAssessmentPart, JobCardAssessmentLabour, JobCardTyreInventory, \
    CommunicationLog, UserNotification, ClaimStageCode, WorkProgress, WorkAllocation, AnnouncementRead, Announcement, \
    PartOrder, PartOrderHeader, WorkAllocationPart, WorkAllocationLabour, JobCardReInspectionPhoto, \
    JobCardVehicleConditionPhoto, ClaimDocument, WorkProgressPhoto, JobCardAdditionalApprovalPhoto


REINSPECTION_MAX_PHOTOS_PER_JOBCARD = getattr(settings, "REINSPECTION_MAX_PHOTOS_PER_JOBCARD", 25)
REINSPECTION_MAX_IMAGE_SIZE_MB = getattr(settings, "REINSPECTION_MAX_IMAGE_SIZE_MB", 8)
REINSPECTION_MAX_TOTAL_SIZE_MB = getattr(settings, "REINSPECTION_MAX_TOTAL_SIZE_MB", 50)
REINSPECTION_MAX_IMAGE_SIZE_BYTES = REINSPECTION_MAX_IMAGE_SIZE_MB * 1024 * 1024
REINSPECTION_MAX_TOTAL_SIZE_BYTES = REINSPECTION_MAX_TOTAL_SIZE_MB * 1024 * 1024

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

CLAIM_DOCUMENT_TYPES = [
    "RC Book",
    "Driving License",
    "Insurance Policy",
    "Aadhar Card",
    "PAN Card",
    "Claim Form",
    "Other 1",
    "Other 2",
]


def get_reinspection_photo_storage_size(job):
    total_size = 0

    for photo in job.reinspection_photos.all():
        if not photo.image:
            continue

        try:
            total_size += photo.image.size
        except (OSError, ValueError):
            continue

    return total_size


def vehicle_condition_photo_input_name(index):
    return f"vehicle_condition_photo_{index}"


def get_vehicle_condition_photo_slots(job):
    existing = {}
    if job:
        existing = {
            photo.caption: photo
            for photo in job.vehicle_condition_photos.all()
        }

    return [
        {
            "index": index,
            "caption": caption,
            "input_name": vehicle_condition_photo_input_name(index),
            "photo": existing.get(caption),
        }
        for index, caption in enumerate(VEHICLE_CONDITION_PHOTO_CAPTIONS, start=1)
    ]


def save_vehicle_condition_photos(request, job):
    for index, caption in enumerate(VEHICLE_CONDITION_PHOTO_CAPTIONS, start=1):
        image = request.FILES.get(vehicle_condition_photo_input_name(index))
        if not image:
            continue

        photo = JobCardVehicleConditionPhoto.objects.filter(
            job=job,
            caption=caption,
        ).first()

        if photo and photo.image:
            photo.image.delete(save=False)

        if photo:
            photo.image = image
            photo.save()
        else:
            JobCardVehicleConditionPhoto.objects.create(
                job=job,
                caption=caption,
                image=image,
            )


def save_signature_data(job, field_name, data_url):
    data_url = (data_url or "").strip()
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


def save_jobcard_signatures(request, job):
    changed = False
    changed = save_signature_data(
        job,
        "advisor_signature",
        request.POST.get("advisor_signature_data")
    ) or changed
    changed = save_signature_data(
        job,
        "customer_signature",
        request.POST.get("customer_signature_data")
    ) or changed

    if changed:
        job.save(update_fields=["advisor_signature", "customer_signature"])


def claim_document_input_name(index):
    return f"claim_document_{index}"


def get_claim_document_slots(claim):
    existing = {}
    if claim:
        existing = {
            document.document_type: document
            for document in ClaimDocument.objects.filter(claim=claim)
        }

    return [
        {
            "index": index,
            "document_type": document_type,
            "input_name": claim_document_input_name(index),
            "document": existing.get(document_type),
        }
        for index, document_type in enumerate(CLAIM_DOCUMENT_TYPES, start=1)
    ]


def save_claim_documents(request, claim):
    if not claim:
        return

    for index, document_type in enumerate(CLAIM_DOCUMENT_TYPES, start=1):
        uploaded_file = request.FILES.get(claim_document_input_name(index))
        if not uploaded_file:
            continue

        document = ClaimDocument.objects.filter(
            claim=claim,
            document_type=document_type,
        ).first()

        if document and document.file:
            document.file.delete(save=False)

        if document:
            document.file = uploaded_file
            document.save()
        else:
            ClaimDocument.objects.create(
                claim=claim,
                document_type=document_type,
                file=uploaded_file,
            )


def progress_photo_input_name(stage):
    safe_stage = "".join(
        char if char.isalnum() or char in ["-", "_"] else "_"
        for char in str(stage or "")
    )
    return f"progress_photo_{safe_stage}"


def is_repair_resource(employee):
    if not employee:
        return False

    role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
    return any(
        keyword in role_text
        for keyword in ["TECHNICIAN", "DENTER", "PAINTER"]
    )


def is_floor_supervisor(employee):
    if not employee:
        return False

    role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
    return any(
        keyword in role_text
        for keyword in ["FLOOR SUPERVISOR", "FLOOR INCHARGE", "FLOOR IN-CHARGE"]
    )


def workflow_date_value(value):
    if not value:
        return None

    if isinstance(value, datetime):
        if timezone.is_aware(value):
            return timezone.localtime(value)
        return timezone.make_aware(value)

    if hasattr(value, "date"):
        return timezone.make_aware(datetime.combine(value, datetime_time.min))

    return timezone.make_aware(datetime.combine(value, datetime_time.min))


def parse_workflow_datetime(value):
    value = (value or "").strip()
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed:
        return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)

    parsed_date = parse_date(value)
    if parsed_date:
        return timezone.make_aware(datetime.combine(parsed_date, datetime_time.min))

    return None


def datetime_local_value(value):
    if not value:
        return ""

    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%Y-%m-%dT%H:%M")

    return datetime.combine(value, datetime_time.min).strftime("%Y-%m-%dT%H:%M")


def validate_no_future_workflow_dates(points):
    now = timezone.now()

    for label, value in points:
        current_value = control_board_datetime_value(value)
        if current_value and current_value > now:
            return f"{label} cannot be future date/time."

    return ""


def validate_workflow_dates(points, validate_labels=None):
    validate_all = validate_labels is None
    validate_labels = set(validate_labels or [])
    previous_label = None
    previous_date = None

    for label, value in points:
        current_date = workflow_date_value(value)
        if not current_date:
            continue

        should_validate = validate_all or label in validate_labels

        if should_validate and previous_date and current_date < previous_date:
            return (
                f"{label} cannot be before {previous_label}. "
                f"{previous_label}: {previous_date.strftime('%d-%m-%Y %H:%M')}, "
                f"{label}: {current_date.strftime('%d-%m-%Y %H:%M')}"
            )

        previous_label = label
        previous_date = current_date

    return ""


def workflow_date_changed(old_value, new_value):
    old_date = workflow_date_value(old_value)
    new_date = workflow_date_value(new_value)
    return bool(new_date and old_date != new_date)


def validate_claim_job_workflow_dates(
        claim,
        job=None,
        allocation=None,
        claim_created_date=None,
        job_created_date=None,
        validate_labels=None
):
    claim_created_value = claim_created_date or (claim.created_at if claim else None)
    job_created_value = job_created_date or (job.job_date if job else None) or (job.created_at if job else None)
    first_progress = None
    work_completed = None

    if allocation:
        first_progress = (
            allocation.progress
            .filter(start_time__isnull=False)
            .order_by("start_time")
            .first()
        )
        work_completed = (
            allocation.progress
            .filter(finish_time__isnull=False)
            .order_by("-finish_time")
            .first()
        )

    return validate_workflow_dates([
        ("Gate In Date", job.gate_in_datetime if job else None),
        ("Claim Created Date", claim_created_value),
        ("Jobcard Created Date", job_created_value),
        ("Claim Intimation Date", claim.intimation_date if claim else None),
        ("Survey Date", claim.survey_date if claim else None),
        ("Insurance Approval Date", claim.insurance_approval_date if claim else None),
        ("Work Allocation Date", allocation.allotment_date if allocation else None),
        ("Repair Start Date", first_progress.start_time if first_progress else None),
        ("Work Completed Date", work_completed.finish_time if work_completed else None),
        ("Re-Inspection Date", job.reinspection_date if job else None),
        ("Liability Received Date", claim.liability_received_at if claim else None),
        ("Invoice Date", claim.invoice_datetime if claim else None),
        ("Delivery Date", claim.delivery_datetime if claim else None),
    ], validate_labels=validate_labels)


def my_work_base_queryset(employee, from_date=None, to_date=None):
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


def apply_my_work_status_filter(progress, status_filter):
    if status_filter == "wip":
        return progress.filter(start_time__isnull=False, finish_time__isnull=True)

    if status_filter == "completed":
        return progress.filter(finish_time__isnull=False)

    return progress.filter(start_time__isnull=True)


def my_work_row_payload(progress):
    job = progress.allocation.job if progress.allocation_id else None
    claim = job.claim if job and job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None

    return {
        "id": progress.id,
        "stage": progress.stage,
        "stage_label": progress.get_stage_display(),
        "start_time": progress.start_time,
        "finish_time": progress.finish_time,
        "remarks": progress.remarks or "",
        "photo_count": progress.photos.count(),
        "job": job,
        "claim": claim,
        "vehicle": vehicle,
        "additional_approval_required": bool(
            job and job.additional_approval_required
        ),
        "second_approval_status": (
            job.second_approval_status
            if job
            else ""
        ),
        "additional_approval_reason": (
            job.additional_approval_reason
            if job
            else ""
        ),
    }


def start_work_progress(progress):
    if not progress.start_time:
        progress.start_time = timezone.now()
        progress.save(update_fields=["start_time"])
        return True
    return False


def finish_work_progress(progress):
    changed = False
    if not progress.start_time:
        progress.start_time = timezone.now()
        changed = True
    if not progress.finish_time:
        progress.finish_time = timezone.now()
        changed = True
    progress.save(update_fields=["start_time", "finish_time"])
    return changed


def save_work_progress_uploaded_photos(request, progress):
    for image in request.FILES.getlist("progress_photos"):
        WorkProgressPhoto.objects.create(
            progress=progress,
            image=image
        )


def is_admin_or_manager_user(user, employee=None):
    if not user or not user.is_authenticated:
        return False

    role_text = f"{employee.employee_type if employee else ''} {employee.designation if employee else ''}".upper()
    return (
        user.is_superuser
        or "MANAGER" in role_text
        or "ADMIN" in role_text
        or user.groups.filter(name__iexact="Manager").exists()
    )


def create_user_notification(user, title, message, url=""):
    if not user:
        return

    UserNotification.objects.create(
        user=user,
        title=title,
        message=message,
        url=url or "",
    )


def notify_jobcard_advisor(job, title, message):
    if not job:
        return

    advisor_user = None
    if job.advisor_id and job.advisor and job.advisor.user_id:
        advisor_user = job.advisor.user
    elif job.claim_id and job.claim and job.claim.employee_id and job.claim.employee.user_id:
        advisor_user = job.claim.employee.user

    create_user_notification(
        advisor_user,
        title,
        message,
        f"/jobCard/{job.id}/edit/",
    )


def floor_incharge_users():
    employees = Employee.objects.filter(
        is_active=True,
        user__isnull=False,
    )
    users = []
    seen_user_ids = set()

    for employee in employees:
        role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()

        if not any(
            keyword in role_text
            for keyword in ["FLOOR INCHARGE", "FLOOR IN-CHARGE", "FLOOR SUPERVISOR"]
        ):
            continue

        if employee.user_id in seen_user_ids:
            continue

        users.append(employee.user)
        seen_user_ids.add(employee.user_id)

    return users


def notify_floor_incharge_work_allocated(job):
    if not job:
        return

    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    registration_no = vehicle.registration_no if vehicle else "-"
    model_name = vehicle.model.name if vehicle and vehicle.model_id else "-"
    message = (
        f"Work allocated for Jobcard {job.job_no} "
        f"({registration_no} - {model_name})"
    )

    for user in floor_incharge_users():
        create_user_notification(
            user,
            "Work Allocated",
            message,
            f"/work-allocation/{job.id}/",
        )


def notify_floor_incharge_work_allocation_pending(claim):
    if not claim:
        return

    job = JobCard.objects.filter(claim=claim).select_related(
        "claim",
        "claim__vehicle",
        "claim__vehicle__model",
    ).first()
    vehicle = claim.vehicle if claim.vehicle_id else None
    registration_no = vehicle.registration_no if vehicle else "-"
    model_name = vehicle.model.name if vehicle and vehicle.model_id else "-"
    job_no = job.job_no if job else "-"
    url = f"/work-allocation/{job.id}/" if job else f"/claim/{claim.id}/edit/"
    message = (
        f"Claim {claim.claim_no} moved to Work Allocation. "
        f"Jobcard {job_no} ({registration_no} - {model_name})"
    )

    for user in floor_incharge_users():
        create_user_notification(
            user,
            "Work Allocation Pending",
            message,
            url,
        )


def notify_progress_employee_assigned(progress):
    if not progress or not progress.employee_id or not progress.employee.user_id:
        return

    if not is_repair_resource(progress.employee):
        return

    job = progress.allocation.job if progress.allocation_id else None
    if not job:
        return

    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    registration_no = vehicle.registration_no if vehicle else "-"
    model_name = vehicle.model.name if vehicle and vehicle.model_id else "-"
    message = (
        f"{progress.get_stage_display()} assigned for "
        f"Jobcard {job.job_no} ({registration_no} - {model_name})"
    )

    create_user_notification(
        progress.employee.user,
        "New Work Assigned",
        message,
        "/my-work/",
    )


def notify_floor_incharge_work_progress(progress, action_label):
    job = progress.allocation.job if progress and progress.allocation_id else None
    if not job:
        return

    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    registration_no = vehicle.registration_no if vehicle else "-"
    employee_name = progress.employee.name if progress.employee_id else "-"
    message = (
        f"{employee_name} {action_label} "
        f"{progress.get_stage_display()} for Jobcard {job.job_no} "
        f"({registration_no})"
    )

    for user in floor_incharge_users():
        create_user_notification(
            user,
            "Work Progress Updated",
            message,
            f"/work-allocation/{job.id}/",
        )


def notify_work_progress_change(progress, action_label):
    job = progress.allocation.job if progress and progress.allocation_id else None
    if not job:
        return

    vehicle = job.claim.vehicle if job.claim_id and job.claim and job.claim.vehicle_id else None
    registration_no = vehicle.registration_no if vehicle else "-"
    message = (
        f"Jobcard {job.job_no} {progress.get_stage_display()} "
        f"{action_label} for {registration_no}"
    )
    notify_jobcard_advisor(
        job,
        "Repair Work Progress Updated",
        message,
    )

    if action_label in ["started", "finished"]:
        notify_floor_incharge_work_progress(progress, action_label)


def can_update_second_approval(user, employee, job):
    if is_admin_or_manager_user(user, employee):
        return True

    if not employee or not job:
        return False

    return (
        (job.advisor_id and job.advisor_id == employee.id)
        or (
            job.claim_id
            and job.claim
            and job.claim.employee_id == employee.id
        )
    )


# Create your views here.
@login_required
@login_required
def dashboard(request):
    from datetime import date
    from django.utils.dateparse import parse_date

    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    if is_repair_resource(logged_emp):
        return redirect("my_work_list")

    if is_floor_supervisor(logged_emp):
        return redirect("work_allocation_list")

    claims = Claim.objects.none()
    jobcards = JobCard.objects.none()

    show_manager_dashboard = False

    # ADMIN
    if request.user.is_superuser:

        claims = Claim.objects.all()
        jobcards = JobCard.objects.all()
        show_manager_dashboard = True

    # MANAGER
    elif logged_emp and logged_emp.employee_type == "MANAGER":

        claims = Claim.objects.all()
        jobcards = JobCard.objects.all()
        show_manager_dashboard = True

    # ADVISOR
    elif logged_emp and logged_emp.employee_type == "Advisor":

        claims = Claim.objects.filter(
            employee=logged_emp
        )

        jobcards = JobCard.objects.filter(
            advisor=logged_emp
        )

    # STAFF / RECEPTION
    elif logged_emp and logged_emp.employee_type in [
        "STAFF",
        "RECEPTION",
        "ADMIN",
    ]:

        claims = Claim.objects.filter(
            employee__isnull=True
        )

    today = date.today()
    default_from_date = today.replace(day=1)
    from_date = parse_date(request.GET.get("from_date") or "") or default_from_date
    to_date = parse_date(request.GET.get("to_date") or "") or today
    status_scope = request.GET.get("status_scope") or ""
    main_status = request.GET.get("main_status") or ""
    advisor_id = request.GET.get("advisor") or ""

    if from_date:
        claims = claims.filter(created_at__date__gte=from_date)
        jobcards = jobcards.filter(created_at__date__gte=from_date)

    if to_date:
        claims = claims.filter(created_at__date__lte=to_date)
        jobcards = jobcards.filter(created_at__date__lte=to_date)

    if advisor_id:
        claims = claims.filter(employee_id=advisor_id)
        jobcards = jobcards.filter(advisor_id=advisor_id)

    if main_status:
        if status_scope == "claim":
            claims = claims.filter(status=main_status)
        elif status_scope == "jobcard":
            jobcards = jobcards.filter(repair_status=main_status)
        else:
            claims = claims.filter(status=main_status)
            jobcards = jobcards.filter(repair_status=main_status)

    advisor_options = Employee.objects.filter(
        is_active=True
    ).filter(
        Q(employee_type__iexact="Advisor")
        | Q(designation__iexact="Advisor")
    ).order_by("name")

    # MANAGER REPORT DEFAULTS
    total_claims = 0
    pending_claims = 0
    closed_claims = 0
    work_allocation_pending = 0
    repair_in_progress = 0
    total_estimate_value = 0

    stage_counts = []
    advisor_counts = []
    recent_jobs = []

    if show_manager_dashboard:
        total_claims = claims.count()

        pending_claims = claims.exclude(
            claim_stage=ClaimStageCode.CLOSED
        ).count()

        closed_claims = claims.filter(
            claim_stage=ClaimStageCode.CLOSED
        ).count()

        work_allocation_pending = claims.filter(
            claim_stage=ClaimStageCode.WORK_ALLOCATION
        ).count()

        repair_in_progress = claims.filter(
            claim_stage=ClaimStageCode.REPAIR_IN_PROGRESS
        ).count()

        stage_counts = (
            claims
            .values("claim_stage")
            .annotate(total=Count("id"))
            .order_by("claim_stage")
        )

        advisor_counts = (
            claims
            .values("employee__name")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )

        recent_jobs = (
            jobcards
            .select_related(
                "claim",
                "claim__vehicle",
                "advisor"
            )
            .order_by("-id")[:10]
        )

        total_estimate_value = (
                jobcards
                .aggregate(total=Sum("grand_total"))
                .get("total") or 0
        )

    return render(request, "index.html", {
        "logged_emp": logged_emp,

        "claims": claims,
        "jobcards": jobcards,

        "show_manager_dashboard": show_manager_dashboard,

        "total_claims": total_claims,
        "pending_claims": pending_claims,
        "closed_claims": closed_claims,
        "work_allocation_pending": work_allocation_pending,
        "repair_in_progress": repair_in_progress,
        "stage_counts": stage_counts,
        "advisor_counts": advisor_counts,
        "recent_jobs": recent_jobs,
        "total_estimate_value": total_estimate_value,
        "advisor_options": advisor_options,
        "filter_from_date": from_date.strftime("%Y-%m-%d"),
        "filter_to_date": to_date.strftime("%Y-%m-%d"),
        "filter_status_scope": status_scope,
        "filter_main_status": main_status,
        "filter_advisor": advisor_id,
        "claim_status_choices": Claim.STATUS_CHOICES,
        "jobcard_status_choices": [
            ("Open", "Open"),
            ("Completed", "Completed"),
            ("Closed", "Closed"),
            ("Cancellation", "Cancellation"),
        ],
    })


@login_required
def register_view(request):
    if not request.user.is_superuser:
        messages.error(request, "Only Admin can create users.")
        return redirect("dashboard")

    if request.method == 'POST':  # ✅ use uppercase
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # ✅ redirect after success
        else:
            # Invalid form → re-render with errors
            return render(request, "registration/register.html", {"form": form})
    else:
        # GET request → show blank form
        form = UserCreationForm()
        return render(request, "registration/register.html", {"form": form})


def logout_view(request):
    # ✅ Remove cart data if it exists
    # request.session.pop('cart', {})

    request.session.flush()

    # ✅ Log out the user
    logout(request)

    # ✅ Redirect to homepage
    return redirect('login')  # 'home' should be the name of your homepage URLlogin_required


@login_required
def insurance_list(request):
    context = {

        "breadcrumbs": [

            {
                "title": "Master",
                "icon": "fa fa-database"
            },

            {
                "title": "Insurance List",
                "icon": "fa fa-users"
            }
        ]
    }
    return render(request, 'insurance/list.html', context)


@login_required
def insurance_data(request):
    data = list(InsuranceCompany.objects.values())
    return JsonResponse({'data': data})


@login_required
def insurance_get(request, pk):
    obj = get_object_or_404(InsuranceCompany, pk=pk)
    return JsonResponse({
        'id': obj.id,
        'ins_co_name': obj.ins_co_name,
        'city': obj.city,
        'mobile_no': obj.mobile_no,
    })


@login_required
def insurance_save(request):
    if request.method == 'POST':
        pk = request.POST.get('id')

        if pk:
            obj = get_object_or_404(InsuranceCompany, pk=pk)
            form = InsuranceCompanyForm(request.POST, instance=obj)
        else:
            form = InsuranceCompanyForm(request.POST)

        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})

        return JsonResponse({'success': False, 'errors': form.errors})


@login_required
def insurance_edit(request, pk):
    obj = get_object_or_404(InsuranceCompany, pk=pk)
    form = InsuranceCompanyForm(request.POST or None, instance=obj)

    if form.is_valid():
        form.save()
        return redirect('insurance')

    return render(request, 'insurance/edit.html', {'form': form})


@login_required
def vehicle_list(request):
    return render(request, 'master/vehicle_list.html')


from .models import VehicleVariant


@login_required
def load_variants(request):
    model_id = request.GET.get('model_id')
    variants = VehicleVariant.objects.filter(model_id=model_id).values('id', 'name')
    return JsonResponse(list(variants), safe=False)


@never_cache
@login_required
def vehicle_list_api(request):
    data = list(
        Vehicle.objects.select_related('model', 'variant', 'customer')
        .values(
            'id',
            'registration_no',
            'chassis_no',
            'engine_no',
            'model__name',
            'variant__name',
            'color',
            'sale_date',
            'vehicle_type',
            'customer',
            'customer__name'
        )
    )
    return JsonResponse(data, safe=False)


from .models import Vehicle

from django.views.decorators.http import require_POST


@require_POST
@login_required
def vehicle_update_api(request, pk):
    try:
        vehicle = get_object_or_404(Vehicle, pk=pk)

        customer_id = request.POST.get("customer")
        model_id = request.POST.get("model")
        variant_id = request.POST.get("variant")

        if customer_id:
            vehicle.customer_id = customer_id

        if model_id:
            vehicle.model_id = model_id

        if variant_id:
            vehicle.variant_id = variant_id

        vehicle.registration_no = request.POST.get(
            "registration_no",
            vehicle.registration_no
        )

        vehicle.chassis_no = request.POST.get(
            "chassis_no",
            vehicle.chassis_no
        )

        vehicle.engine_no = request.POST.get(
            "engine_no",
            vehicle.engine_no
        )

        vehicle.color = request.POST.get(
            "color",
            vehicle.color
        )

        vehicle.vehicle_type = request.POST.get(
            "vehicle_type",
            vehicle.vehicle_type
        )

        vehicle.save()

        return JsonResponse({
            "status": "success",
            "id": vehicle.id
        })

    except Exception as e:

        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)


@login_required
def vehicle_create(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)

        if form.is_valid():
            vehicle = form.save()

            return JsonResponse({
                "status": "success",
                "id": vehicle.id,
                "text": f"{vehicle.registration_no} - {vehicle.model.name if vehicle.model else ''}"
            })

        return JsonResponse({
            'status': 'error',
            'errors': form.errors
        })

    # ✅ THIS WAS MISSING (GET REQUEST)
    form = VehicleForm()
    models = VehicleModel.objects.all().order_by("name")
    return render(request, 'master/vehicle_list.html', {
        'form': form,
        "models": models
    })


@login_required
def check_registration(request):
    reg = request.GET.get('registration_no')

    exists = Vehicle.objects.filter(
        registration_no__iexact=reg
    ).exists()

    return JsonResponse({
        'exists': exists
    })


@login_required
def add_model_ajax(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name").strip()

        if VehicleModel.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                "status": "error",
                "message": "Model already exists"
            })

        model = VehicleModel.objects.create(name=name)

        return JsonResponse({
            "status": "success",
            "id": model.id,
            "name": model.name
        })


@login_required
def add_variant_ajax(request):
    if request.method == "POST":
        data = json.loads(request.body)

        model_id = data.get('model_id')
        name = data.get('name').strip()

        if VehicleVariant.objects.filter(model_id=model_id, name__iexact=name).exists():
            return JsonResponse({
                "status": "error",
                "message": "Variant already exists for this model"
            })

        variant = VehicleVariant.objects.create(
            model_id=model_id,
            name=name
        )

        return JsonResponse({
            "status": "success",
            "id": variant.id,
            "name": variant.name
        })


@login_required
def check_customer(request):
    name = request.GET.get("name", "").strip()
    mobile = request.GET.get("mobile", "").strip()

    exists = Customer.objects.filter(
        name__iexact=name,
        mobile_no=mobile
    ).exists()

    return JsonResponse({"exists": exists})


@login_required
def customer_search(request):
    term = request.GET.get('term')

    customers = Customer.objects.filter(
        name__icontains=term
    )[:10]

    results = [
        {
            'id': c.id,
            'text': f"{c.name} ({c.mobile_no})"
        }
        for c in customers
    ]

    return JsonResponse({'results': results})


@login_required
def add_customer(request):
    data = json.loads(request.body)

    name = data.get("name", "").strip()
    mobile = data.get("mobile", "").strip()

    if not name:
        return JsonResponse({"status": "error", "message": "Name required"})

    # 🔥 DUPLICATE CHECK
    existing = Customer.objects.filter(
        name__iexact=name,
        mobile_no=mobile
    ).first()

    if existing:
        return JsonResponse({
            "status": "exists",
            "id": existing.id,
            "text": f"{existing.name} - {existing.mobile_no or ''}",
            "message": "Customer already exists"
        })

    # ✅ CREATE
    customer = Customer.objects.create(
        name=name,
        mobile_no=mobile
    )

    return JsonResponse({
        "status": "success",
        "id": customer.id,
        "text": f"{customer.name} - {customer.mobile_no or ''}"
    })


@login_required
def get_customer_details(request):
    customer_id = request.GET.get("id")

    # ✅ FIX 1: empty check
    if not customer_id:
        return JsonResponse({
            "status": "error",
            "message": "No customer selected"
        })

    # ✅ FIX 2: numeric validation
    if not str(customer_id).isdigit():
        return JsonResponse({
            "status": "error",
            "message": "Invalid customer ID"
        })

    try:
        c = Customer.objects.get(id=customer_id)

        return JsonResponse({
            "status": "success",
            "data": {
                "name": c.name,
                "mobile": c.mobile_no,
                "email": c.email,
                "city": c.city,
                "state": c.state,
                "gst": c.gst_no,
                "address": c.address
            }
        })

    except Customer.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Customer not found"
        })


@login_required
def customer_list(request):
    context = {

        "breadcrumbs": [

            {
                "title": "Master",
                "icon": "fa fa-database"
            },

            {
                "title": "Customer List",
                "icon": "fa fa-users"
            }
        ]
    }

    return render(
        request,
        "master/Customer_list.html",
        context
    )


@login_required
def customer_data(request):
    data = list(Customer.objects.values())
    return JsonResponse({'data': data})


@login_required
def customer_get(request, id):
    obj = Customer.objects.get(id=id)
    return JsonResponse({
        'id': obj.id,
        'name': obj.name,
        'mobile_no': obj.mobile_no,
        'email': obj.email,
        'city': obj.city,
        'gst_no': obj.gst_no
    })


@login_required
def customer_save(request):
    if request.method == "POST":

        obj_id = request.POST.get("id")

        if obj_id:
            obj = Customer.objects.get(id=obj_id)
            form = CustomerForm(request.POST, instance=obj)
        else:
            form = CustomerForm(request.POST)

        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})

        return JsonResponse({
            "success": False,
            "errors": form.errors
        })

    # core/views.py


@login_required
def save_column_pref(request):
    # ✅ Handle GET (for testing / safety)
    if request.method == "GET":
        return JsonResponse({
            "status": "error",
            "message": "Use POST request"
        })

    # ✅ Handle POST
    if request.method == "POST":

        if not request.user.is_authenticated:
            return JsonResponse({
                "status": "error",
                "message": "Login required"
            })

        try:
            data = json.loads(request.body)

            screen = data.get("screen")
            state = data.get("state")
            name = data.get("name", "default")

            if not screen or not state:
                return JsonResponse({
                    "status": "error",
                    "message": "Missing data"
                })

            ColumnPreference.objects.update_or_create(
                user=request.user,
                screen=screen,
                name=name,
                defaults={"state": state}
            )

            return JsonResponse({"status": "success"})

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            })

    # ✅ Fallback (very important)
    return JsonResponse({
        "status": "error",
        "message": "Invalid request"
    })


@login_required
def load_column_pref(request):
    screen = request.GET.get("screen")
    name = request.GET.get("name", "default")

    try:
        pref = ColumnPreference.objects.get(
            user=request.user,
            screen=screen,
            name=name
        )
        return JsonResponse({"state": pref.state})

    except ColumnPreference.DoesNotExist:
        return JsonResponse({"state": []})


@login_required
def surveyor_page(request):
    form = SurveyorForm()
    return render(request, "master/surveyor.html", {"form": form})


@login_required
def surveyor_data(request):
    data = list(Surveyor.objects.values())
    return JsonResponse({"data": data})


@login_required
def surveyor_save(request):
    if request.method == "POST":
        try:
            surveyor_id = request.POST.get("id")

            if surveyor_id and surveyor_id.strip():
                obj = Surveyor.objects.get(id=int(surveyor_id))
                form = SurveyorForm(request.POST, instance=obj)
            else:
                form = SurveyorForm(request.POST)

            if form.is_valid():
                obj = form.save()
                return JsonResponse({"success": True, "id": obj.id})

            return JsonResponse({"success": False, "errors": form.errors})

        except IntegrityError:
            return JsonResponse({
                "success": False,
                "errors": {"mobile_no": ["Duplicate mobile or license"]}
            })

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def surveyor_get(request, id):
    data = Surveyor.objects.filter(id=id).values().first()
    return JsonResponse(data)


@login_required
def check_surveyor_mobile(request):
    mobile = request.GET.get("mobile")

    exists = Surveyor.objects.filter(mobile_no=mobile).exists()

    return JsonResponse({"exists": exists})


@login_required
def employee_page(request):
    form = EmployeeForm()
    return render(request, "master/employee.html", {"form": form})


@login_required
def employee_data(request):
    data = list(Employee.objects.values())
    return JsonResponse({"data": data})


@login_required
def employee_save(request):
    if request.method == "POST":

        emp_id = request.POST.get("id")

        if emp_id and emp_id.strip():
            obj = Employee.objects.get(id=int(emp_id))
            form = EmployeeForm(request.POST, instance=obj)
        else:
            form = EmployeeForm(request.POST)

        if form.is_valid():
            obj = form.save()
            return JsonResponse({"success": True, "id": obj.id})

        return JsonResponse({"success": False, "errors": form.errors})

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def employee_get(request, id):
    data = Employee.objects.filter(id=id).values().first()
    return JsonResponse(data)


from datetime import datetime


def generate_claim_no():
    year = datetime.now().year

    last = Claim.objects.order_by('-id').first()

    if last:
        number = last.id + 1
    else:
        number = 1

    return f"CLM-{year}-{number:04d}"


@login_required
def claim_page(request):
    print("LOGIN USER in CLAIM PAGE", request.user.id)

    # =====================================
    # LOGGED EMPLOYEE
    # =====================================

    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    # =====================================
    # CLAIM FILTER
    # =====================================

    if logged_emp and logged_emp.employee_type.upper() == "STAFF":

        claims = Claim.objects.filter(
            employee__isnull=True
        )

    elif logged_emp and logged_emp.employee_type.upper() == "ADVISOR":

        claims = Claim.objects.filter(
            employee=logged_emp
        )

    else:

        claims = Claim.objects.all()

    # =====================================
    # ROLE CHECK
    # =====================================

    can_change_advisor = (
            logged_emp and
            logged_emp.employee_type.upper() != "ADVISOR"
    )

    # =====================================
    # FORM
    # =====================================

    current_stage = 1
    pending_days = 0

    claim_form = ClaimForm(initial={
        'claim_no': generate_claim_no(),
        'employee': logged_emp.id if logged_emp else None
    })

    vehicle_form = VehicleForm()

    # =====================================
    # CONTEXT
    # =====================================

    context = {
        "form": claim_form,
        "vehicle_form": vehicle_form,
        "logged_emp": logged_emp,
        "can_change_advisor": can_change_advisor,
        "current_stage": current_stage,
        "pending_days": pending_days,
        "claim_document_slots": get_claim_document_slots(None),
        "claims": claims,
        "breadcrumbs": [

            {
                "title": "Claims",
                "url": "",
                "icon": "fa fa-list"
            },

            {
                "title": "Claim  List",
                "url": "claimList",
                "icon": "fa fa-file"
            },

            {
                "title": "Create New Claim",
                "icon": "fa fa-plus"
            }
        ]
    }

    return render(
        request,
        "claim/claimEntry.html",
        context
    )


@never_cache
@login_required
def claimList_page(request):
    claim_form = ClaimForm(initial={
        "claim_no": generate_claim_no()
    })

    vehicle_form = VehicleForm()

    context = {
        "form": claim_form,
        "vehicle_form": vehicle_form,

        "breadcrumbs": [
            {
                "title": "Claims",
                "icon": "fa fa-list"
            },
            {
                "title": "Claim List",
                "url": "claimList",
                "icon": "fa fa-file"
            }
        ]
    }

    return render(
        request,
        "claim/claim.html",
        context
    )


@never_cache
@login_required
def jobList_page(request):
    job_form = JobCardForm(initial={
        'job_no': generate_job_no()})
    claim_form = ClaimForm()

    context = {
        "form": job_form,
        "claimform": claim_form,
    }

    return render(request, "jobcard/jobList.html", context)


from .models import Employee


@login_required
def claim_save(request, pk=None):
    claim = None

    if pk:
        claim = get_object_or_404(
            Claim,
            pk=pk
        )

    if request.method == "POST":

        form = ClaimForm(
            request.POST,
            instance=claim
        )

        if form.is_valid():

            obj = form.save(commit=False)

            try:

                employee = Employee.objects.get(
                    user=request.user
                )

                obj.employee = employee

            except Employee.DoesNotExist:

                return JsonResponse({
                    "status": "error",
                    "message": "Employee mapping missing"
                })

            # preserve claim no
            if not obj.claim_no:
                obj.claim_no = generate_claim_no()

            obj.save()

            return JsonResponse({
                "status": "success",
                "id": obj.id
            })

        return JsonResponse({
            "status": "error",
            "errors": form.errors
        })

    form = ClaimForm(instance=claim)

    pending_days = (
        (timezone.localdate() - timezone.localdate(claim.created_at)).days
        if claim and claim.created_at
        else 0
    )

    return render(
        request,
        "claim/claimEntry.html",
        {
            "form": form,
            "claim": claim,
            "pending_days": pending_days,
            "claim_document_slots": get_claim_document_slots(claim),
        }
    )


@login_required
def claim_data(request):
    data = Claim.objects.select_related(
        'vehicle',
        'customer',
        'insurance_company',
        'surveyor'
    ).values(
        'id',
        'claim_no',
        'vehicle__registration_no',
        'customer__name',
        'insurance_company__ins_co_name',
        'surveyor__name',
        'status',
        'estimated_amount',
        'approved_amount'
    )

    return JsonResponse({
        "data": list(data)
    })


@never_cache
@login_required
def claim_list_api(request):
    logged_emp = Employee.objects.filter(user=request.user).first()

    if request.user.is_superuser:
        claims = Claim.objects.all()
    elif logged_emp and logged_emp.employee_type.upper() == "ADVISOR":
        claims = Claim.objects.filter(employee=logged_emp)
    else:
        claims = Claim.objects.all()

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    claim_status = request.GET.get("claim_status", "open").strip().lower()

    if claim_status == "closed":
        claims = claims.filter(claim_stage=ClaimStageCode.CLOSED)
    elif claim_status != "all":
        claims = claims.exclude(claim_stage=ClaimStageCode.CLOSED)

    if from_date:
        claims = claims.filter(created_at__date__gte=from_date)

    if to_date:
        claims = claims.filter(created_at__date__lte=to_date)

    if request.GET.get("advisor_blank") == "1":
        claims = claims.filter(employee__isnull=True)

    if request.GET.get("advisor_assigned") == "1":
        claims = claims.filter(employee__isnull=False)

    claims = claims.select_related(
        "vehicle",
        "vehicle__model",
        "vehicle__customer",
        "surveyor",
        "insurance_company",
        "employee",
        "jobcard"
    )

    data = []

    for claim in claims:
        job = JobCard.objects.filter(claim=claim).first()

        data.append({
            "id": claim.id,
            "claim_no": claim.claim_no,

            "employee__name": claim.employee.name if claim.employee else "",

            "vehicle__registration_no": claim.vehicle.registration_no if claim.vehicle else "",
            "vehicle__model__name": claim.vehicle.model.name if claim.vehicle and claim.vehicle.model else "",
            "vehicle__customer__name": claim.vehicle.customer.name if claim.vehicle and claim.vehicle.customer else "",
            "vehicle__customer__mobile_no": claim.vehicle.customer.mobile_no if claim.vehicle and claim.vehicle.customer else "",
            "insurance_company__ins_co_name": claim.insurance_company.ins_co_name if claim.insurance_company else "",

            "surveyor__name": claim.surveyor.name if claim.surveyor else "",
            "surveyor__mobile_no": claim.surveyor.mobile_no if claim.surveyor else "",

            "policy_no": claim.policy_no,
            "ic_claim_no": claim.ic_claim_no,
            "claim_type": claim.claim_type,

            "accident_date": claim.accident_date,
            "intimation_date": claim.intimation_date,
            "survey_date": claim.survey_date,
            "survey_status": claim.survey_status,

            "claim_stage": claim.claim_stage,
            "claim_stage_name": claim.get_claim_stage_display(),
            "status": claim.status,

            "estimated_amount": claim.estimated_amount,
            "approved_amount": claim.approved_amount,
            "remarks": claim.remarks,
            "created_at": claim.created_at,

            "has_jobcard": True if job else False,
            "jobcard_id": job.id if job else None,
        })

    return JsonResponse(data, safe=False)


@login_required
def add_vehicle(request):
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Invalid request"
        })

    data = json.loads(request.body)

    registration_no = data.get("registration_no", "").strip().upper()
    chassis_no = data.get("chassis_no", "").strip()
    engine_no = data.get("engine_no", "").strip()

    # =========================
    # VALIDATION
    # =========================
    if not registration_no:
        return JsonResponse({
            "status": "error",
            "message": "Registration No required"
        })

    # =========================
    # DUPLICATE CHECK
    # =========================
    existing = Vehicle.objects.filter(
        registration_no__iexact=registration_no
    ).first()

    if existing:
        return JsonResponse({
            "status": "exists",
            "id": existing.id,
            "text": f"{existing.registration_no}",
            "message": "Vehicle already exists"
        })

    # =========================
    # CREATE VEHICLE
    # =========================
    vehicle = Vehicle.objects.create(
        registration_no=registration_no,
        chassis_no=chassis_no,
        engine_no=engine_no
    )

    return JsonResponse({
        "status": "success",
        "id": vehicle.id,
        "text": f"{vehicle.registration_no}"
    })


from django.db.models import Q


@login_required
def vehicle_search(request):
    term = request.GET.get('term', '').strip()

    vehicles = Vehicle.objects.filter(
        Q(registration_no__icontains=term) |
        Q(chassis_no__icontains=term) |
        Q(engine_no__icontains=term) |
        Q(customer__name__icontains=term)
    ).select_related(
        'model',
        'customer'
    )[:10]

    results = [
        {
            'id': v.id,
            'text': (
                f"{v.registration_no} | "
                f"{v.customer.name if v.customer else ''} | "
                f"{v.model.name if v.model else ''}"
            )
        }
        for v in vehicles
    ]

    return JsonResponse({
        'results': results
    })


@login_required
def get_vehicle_details(request):
    vehicle_id = request.GET.get("id")

    # =========================
    # EMPTY CHECK
    # =========================
    if not vehicle_id:
        return JsonResponse({
            "status": "error",
            "message": "No vehicle selected"
        })

    # =========================
    # NUMERIC VALIDATION
    # =========================
    if not str(vehicle_id).isdigit():
        return JsonResponse({
            "status": "error",
            "message": "Invalid vehicle ID"
        })

    try:

        v = Vehicle.objects.select_related(
            "model",
            "variant",
            "customer"
        ).get(id=vehicle_id)

        return JsonResponse({
            "status": "success",
            "data": {

                "registration_no": v.registration_no,
                "chassis_no": v.chassis_no,
                "engine_no": v.engine_no,

                "vehicle_type": v.vehicle_type,
                "color": v.color,

                "model": v.model.name if v.model else "",
                "variant": v.variant.name if v.variant else "",
                # CUSTOMER
                "customer_id": v.customer.id if v.customer else "",
                "customer_name": v.customer.name if v.customer else "",
                "mobile": v.customer.mobile_no if v.customer else "",
                "city": v.customer.city if v.customer else "",
                "gst": v.customer.gst_no if v.customer else "",

                "sale_date": (
                    v.sale_date.strftime("%Y-%m-%d")
                    if v.sale_date else ""
                )
            }
        })

    except Vehicle.DoesNotExist:

        return JsonResponse({
            "status": "error",
            "message": "Vehicle not found"
        })


# views.py

from .models import Claim
from .forms import ClaimForm


@never_cache
@login_required
def claim_edit(request, pk=None):
    from django.utils.dateparse import parse_date
    from datetime import datetime, time
    from django.utils import timezone

    print("LOGIN USER in claim_edit", request.user.id)

    claim = None

    if pk:
        claim = get_object_or_404(
            Claim,
            pk=pk
        )

    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()
    role = (
        logged_emp.employee_type.upper()
        if logged_emp else ""
    )
    can_reopen_claim = (
        request.user.is_superuser
        or role == "MANAGER"
        or request.user.groups.filter(name__iexact="Manager").exists()
    )

    if (
        claim
        and int(claim.claim_stage or 0) == ClaimStageCode.CLOSED
        and claim.status != "Closed"
    ):
        claim.status = "Closed"
        claim.save(update_fields=["status"])

    is_claim_locked = bool(
        claim
        and (
            int(claim.claim_stage or 0) == ClaimStageCode.CLOSED
            or claim.status == "Closed"
        )
        and not can_reopen_claim
    )

    # =====================================
    # POST
    # =====================================

    if request.method == "POST":
        if is_claim_locked:
            messages.error(
                request,
                "Closed claim cannot be updated. Only Admin or Manager can re-open it."
            )
            return redirect("claim_edit", pk=claim.id)

        form = ClaimForm(
            request.POST,
            request.FILES,
            instance=claim
        )

        print("FORM VALID:", form.is_valid())
        old_advisor_id = claim.employee_id if claim and claim.employee_id else None
        old_stage = claim.claim_stage if claim else None
        old_status = claim.status if claim else None
        if request.method == "POST":

            vehicle_id = request.POST.get("vehicle")

            if vehicle_id:

                open_claim = Claim.objects.filter(
                    vehicle_id=vehicle_id
                ).exclude(
                    claim_stage=ClaimStageCode.CLOSED
                )

                # edit mode exclude same claim
                if claim:
                    open_claim = open_claim.exclude(id=claim.id)

                if open_claim.exists():
                    existing = open_claim.first()

                    return JsonResponse({
                        "status": "error",
                        "message": (
                            f"Open claim already exists for this vehicle. "
                            f"Claim No: {existing.claim_no}"
                        )
                    })
        if form.is_valid():

            obj = form.save(commit=False)
            jobcard = JobCard.objects.filter(claim=obj).first() if obj.pk else None
            claim_created_date = parse_workflow_datetime(
                request.POST.get("claim_created_date") or ""
            )
            validate_labels = set()
            if not claim:
                validate_labels = {
                    "Claim Created Date",
                    "Claim Intimation Date",
                    "Survey Date",
                    "Insurance Approval Date",
                    "Liability Received Date",
                    "Invoice Date",
                    "Delivery Date",
                }
            else:
                if workflow_date_changed(claim.created_at, claim_created_date):
                    validate_labels.add("Claim Created Date")
                if workflow_date_changed(claim.intimation_date, obj.intimation_date):
                    validate_labels.add("Claim Intimation Date")
                if workflow_date_changed(claim.survey_date, obj.survey_date):
                    validate_labels.add("Survey Date")
                if workflow_date_changed(claim.insurance_approval_date, obj.insurance_approval_date):
                    validate_labels.add("Insurance Approval Date")
                if workflow_date_changed(claim.liability_received_at, obj.liability_received_at):
                    validate_labels.add("Liability Received Date")
                if workflow_date_changed(claim.invoice_datetime, obj.invoice_datetime):
                    validate_labels.add("Invoice Date")
                if workflow_date_changed(claim.delivery_datetime, obj.delivery_datetime):
                    validate_labels.add("Delivery Date")

            date_error = validate_claim_job_workflow_dates(
                obj,
                job=jobcard,
                allocation=getattr(jobcard, "allocation", None) if jobcard else None,
                claim_created_date=claim_created_date,
                validate_labels=validate_labels,
            )
            if date_error:
                messages.error(request, date_error)
                return redirect("claim_edit", pk=obj.id if obj.id else pk)

            future_error = validate_no_future_workflow_dates([
                ("Claim Created Date", claim_created_date),
                ("Claim Intimation Date", obj.intimation_date),
                ("Survey Date", obj.survey_date),
                ("Insurance Approval Date", obj.insurance_approval_date),
                ("Liability Received Date", obj.liability_received_at),
                ("Invoice Date", obj.invoice_datetime),
                ("Delivery Date", obj.delivery_datetime),
            ])
            if future_error:
                messages.error(request, future_error)
                return redirect("claim_edit", pk=obj.id if obj.id else pk)


            has_invoice_data = any([
                obj.invoice_datetime,
                obj.invoice_amount and obj.invoice_amount > 0,
                obj.invoice_parts_amount and obj.invoice_parts_amount > 0,
                obj.invoice_labour_amount and obj.invoice_labour_amount > 0,
                obj.payment_mode,
                obj.payment_details,
            ])

            if (
                has_invoice_data
                and (
                    not jobcard
                    or sync_jobcard_main_status(jobcard) != "Closed"
                )
            ):
                messages.error(
                    request,
                    "First close the linked jobcard for this claim before saving invoice details."
                )
                return redirect("claim_edit", pk=obj.id if obj.id else pk)

            # =====================================
            # AUTO ASSIGN ADVISOR
            # =====================================

            if logged_emp and logged_emp.employee_type == "Advisor":
                obj.employee = logged_emp

            # =====================================
            # AUTO CLAIM NO
            # =====================================

            if not obj.claim_no:
                obj.claim_no = generate_claim_no()

            # =====================================
            # STAGE LOGIC
            # =====================================
            has_liability_document = bool(
                obj.liability_document
                or (
                    claim
                    and claim.liability_document
                    and not request.FILES.get("liability_document")
                )
            )

            if (
                    obj.liability_received_at
                    and obj.liability_do_amount
                    and obj.liability_do_amount > 0
                    and has_liability_document
            ):
                if claim and claim.claim_stage >= ClaimStageCode.INVOICED:
                    obj.claim_stage = claim.claim_stage
                else:
                    obj.claim_stage = ClaimStageCode.INVOICED
            elif (
                    obj.insurance_approval_date
                    and obj.assessment_file
            ):
                obj.claim_stage = ClaimStageCode.INSURANCE_APPROVAL
            elif (
                    obj.survey_date
                    and obj.surveyor
            ):
                obj.claim_stage = ClaimStageCode.SURVEY
            elif (
                    obj.intimation_date
                    and obj.insurance_company
                    and obj.policy_no
            ):

                obj.claim_stage = ClaimStageCode.INTIMATION

            elif claim and claim.claim_stage >= ClaimStageCode.ESTIMATE_CREATED:

                obj.claim_stage = claim.claim_stage

            elif obj.employee:

                obj.claim_stage = ClaimStageCode.ADVISOR_ASSIGNED

            else:

                obj.claim_stage = ClaimStageCode.CLAIM_CREATED

            delivery_complete = (
                obj.delivery_datetime
                and obj.delivered_by
                and obj.delivered_to
                and (
                    obj.delivered_to != "Drop By Driver"
                    or obj.delivery_driver_name
                )
            )

            if delivery_complete:
                obj.claim_stage = ClaimStageCode.CLOSED
                obj.status = "Closed"

            # =====================================
            # SAVE
            # =====================================

            is_new = obj.pk is None

            obj.save()
            jobcard = JobCard.objects.filter(claim=obj).first()
            save_claim_documents(request, obj)
            if jobcard and obj.self_survey:
                save_vehicle_condition_photos(request, jobcard)
            if claim_created_date:
                obj.created_at = claim_created_date
                obj.save(update_fields=["created_at"])

            if claim and claim.employee:
                old_advisor_id = claim.employee_id

            obj.save()

            new_advisor_id = obj.employee_id
            new_stage = obj.claim_stage
            new_status = obj.status

            if jobcard:
                uploaded_reinspection_images = request.FILES.getlist("reinspection_images")
                posted_reinspection_done = request.POST.get("reinspection_done") == "1"
                posted_reinspection_date = parse_workflow_datetime(
                    request.POST.get("reinspection_date") or ""
                )
                posted_reinspection_done_by = request.POST.get(
                    "reinspection_done_by",
                    ""
                ).strip()
                current_claim_stage = int((claim.claim_stage if claim else obj.claim_stage) or 0)
                should_update_reinspection_fields = (
                    current_claim_stage <= ClaimStageCode.RE_INSPECTION
                    or posted_reinspection_done
                    or bool(posted_reinspection_date)
                    or bool(posted_reinspection_done_by)
                )
                if should_update_reinspection_fields:
                    future_error = validate_no_future_workflow_dates([
                        ("Re-Inspection Date", posted_reinspection_date),
                    ])
                    if future_error:
                        messages.error(request, future_error)
                        return redirect("claim_edit", pk=obj.id)

                if uploaded_reinspection_images:
                    existing_reinspection_photo_count = jobcard.reinspection_photos.count()
                    existing_reinspection_photo_size = get_reinspection_photo_storage_size(jobcard)
                    total_photo_count = existing_reinspection_photo_count + len(uploaded_reinspection_images)

                    if total_photo_count > REINSPECTION_MAX_PHOTOS_PER_JOBCARD:
                        messages.error(
                            request,
                            "Re-inspection image limit exceeded. "
                            f"Maximum {REINSPECTION_MAX_PHOTOS_PER_JOBCARD} images are allowed per jobcard."
                        )
                        return redirect("claim_edit", pk=obj.id)

                    oversized_image = next(
                        (
                            image for image in uploaded_reinspection_images
                            if image.size > REINSPECTION_MAX_IMAGE_SIZE_BYTES
                        ),
                        None
                    )

                    if oversized_image:
                        messages.error(
                            request,
                            f"{oversized_image.name} is too large. "
                            f"Maximum {REINSPECTION_MAX_IMAGE_SIZE_MB} MB is allowed per image."
                        )
                        return redirect("claim_edit", pk=obj.id)

                    upload_total_size = sum(image.size for image in uploaded_reinspection_images)

                    if existing_reinspection_photo_size + upload_total_size > REINSPECTION_MAX_TOTAL_SIZE_BYTES:
                        messages.error(
                            request,
                            "Re-inspection image storage limit exceeded. "
                            f"Maximum {REINSPECTION_MAX_TOTAL_SIZE_MB} MB is allowed per jobcard."
                        )
                        return redirect("claim_edit", pk=obj.id)

                if should_update_reinspection_fields:
                    jobcard.reinspection_done = posted_reinspection_done
                    jobcard.reinspection_date = posted_reinspection_date
                    jobcard.reinspection_done_by = posted_reinspection_done_by
                    jobcard.save(update_fields=[
                        "reinspection_done",
                        "reinspection_date",
                        "reinspection_done_by",
                    ])

                for image in uploaded_reinspection_images:
                    JobCardReInspectionPhoto.objects.create(
                        job=jobcard,
                        image=image
                    )

                if should_update_reinspection_fields and jobcard.reinspection_done:
                    obj.claim_stage = ClaimStageCode.LIABILITY
                    obj.save(update_fields=["claim_stage"])

                sync_jobcard_main_status(jobcard)

            notify_title = None
            notify_message = None

            # 1. New advisor assigned
            if old_advisor_id != new_advisor_id and obj.employee:

                notify_title = "New Claim Assigned"
                notify_message = f"Claim {obj.claim_no} assigned to you"

            # 2. Stage changed
            elif old_stage != new_stage and obj.employee:

                notify_title = "Claim Stage Updated"
                notify_message = (
                    f"Claim {obj.claim_no} stage updated to "
                    f"{obj.get_claim_stage_display()}"
                )

            # 3. Status changed
            elif old_status != new_status and obj.employee:

                notify_title = "Claim Status Updated"
                notify_message = (
                    f"Claim {obj.claim_no} status changed to "
                    f"{obj.status}"
                )

            # 4. Normal edit
            elif obj.employee:

                notify_title = "Claim Updated"
                notify_message = f"Claim {obj.claim_no} details updated"

            if notify_title and obj.employee and obj.employee.user:
                UserNotification.objects.create(
                    user=obj.employee.user,
                    title=notify_title,
                    message=notify_message,
                    url=f"/claim/{obj.id}/edit/"
                )
            # =====================================
            # SUCCESS MESSAGE
            # =====================================

            if is_new:

                messages.success(
                    request,
                    f"Claim {obj.claim_no} created successfully"
                )

            else:

                messages.success(
                    request,
                    f"Claim {obj.claim_no} updated successfully"
                )

            return redirect(
                "claim_edit",
                pk=obj.id
            )

        else:

            print("FORM ERRORS:", form.errors)

            return JsonResponse({
                "status": "error",
                "errors": form.errors
            })

    # =====================================
    # GET
    # =====================================
    move_stage = request.GET.get("move_stage")

    if claim and move_stage:

        current = int(
            claim.claim_stage or
            ClaimStageCode.CLAIM_CREATED
        )
        old_stage_before_move = current

        if move_stage == "next":

            is_valid, missing = validate_claim_stage_before_next(claim)

            if not is_valid:
                messages.error(
                    request,
                    "Cannot move next. Missing: "
                    + ", ".join(missing)
                )

                return redirect(
                    "claim_edit",
                    pk=claim.id
                )

            if current == ClaimStageCode.LIABILITY:
                jobcard = JobCard.objects.filter(claim=claim).first()
                if not jobcard or sync_jobcard_main_status(jobcard) != "Closed":
                    messages.error(
                        request,
                        "First close the linked jobcard for this claim before moving to Invoiced stage."
                    )
                    return redirect(
                        "claim_edit",
                        pk=claim.id
                    )

            current += 1

        elif move_stage == "back":
            if (
                current >= ClaimStageCode.REPAIR_IN_PROGRESS
                and claim_has_repair_progress_data(claim)
            ):
                messages.error(
                    request,
                    "Cannot move to previous stage because repair progress entries exist. "
                    "First clear the started/finished progress rows and uploaded progress photos from Work Allocation."
                )
                return redirect(
                    "claim_edit",
                    pk=claim.id
                )

            current -= 1

        current = max(1, min(current, ClaimStageCode.CLOSED))

        claim.claim_stage = current

        if current == ClaimStageCode.CLOSED:
            claim.status = "Closed"
            claim.save(update_fields=["claim_stage", "status"])
        else:
            claim.save(update_fields=["claim_stage"])

        jobcard = JobCard.objects.filter(claim=claim).first()

        if jobcard:
            sync_jobcard_main_status(jobcard)

        if (
            old_stage_before_move != current
            and current == ClaimStageCode.WORK_ALLOCATION
        ):
            notify_floor_incharge_work_allocation_pending(claim)

        messages.success(
            request,
            f"Stage changed to {claim.get_claim_stage_display()}"
        )

        return redirect(
            "claim_edit",
            pk=claim.id
        )
    can_change_advisor = role != "ADVISOR"

    form = ClaimForm(instance=claim)
    if is_claim_locked:
        for field in form.fields.values():
            field.disabled = True

    jobcard = JobCard.objects.filter(claim=claim).first() if claim else None
    existing_reinspection_photo_count = (
        jobcard.reinspection_photos.count()
        if jobcard else 0
    )
    existing_reinspection_photo_size = (
        get_reinspection_photo_storage_size(jobcard)
        if jobcard else 0
    )

    # =====================================
    # SHOW ONLY ADVISORS IN DROPDOWN
    # =====================================

    form.fields['employee'].queryset = Employee.objects.filter(
        designation__iexact="Advisor",
        is_active=True
    )
    current_stage = int(claim.claim_stage or ClaimStageCode.CLAIM_CREATED)
    claim_created_date_value = (
        datetime_local_value(claim.created_at)
        if claim and claim.created_at
        else timezone.localtime().strftime("%Y-%m-%dT%H:%M")
    )
    is_jobcard_closed = bool(
        jobcard
        and sync_jobcard_main_status(jobcard) == "Closed"
    )
    is_reinspection_done = bool(
        jobcard
        and (
            jobcard.reinspection_done
            or current_stage >= ClaimStageCode.LIABILITY
        )
    )
    has_repair_progress_data = claim_has_repair_progress_data(claim)
    has_repair_progress_started = bool(
        jobcard
        and WorkProgress.objects.filter(
            allocation__job=jobcard,
            start_time__isnull=False,
        ).exists()
    )
    second_approval_pending = bool(
        jobcard
        and jobcard.additional_approval_required
        and jobcard.second_approval_status == "Pending"
    )
    next_stage_label = (
        ClaimStageCode(current_stage + 1).label
        if current_stage < ClaimStageCode.CLOSED
        else "Completed"
    )
    pending_days = (
        timezone.localdate() - timezone.localdate(claim.created_at)
    ).days if claim.created_at else 0
    print("current_stage = ", current_stage)

    # =====================================
    # RENDER
    # =====================================
    is_manager = request.user.groups.filter(
        name__iexact="Manager"
    ).exists()
    return render(
        request,
        "claim/claimEntry.html",
        {
            "form": form,
            "claim": claim,
            "logged_emp": logged_emp,
            "can_change_advisor": can_change_advisor,
            "current_stage": current_stage,
            "claim_created_date_value": claim_created_date_value,
            "next_stage_label": next_stage_label,
            "pending_days": pending_days,
            "is_manager": is_manager,
            "jobcard": jobcard,
            "is_jobcard_closed": is_jobcard_closed,
            "is_reinspection_done": is_reinspection_done,
            "has_repair_progress_data": has_repair_progress_data,
            "has_repair_progress_started": has_repair_progress_started,
            "second_approval_pending": second_approval_pending,
            "is_claim_locked": is_claim_locked,
            "can_reopen_claim": can_reopen_claim,
            "vehicle_photo_slots": get_vehicle_condition_photo_slots(jobcard),
            "existing_reinspection_photo_count": existing_reinspection_photo_count,
            "existing_reinspection_photo_size_mb": round(
                existing_reinspection_photo_size / (1024 * 1024),
                2
            ),
            "reinspection_max_photos": REINSPECTION_MAX_PHOTOS_PER_JOBCARD,
            "reinspection_max_image_size_mb": REINSPECTION_MAX_IMAGE_SIZE_MB,
            "reinspection_max_total_size_mb": REINSPECTION_MAX_TOTAL_SIZE_MB,
            "claim_document_slots": get_claim_document_slots(claim),
            "stage_steps": [
                (ClaimStageCode.CLAIM_CREATED, "Claim Created"),
                (ClaimStageCode.ADVISOR_ASSIGNED, "Advisor Assigned"),
                (ClaimStageCode.ESTIMATE_CREATED, "Job Estimation"),
                (ClaimStageCode.INTIMATION, "Claim Intimation"),
                (ClaimStageCode.SURVEY, "Survey"),
                (ClaimStageCode.INSURANCE_APPROVAL, "Approval"),
                (ClaimStageCode.WORK_ALLOCATION, "Pending Work Allocation"),
                (ClaimStageCode.REPAIR_IN_PROGRESS, "Repair Work"),
                (ClaimStageCode.WORK_COMPLETED, "Work Completed"),
                (ClaimStageCode.RE_INSPECTION, "Re Inspection"),
                (ClaimStageCode.LIABILITY, "Liability"),
                (ClaimStageCode.INVOICED, "Invoiced"),
                (ClaimStageCode.DELIVERY, "Delivery"),
                (ClaimStageCode.CLOSED, "Closed"),
            ],
            "breadcrumbs": [

                {
                    "title": "Claim",
                    "url": "",
                    "icon": "fa fa-list"
                },

                {
                    "title": "Claim List",
                    "url": "claimList",
                    "icon": "fa fa-file"
                },

                {
                    "title": "Edit Claim No:",
                    "icon": "fa fa-plus"
                }
            ]
        }
    )


@login_required
def claimdashboard(request):
    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    claims = Claim.objects.none()

    # =====================================
    # ADMIN
    # =====================================

    if request.user.is_superuser:

        claims = Claim.objects.all()

    # =====================================
    # RECEPTION / STAFF
    # =====================================

    elif logged_emp and logged_emp.employee_type in [
        "STAFF",
        "RECEPTION",
        "ADMIN"
    ]:

        claims = Claim.objects.filter(
            employee__isnull=True
        )

    # =====================================
    # ADVISOR
    # =====================================

    elif logged_emp and logged_emp.employee_type == "Advisor":

        claims = Claim.objects.filter(
            employee=logged_emp
        )

    # =====================================
    # MANAGER
    # =====================================

    elif logged_emp and logged_emp.employee_type == "MANAGER":

        claims = Claim.objects.all()

    context = {
        "claims": claims
    }

    return render(
        request,
        "dashboard.html",
        context
    )


def job_save(self, *args, **kwargs):
    is_new = self.pk is None

    super().save(*args, **kwargs)

    # =====================================
    # CLAIM STAGE UPDATE
    # =====================================

    if self.claim:

        # JOB CARD CREATED
        if self.claim.claim_stage < 3:
            self.claim.claim_stage = 3
            self.claim.save(
                update_fields=["claim_stage"]
            )


def generate_job_no():
    year = datetime.now().year

    last = JobCard.objects.order_by('-id').first()

    if last:
        number = last.id + 1
    else:
        number = 1

    return f"JOB-{year}-{number:04d}"


def get_inventory_context(job=None):
    inventory = None

    # SAFE INVENTORY LOAD
    if job:
        try:
            inventory = job.inventory
        except Exception:
            inventory = None

    # SAFE VALUES
    fuel_percent = 0
    cng_percent = 0

    if inventory:
        fuel_percent = inventory.fuel_percent or 0
        cng_percent = inventory.cng_percent or 0

    # GAUGE ANGLE
    fuel_angle = -90 + (fuel_percent * 1.8)
    cng_angle = -90 + (cng_percent * 1.8)

    # LABELS
    def get_fuel_label(value):

        value = int(value or 0)

        if value <= 0:
            return "Empty"

        elif value <= 25:
            return "1/4"

        elif value <= 50:
            return "Half"

        elif value <= 75:
            return "3/4"

        return "Full"

    # DAMAGE MARKS
    raw_marks = inventory.damage_marks if inventory else []

    damage_marks = []

    for m in raw_marks:

        if m.get("type") == "scratch":
            x1 = float(m.get("x1", 0))
            y1 = float(m.get("y1", 0))
            x2 = float(m.get("x2", 0))
            y2 = float(m.get("y2", 0))

            dx = x2 - x1
            dy = y2 - y1

            m["length"] = round((dx * dx + dy * dy) ** 0.5, 2)
            m["angle"] = round(math.degrees(math.atan2(dy, dx)), 2)

        damage_marks.append(m)
    tyre_map = {}

    if job:
        for t in job.tyres.all():
            tyre_map[t.position] = t

    tyre_positions = [
        ("front_left", "Front Left"),
        ("front_right", "Front Right"),
        ("rear_left", "Rear Left"),
        ("rear_right", "Rear Right"),
        ("stepney", "Stepney"),
    ]
    items = [
        ("lh_mirror", "LH Side Mirror"),
        ("jack", "Jack"),
        ("tool_kit", "Tool Kit"),
        ("floor_mat_count", "Floor Mat"),
        ("mud_flap_count", "Mud Flap"),
        ("stereo", "Stereo"),
        ("battery", "Battery"),
        ("rh_mirror", "RH Side Mirror"),
        ("number_plate", "Number Plate"),
        ("center_mirror", "Center Rear View Mirror"),
        ("frt_wiper", "Front Wiper"),
        ("rr_wiper", "Rear Wiper"),
        ("accessories", "Extra Accessories"),
    ]
    print("CTX INVENTORY:", inventory)
    fuel_percent = inventory.fuel_percent if inventory else 0
    cng_percent = inventory.cng_percent if inventory else 0

    fuel_label = get_fuel_label(fuel_percent)
    cng_label = get_fuel_label(cng_percent)
    return {
        "lh_mirror": inventory.lh_mirror if inventory else "",
        "jack": inventory.jack if inventory else "",
        "tool_kit": inventory.tool_kit if inventory else "",
        "floor_mat_count": inventory.floor_mat_count if inventory else "",
        "mud_flap_count": inventory.mud_flap_count if inventory else "",
        "stereo": inventory.stereo if inventory else "",
        "battery": inventory.battery if inventory else "",
        "rh_mirror": inventory.rh_mirror if inventory else "",
        "number_plate": inventory.number_plate if inventory else "",
        "center_mirror": inventory.center_mirror if inventory else "",
        "frt_wiper": inventory.frt_wiper if inventory else "",
        "rr_wiper": inventory.rr_wiper if inventory else "",
        "accessories": inventory.accessories if inventory else "",
        "inventory_remarks": inventory.remarks if inventory else "",
        "fuel_percent": inventory.fuel_percent if inventory else 0,
        "cng_percent": inventory.cng_percent if inventory else 0,
        "fuel_angle": fuel_angle,
        "cng_angle": cng_angle,
        "damage_marks_json": json.dumps(raw_marks),
        "damage_marks": damage_marks,
        "fuel_label": fuel_label,
        "cng_label": cng_label,
        "tyre_inventory": [
            {
                "position": key,
                "label": label,
                "make": tyre_map[key].make if key in tyre_map else "",
                "size": tyre_map[key].size if key in tyre_map else "",
                "depth": tyre_map[key].depth if key in tyre_map else "",
                "wheel_cap": tyre_map[key].wheel_cap if key in tyre_map else "",
            }
            for key, label in tyre_positions
        ],
    }


@login_required
@login_required
def jobcard_create(request, claim_id=None):
    from django.utils import timezone
    from django.utils.dateparse import parse_date

    claim = None
    job = None
    if claim_id:
        claim = get_object_or_404(Claim, id=claim_id)

    job_no = generate_job_no()

    form = JobCardForm(initial={
        "job_no": job_no,
        "claim": claim.id if claim else None,
        "advisor": claim.employee if claim else None
    })
    variant_name = ""

    if (
            claim
            and claim.vehicle
            and claim.vehicle.variant
    ):
        variant_name = claim.vehicle.variant.name or ""

    is_cng_vehicle = "CNG" in variant_name.upper()
    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    role = (
        logged_emp.employee_type.upper()
        if logged_emp else ""
    )

    can_change_advisor = role != "ADVISOR"
    can_edit_jobcard_entries = (
        request.user.is_superuser
        or role in ["MANAGER", "ADVISOR"]
        or request.user.groups.filter(name__iexact="Manager").exists()
    )
    can_reopen_jobcard = (
        request.user.is_superuser
        or role == "MANAGER"
        or request.user.groups.filter(name__iexact="Manager").exists()
    )

    if request.method == "POST":

        form = JobCardForm(request.POST, request.FILES)

        if form.is_valid():

            obj = form.save(commit=False)

            if claim:
                obj.claim = claim
                obj.advisor = claim.employee

            if not obj.job_no:
                obj.job_no = generate_job_no()

            job_created_date = parse_workflow_datetime(
                request.POST.get("job_created_date") or ""
            )
            validate_labels = set()
            if workflow_date_changed(None, job_created_date):
                validate_labels.add("Jobcard Created Date")
            if workflow_date_changed(None, obj.gate_in_datetime):
                validate_labels.add("Gate In Date")

            date_error = validate_claim_job_workflow_dates(
                obj.claim,
                job=obj,
                job_created_date=job_created_date,
                validate_labels=validate_labels,
            )
            if date_error:
                messages.error(request, date_error)
                if claim_id:
                    return redirect("jobcard_create_with_claim", claim_id=claim_id)
                return redirect("jobCreate")

            future_error = validate_no_future_workflow_dates([
                ("Gate In Date", obj.gate_in_datetime),
                ("Jobcard Created Date", job_created_date),
            ])
            if future_error:
                messages.error(request, future_error)
                if claim_id:
                    return redirect("jobcard_create_with_claim", claim_id=claim_id)
                return redirect("jobCreate")

            obj.save()

            save_job_inventory(
                request,
                obj
            )
            # =========================
            # 2. PARTS CALCULATION
            # =========================
            part_no = request.POST.getlist("part_no[]")
            part_desc = request.POST.getlist("part_desc[]")
            qty = request.POST.getlist("qty[]")
            rate = request.POST.getlist("rate[]")

            parts_total = Decimal("0")

            for i in range(len(part_no)):
                amount = Decimal(qty[i]) * Decimal(rate[i])

                JobCardPart.objects.create(
                    job=obj,
                    part_no=part_no[i],
                    description=part_desc[i],
                    qty=qty[i],
                    rate=rate[i],
                    amount=amount
                )

                parts_total += amount

            # =========================
            # 3. LABOUR CALCULATION
            # =========================
            job_code = request.POST.getlist("job_code[]")
            lab_desc = request.POST.getlist("lab_desc[]")
            hrs = request.POST.getlist("hrs[]")
            lab_rate = request.POST.getlist("lab_rate[]")

            labour_total = Decimal("0")

            for i in range(len(job_code)):
                amount = Decimal(hrs[i]) * Decimal(lab_rate[i])

                JobCardLabour.objects.create(
                    job=obj,
                    job_code=job_code[i],
                    description=lab_desc[i],
                    labour_hrs=hrs[i],
                    rate=lab_rate[i],
                    amount=amount
                )

                labour_total += amount

            # =========================
            # 4. GST CALCULATION (18%)
            # =========================
            base_total = parts_total + labour_total
            gst_amount = (base_total * Decimal("18")) / Decimal("100")
            net_total = base_total + gst_amount

            obj.parts_total = parts_total
            obj.labour_total = labour_total
            obj.grand_total = base_total
            obj.gst_amount = gst_amount
            obj.net_total = net_total

            obj.save()
            save_vehicle_condition_photos(request, obj)
            save_jobcard_signatures(request, obj)
            if obj.claim_id:
                save_claim_documents(request, obj.claim)
            if job_created_date:
                JobCard.objects.filter(pk=obj.pk).update(
                    job_date=job_created_date
                )
                obj.job_date = job_created_date

            if request.POST.get("send_whatsapp") == "on":
                send_jobcard_whatsapp(obj)
            # =========================
            # 5. UPDATE CLAIM STAGE
            # =========================
            if claim:
                claim.claim_stage = ClaimStageCode.ESTIMATE_CREATED
                claim.save()

            messages.success(
                request,
                f"Job Card {obj.job_no} created successfully"
            )

            return redirect("jobcard_edit", pk=obj.id)

        return JsonResponse({
            "status": "error",
            "errors": form.errors
        })

    return render(request, "jobcard/jobcardEntry.html", {
        "form": form,
        "claim": claim,
        "job": None,
        "job_created_date_value": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        **get_inventory_context(None),
        "can_change_advisor": can_change_advisor,
        "can_edit_jobcard_entries": can_edit_jobcard_entries,
        "is_cng_vehicle": is_cng_vehicle,
        "logged_emp": logged_emp,
        "vehicle_photo_slots": get_vehicle_condition_photo_slots(None),
        "claim_document_slots": get_claim_document_slots(claim),
        "fuel_percent": JobCardInventory.fuel_percent if JobCardInventory else 0,
        "cng_percent": JobCardInventory.cng_percent if JobCardInventory else 0,
        # ✅ BREADCRUMB
        "breadcrumbs": [

            {
                "title": "Jobcards",
                "url": "",
                "icon": "fa fa-list"
            },

            {
                "title": "Job Card List",
                "url": "jobList",
                "icon": "fa fa-file"
            },

            {
                "title": "Create Job Card",
                "icon": "fa fa-plus"
            }
        ]

    })


@never_cache
@login_required
def jobcard_edit(request, pk):
    from django.utils.dateparse import parse_date

    job = get_object_or_404(JobCard, pk=pk)
    claim = job.claim
    insurance_companies = InsuranceCompany.objects.all()
    variant_name = ""

    if (
            claim
            and claim.vehicle
            and claim.vehicle.variant
    ):
        variant_name = claim.vehicle.variant.name or ""

    is_cng_vehicle = "CNG" in variant_name.upper()
    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    role = (
        logged_emp.employee_type.upper()
        if logged_emp else ""
    )

    can_change_advisor = role != "ADVISOR"
    can_edit_jobcard_entries = (
        request.user.is_superuser
        or role in ["MANAGER", "ADVISOR"]
        or request.user.groups.filter(name__iexact="Manager").exists()
    )
    can_reopen_jobcard = (
        request.user.is_superuser
        or role == "MANAGER"
        or request.user.groups.filter(name__iexact="Manager").exists()
    )
    can_approve_second_approval = can_update_second_approval(
        request.user,
        logged_emp,
        job,
    )
    second_approval_pending = bool(
        job.additional_approval_required
        and job.second_approval_status == "Pending"
    )
    allocation = getattr(job, "allocation", None)
    additional_approval_parts = (
        list(allocation.parts.filter(is_additional=True)
        .select_related("job_part")
        .prefetch_related("additional_approval_photos"))
        if allocation
        else []
    )
    additional_approval_labours = (
        list(allocation.labours.filter(is_additional=True)
        .select_related("job_labour")
        .prefetch_related("additional_approval_photos"))
        if allocation
        else []
    )
    additional_approval_lines = [
        *additional_approval_parts,
        *additional_approval_labours,
    ]
    additional_approval_total_count = len(additional_approval_lines)
    additional_approval_approved_count = sum(
        1
        for line in additional_approval_lines
        if line.advisor_approval_status == "Approved"
    )
    additional_approval_rejected_count = sum(
        1
        for line in additional_approval_lines
        if line.advisor_approval_status == "Rejected"
    )
    additional_approval_pending_count = (
        additional_approval_total_count
        - additional_approval_approved_count
        - additional_approval_rejected_count
    )
    is_jobcard_locked = job.repair_status == "Closed" and not can_reopen_jobcard
    can_edit_jobcard_entries = can_edit_jobcard_entries and not is_jobcard_locked

    if request.method == "POST":
        if is_jobcard_locked:
            messages.error(
                request,
                "Closed jobcard cannot be updated. Only Admin or Manager can re-open it."
            )
            return redirect("jobcard_edit", pk=job.id)

        old_repair_status = job.repair_status
        old_grand_total = job.grand_total
        old_parts_total = job.parts_total
        old_labour_total = job.labour_total
        old_expected_delivery = job.expected_delivery_datetime
        old_gate_in_datetime = job.gate_in_datetime
        old_job_date = job.job_date

        form = JobCardForm(
            request.POST,
            request.FILES,
            instance=job
        )

        if form.is_valid():

            requested_main_status = request.POST.get("jobcard_main_status", "")
            is_closing_now = (
                requested_main_status == "Closed"
                and job.repair_status != "Closed"
            )

            if (
                job.repair_status == "Closed"
                and requested_main_status
                and requested_main_status != "Closed"
                and not can_reopen_jobcard
            ):
                messages.error(
                    request,
                    "Only Admin or Manager can re-open a closed jobcard."
                )
                return redirect("jobcard_edit", pk=job.id)

            if is_closing_now:
                close_job = JobCard.objects.select_related(
                    "claim",
                    "allocation"
                ).get(pk=job.pk)
                pending_close_items = get_jobcard_close_pending_items(close_job)

                if pending_close_items:
                    messages.error(
                        request,
                        "Before closing jobcard, complete: "
                        + ", ".join(pending_close_items)
                    )
                    return redirect("jobcard_edit", pk=job.id)

                missing_close_checks = []

                if request.POST.get("road_test_done") != "on":
                    missing_close_checks.append("Road Test")

                if request.POST.get("washing_done") != "on":
                    missing_close_checks.append("Washing")

                if request.POST.get("ready_for_delivery") != "on":
                    missing_close_checks.append("Ready")

                if missing_close_checks:
                    messages.error(
                        request,
                        "Before closing jobcard, tick: "
                        + ", ".join(missing_close_checks)
                    )
                    return redirect("jobcard_edit", pk=job.id)

            with transaction.atomic():

                obj = form.save(commit=False)
                # =====================================
                # AUTO ASSIGN ADVISOR
                # =====================================

                if logged_emp and logged_emp.employee_type == "Advisor":
                    obj.employee = logged_emp
                is_new = obj.pk is None

                job_created_date = parse_workflow_datetime(
                    request.POST.get("job_created_date") or ""
                )
                validate_labels = set()
                if workflow_date_changed(old_gate_in_datetime, obj.gate_in_datetime):
                    validate_labels.add("Gate In Date")
                if workflow_date_changed(old_job_date, job_created_date):
                    validate_labels.add("Jobcard Created Date")

                date_error = validate_claim_job_workflow_dates(
                    obj.claim,
                    job=obj,
                    allocation=getattr(obj, "allocation", None),
                    job_created_date=job_created_date,
                    validate_labels=validate_labels,
                )
                if date_error:
                    messages.error(request, date_error)
                    return redirect("jobcard_edit", pk=job.id)

                future_error = validate_no_future_workflow_dates([
                    ("Gate In Date", obj.gate_in_datetime),
                    ("Jobcard Created Date", job_created_date),
                ])
                if future_error:
                    messages.error(request, future_error)
                    return redirect("jobcard_edit", pk=job.id)

                print("FUEL:", request.POST.get("fuel_percent"))
                print("CNG:", request.POST.get("cng_percent"))
                print("MARKS:", request.POST.get("damage_marks"))
                save_job_inventory(
                    request,
                    obj
                )
                # PARTS
                part_ids = request.POST.getlist("part_id[]")
                part_no = request.POST.getlist("part_no[]")
                part_desc = request.POST.getlist("part_desc[]")
                qty = request.POST.getlist("qty[]")
                rate = request.POST.getlist("rate[]")

                parts_total = Decimal("0")
                existing_parts = list(obj.parts.all().order_by("id"))
                existing_parts_by_id = {
                    str(part.id): part for part in existing_parts
                }
                saved_part_ids = []

                for i in range(len(part_no)):

                    if not part_no[i].strip():
                        continue

                    q = Decimal(qty[i] or "0")
                    r = Decimal(rate[i] or "0")
                    amount = q * r

                    part_id = (
                        part_ids[i]
                        if i < len(part_ids)
                        else ""
                    )
                    part = existing_parts_by_id.get(part_id)

                    if part is None:
                        part = JobCardPart(job=obj)

                    part.part_no = part_no[i]
                    part.description = part_desc[i]
                    part.qty = q
                    part.rate = r
                    part.amount = amount
                    part.save()
                    saved_part_ids.append(part.id)

                    parts_total += amount

                obj.parts.exclude(id__in=saved_part_ids).filter(
                    jobcardassessmentpart__isnull=True
                ).delete()
                parts_total = sum(
                    (p.amount for p in obj.parts.all()),
                    Decimal("0")
                )

                # LABOUR
                labour_ids = request.POST.getlist("labour_id[]")
                job_code = request.POST.getlist("job_code[]")
                lab_desc = request.POST.getlist("lab_desc[]")
                hrs = request.POST.getlist("hrs[]")
                lab_rate = request.POST.getlist("lab_rate[]")

                labour_total = Decimal("0")
                existing_labours = list(obj.labours.all().order_by("id"))
                existing_labours_by_id = {
                    str(labour.id): labour for labour in existing_labours
                }
                saved_labour_ids = []

                for i in range(len(job_code)):

                    if not job_code[i].strip():
                        continue

                    h = Decimal(hrs[i] or "0")
                    r = Decimal(lab_rate[i] or "0")
                    amount = h * r

                    labour_id = (
                        labour_ids[i]
                        if i < len(labour_ids)
                        else ""
                    )
                    labour = existing_labours_by_id.get(labour_id)

                    if labour is None:
                        labour = JobCardLabour(job=obj)

                    labour.job_code = job_code[i]
                    labour.description = lab_desc[i]
                    labour.labour_hrs = h
                    labour.rate = r
                    labour.amount = amount
                    labour.save()
                    saved_labour_ids.append(labour.id)

                    labour_total += amount

                obj.labours.exclude(id__in=saved_labour_ids).filter(
                    jobcardassessmentlabour__isnull=True
                ).delete()
                labour_total = sum(
                    (l.amount for l in obj.labours.all()),
                    Decimal("0")
                )

                # TOTALS + GST
                base_total = parts_total + labour_total
                gst_amount = base_total * Decimal("18") / Decimal("100")
                net_total = base_total + gst_amount

                obj.parts_total = parts_total
                obj.labour_total = labour_total
                obj.grand_total = base_total
                obj.gst_amount = gst_amount
                obj.net_total = net_total
                print("PART NOS:", request.POST.getlist("part_no[]"))
                print("LABOUR CODES:", request.POST.getlist("job_code[]"))
                print("POST KEYS:", request.POST.keys())
                obj.save()
                save_vehicle_condition_photos(request, obj)
                save_jobcard_signatures(request, obj)
                if job_created_date:
                    JobCard.objects.filter(pk=obj.pk).update(
                        job_date=job_created_date
                    )
                    obj.job_date = job_created_date

                if requested_main_status == "Closed":
                    JobCard.objects.filter(pk=obj.pk).update(
                        repair_status="Closed"
                    )
                    obj.repair_status = "Closed"
                elif obj.repair_status == "Closed" and can_reopen_jobcard:
                    JobCard.objects.filter(pk=obj.pk).update(
                        repair_status="Completed"
                    )
                    obj.repair_status = "Completed"

                insurance_company_id = request.POST.get("insurance_company")
                policy_no = request.POST.get("policy_no", "").strip()

                if claim:
                    if insurance_company_id:
                        claim.insurance_company_id = insurance_company_id

                    claim.policy_no = policy_no
                    claim.save()
                    save_claim_documents(request, claim)
                #claim.claim_stage = ClaimStageCode.ESTIMATE_CREATED
                #claim.save()
                if request.POST.get("send_whatsapp") == "on":
                    send_jobcard_whatsapp(obj)

                if (
                    is_admin_or_manager_user(request.user, logged_emp)
                    and obj.advisor
                    and obj.advisor.user
                    and obj.advisor.user != request.user
                ):
                    changed_items = []

                    if old_repair_status != obj.repair_status:
                        changed_items.append(f"status {old_repair_status} to {obj.repair_status}")

                    if old_grand_total != obj.grand_total:
                        changed_items.append(f"estimate amount {obj.grand_total}")

                    if old_parts_total != obj.parts_total or old_labour_total != obj.labour_total:
                        changed_items.append("part/labour estimate")

                    if old_expected_delivery != obj.expected_delivery_datetime:
                        changed_items.append("expected delivery")

                    detail = ", ".join(changed_items) if changed_items else "details"
                    notify_jobcard_advisor(
                        obj,
                        "Jobcard Updated",
                        f"Jobcard {obj.job_no} updated by {logged_emp.name if logged_emp else request.user.username}: {detail}",
                    )

                messages.success(
                    request,
                    f"Job Card {obj.job_no} updated successfully"
                )

            from django.urls import reverse

            return redirect(
                f"{reverse('jobcard_edit', args=[obj.id])}?saved=1"
            )

    else:
        form = JobCardForm(instance=job)

    if is_jobcard_locked:
        for field in form.fields.values():
            field.disabled = True

    job_progress_rows = []
    allocation = getattr(job, "allocation", None)
    can_close_current_jobcard = can_close_jobcard(job)
    close_ready_status = get_jobcard_close_ready_status(job)
    if allocation and claim and int(claim.claim_stage or 0) >= ClaimStageCode.REPAIR_IN_PROGRESS:
        progress_by_stage = {
            progress.stage: progress
            for progress in allocation.progress.select_related("employee")
        }
        last_touched_index = -1

        for index, (stage_key, stage_label) in enumerate(WorkProgress.STAGES):
            progress = progress_by_stage.get(stage_key)
            if progress and (progress.start_time or progress.finish_time):
                last_touched_index = index

        for index, (stage_key, stage_label) in enumerate(WorkProgress.STAGES):
            if index > last_touched_index:
                break

            progress = progress_by_stage.get(stage_key)
            if progress:
                job_progress_rows.append({
                    "label": stage_label,
                    "start_time": progress.start_time if progress else None,
                    "finish_time": progress.finish_time if progress else None,
                    "start_timestamp": (
                        int(progress.start_time.timestamp() * 1000)
                        if progress and progress.start_time
                        else ""
                    ),
                    "finish_timestamp": (
                        int(progress.finish_time.timestamp() * 1000)
                        if progress and progress.finish_time
                        else ""
                    ),
                    "employee": progress.employee.name if progress and progress.employee else "",
                    "remarks": progress.remarks if progress else "",
                    "status": (
                        "Completed" if progress and progress.finish_time
                        else "In Progress" if progress and progress.start_time
                        else "Pending"
                    ),
                })

    return render(request, "jobcard/jobcardEntry.html", {
        "form": form,
        "claim": claim,
        "job": job,
        "job_created_date_value": datetime_local_value(job.job_date),
        "can_change_advisor": can_change_advisor,
        "can_edit_jobcard_entries": can_edit_jobcard_entries,
        "can_reopen_jobcard": can_reopen_jobcard,
        "can_approve_second_approval": can_approve_second_approval,
        "second_approval_pending": second_approval_pending,
        "additional_approval_parts": additional_approval_parts,
        "additional_approval_labours": additional_approval_labours,
        "additional_approval_total_count": additional_approval_total_count,
        "additional_approval_approved_count": additional_approval_approved_count,
        "additional_approval_rejected_count": additional_approval_rejected_count,
        "additional_approval_pending_count": additional_approval_pending_count,
        "is_jobcard_locked": is_jobcard_locked,
        "logged_emp": logged_emp,
        "insurance_companies": insurance_companies,
        "is_cng_vehicle": is_cng_vehicle,
        "parts": job.parts.all(),
        "labours": job.labours.all(),
        "job_progress_rows": job_progress_rows,
        "can_close_jobcard": can_close_current_jobcard,
        "close_ready_status": close_ready_status,
        "vehicle_photo_slots": get_vehicle_condition_photo_slots(job),
        "claim_document_slots": get_claim_document_slots(claim),
        "PDF_SECRET_TOKEN": settings.PDF_SECRET_TOKEN,
        **get_inventory_context(job),

        # ✅ BREADCRUMB
        "breadcrumbs": [

            {
                "title": "Jobcards",
                "url": "",
                "icon": "fa fa-list"
            },

            {
                "title": "Job Card List",
                "url": "jobList",
                "icon": "fa fa-file"
            },

            {
                "title": "Edit Job Card",
                "icon": "fa fa-plus"
            }
        ]

    })


@require_POST
@never_cache
@login_required
def jobcard_second_approval_action(request, pk):
    job = get_object_or_404(
        JobCard.objects.select_related("claim", "advisor", "claim__employee"),
        pk=pk,
    )
    logged_emp = Employee.objects.filter(user=request.user).first()

    if not can_update_second_approval(request.user, logged_emp, job):
        messages.error(request, "You are not allowed to update 2nd Approval.")
        return redirect("jobcard_edit", pk=job.id)

    action = request.POST.get("second_approval_action")

    if action == "line_decision":
        allocation = getattr(job, "allocation", None)
        if not allocation:
            messages.error(request, "Work allocation not found.")
            return redirect("jobcard_edit", pk=job.id)

        part_ids = {
            value
            for value in request.POST.getlist("approval_part_id[]")
            if value.isdigit()
        }
        labour_ids = {
            value
            for value in request.POST.getlist("approval_labour_id[]")
            if value.isdigit()
        }
        part_status_by_id = {
            key.removeprefix("approval_part_status_"): value
            for key, value in request.POST.items()
            if key.startswith("approval_part_status_")
            and key.removeprefix("approval_part_status_").isdigit()
            and value in ["Approved", "Rejected", "Pending"]
        }
        labour_status_by_id = {
            key.removeprefix("approval_labour_status_"): value
            for key, value in request.POST.items()
            if key.startswith("approval_labour_status_")
            and key.removeprefix("approval_labour_status_").isdigit()
            and value in ["Approved", "Rejected", "Pending"]
        }
        has_rejected = False
        has_pending = False

        for part in allocation.parts.filter(is_additional=True, id__in=part_ids):
            status = part_status_by_id.get(str(part.id), "Pending")
            if status == "Rejected":
                has_rejected = True
            elif status == "Pending":
                has_pending = True

            part.advisor_approval_status = status
            update_fields = ["advisor_approval_status"]

            if status in ["Approved", "Rejected"]:
                part.decision = "New" if status == "Approved" else "Reject"
                update_fields.append("decision")

            part.save(update_fields=update_fields)

            if status in ["Approved", "Rejected"]:
                JobCardAssessmentPart.objects.filter(
                    job=job,
                    part=part.job_part,
                ).update(decision=part.decision)

        for labour in allocation.labours.filter(is_additional=True, id__in=labour_ids):
            status = labour_status_by_id.get(str(labour.id), "Pending")
            if status == "Rejected":
                has_rejected = True
            elif status == "Pending":
                has_pending = True

            labour.advisor_approval_status = status
            update_fields = ["advisor_approval_status"]

            if status in ["Approved", "Rejected"]:
                labour.decision = "Approved" if status == "Approved" else "Reject"
                update_fields.append("decision")

            labour.save(update_fields=update_fields)

            if status in ["Approved", "Rejected"]:
                JobCardAssessmentLabour.objects.filter(
                    job=job,
                    labour=labour.job_labour,
                ).update(decision=labour.decision)

        job.additional_approval_required = True
        if has_rejected:
            job.second_approval_status = "Rejected"
        elif has_pending:
            job.second_approval_status = "Pending"
        else:
            job.second_approval_status = "Approved"
        job.save(update_fields=[
            "additional_approval_required",
            "second_approval_status",
        ])

        messages.success(request, "Line level 2nd Approval updated.")
        return redirect("jobcard_edit", pk=job.id)

    if action == "approve":
        job.second_approval_status = "Approved"
        job.additional_approval_required = True
        line_status = "Approved"
        message = "2nd Approval marked Approved."
    elif action == "reject":
        job.second_approval_status = "Rejected"
        job.additional_approval_required = True
        line_status = "Rejected"
        message = "2nd Approval marked Rejected."
    else:
        messages.error(request, "Invalid 2nd Approval action.")
        return redirect("jobcard_edit", pk=job.id)

    job.save(update_fields=[
        "additional_approval_required",
        "second_approval_status",
    ])

    allocation = getattr(job, "allocation", None)
    if allocation:
        allocation.parts.filter(
            is_additional=True,
            advisor_approval_status="Pending",
        ).update(advisor_approval_status=line_status)
        allocation.labours.filter(
            is_additional=True,
            advisor_approval_status="Pending",
        ).update(advisor_approval_status=line_status)

    messages.success(request, message)
    return redirect("jobcard_edit", pk=job.id)


@never_cache
@login_required
def jobcard_list_api(request):
    logged_emp = Employee.objects.filter(user=request.user).first()
    jobs = JobCard.objects.select_related(
        "claim",
        "advisor",
        "claim__vehicle",
        "claim__vehicle__model",
        "claim__vehicle__customer"
    ).prefetch_related(
        "allocation__progress",
        "allocation__parts",
    ).all()

    repair_status = request.GET.get("repair_status", "").strip()
    work_progress_filter = request.GET.get("work_progress", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if repair_status:
        jobs = jobs.filter(repair_status=repair_status)

    if date_from:
        jobs = jobs.filter(job_date__date__gte=date_from)

    if date_to:
        jobs = jobs.filter(job_date__date__lte=date_to)
    if request.user.is_superuser:
        pass  # keep all jobs

    elif logged_emp and logged_emp.employee_type.upper() == "ADVISOR":
        jobs = jobs.filter(advisor=logged_emp)

    else:
        pass  # keep all jobs
    data = []

    for job in jobs:
        allocation = getattr(job, "allocation", None)
        work_progress_status = get_work_progress_status(allocation)

        if job.additional_approval_required and job.second_approval_status:
            work_progress_status = (
                f"{work_progress_status} / 2nd Approval {job.second_approval_status}"
            )

        if (
            work_progress_filter
            and work_progress_filter.lower() != "all"
            and work_progress_filter not in work_progress_status
        ):
            continue

        data.append({
            "id": job.id,
            "job_no": job.job_no,
            "job_date": job.job_date,
            "claim__claim_no": job.claim.claim_no if job.claim else "",
            "claim__vehicle__registration_no": job.claim.vehicle.registration_no if job.claim and job.claim.vehicle else "",
            "claim__vehicle__model__name": job.claim.vehicle.model.name if job.claim and job.claim.vehicle and job.claim.vehicle.model else "",
            "claim__vehicle__customer__name": job.claim.vehicle.customer.name if job.claim and job.claim.vehicle and job.claim.vehicle.customer else "",
            "advisor__name": job.advisor.name if job.advisor else "",
            "vehicle_inward_type": job.vehicle_inward_type,
            "gate_in_datetime": job.gate_in_datetime,
            "repair_status": job.repair_status,
            "work_progress_status": work_progress_status,
            "parts_not_available_status": get_parts_not_available_status(allocation),
            "parts_total": job.parts_total,
            "labour_total": job.labour_total,
            "grand_total": job.grand_total,
            "created_at": job.created_at,
        })

    return JsonResponse(data, safe=False)


from .models import CompanySetup
from .forms import CompanySetupForm


@login_required
def company_setup(request):
    company = CompanySetup.objects.first()

    if request.method == 'POST':
        form = CompanySetupForm(
            request.POST,
            request.FILES,
            instance=company
        )

        if form.is_valid():
            form.save()
            return redirect('company_setup')

    else:
        form = CompanySetupForm(instance=company)

    return render(request, 'core/company_setup.html', {
        'form': form
    })


from django.db import transaction

from openpyxl import load_workbook

from .forms import ItemExcelUploadForm


@login_required
def upload_itemdata_excel(request):
    if request.method == "POST":
        if request.POST.get("part_master_action") == "save":
            item_id = request.POST.get("item_id") or ""
            part_no = (request.POST.get("part_no") or "").strip().upper()
            part_description = (request.POST.get("part_description") or "").strip()
            model_name = (request.POST.get("model") or "").strip()

            if not part_no or not part_description:
                messages.error(request, "Part No and Part Description are required.")
                return redirect("part")

            duplicate_qs = ItemData.objects.filter(item_code__iexact=part_no)

            if item_id:
                duplicate_qs = duplicate_qs.exclude(id=item_id)

            if duplicate_qs.exists():
                messages.error(request, f"Part No {part_no} already exists.")
                return redirect("part")

            if item_id:
                item = get_object_or_404(ItemData, id=item_id)
                message = "Part updated successfully."
            else:
                item = ItemData()
                message = "Part saved successfully."

            item.item_code = part_no
            item.item_name = part_description
            item.category = model_name
            item.status = "Active"
            item.save()
            messages.success(request, message)
            return redirect("part")

        form = ItemExcelUploadForm(request.POST, request.FILES)

        if form.is_valid():
            excel_file = request.FILES["excel_file"]

            wb = load_workbook(excel_file, read_only=True, data_only=True)
            ws = wb.active

            items = []
            skipped_count = 0

            for row_no, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                item_code = str(row[0]).strip() if row[0] else ""
                item_name = str(row[1]).strip() if row[1] else ""
                category = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                rate = row[3] if len(row) > 3 and row[3] else 0
                status = str(row[4]).strip() if len(row) > 4 and row[4] else "Active"

                if not item_code or not item_name:
                    skipped_count += 1
                    continue

                items.append(ItemData(
                    item_code=item_code,
                    item_name=item_name,
                    category=category,
                    rate=rate,
                    status=status,
                ))

            with transaction.atomic():
                ItemData.objects.bulk_create(
                    items,
                    batch_size=5000,
                    ignore_conflicts=True
                )

            messages.success(
                request,
                f"Upload done. DB total rows: {ItemData.objects.count()}, Skipped: {skipped_count}"
            )

            return redirect("partlist")

        messages.error(request, "Invalid form or file not selected.")
        return redirect("part")

    else:
        form = ItemExcelUploadForm()

    search_text = (request.GET.get("q") or "").strip()
    edit_id = request.GET.get("edit") or ""
    items = ItemData.objects.all().order_by("item_name")

    if search_text:
        items = items.filter(
            Q(item_code__icontains=search_text)
            | Q(item_name__icontains=search_text)
            | Q(category__icontains=search_text)
        )

    edit_item = ItemData.objects.filter(id=edit_id).first() if edit_id else None
    model_options = (
        ItemData.objects.exclude(category__isnull=True)
        .exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    return render(request, "master/partmaster.html", {
        "form": form,
        "items": items[:100],
        "edit_item": edit_item,
        "search_text": search_text,
        "model_options": model_options,
    })


@login_required
def itemdata_list(request):
    items = ItemData.objects.all().order_by("item_name")

    context = {
        "items": items
    }

    return render(request, "master/itemdata_list.html", context)


def sync_part_orders(job, header=None, part_ids=None):
    created_count = 0

    if header is None:
        header = PartOrderHeader.objects.create(
            job=job,
            vehicle=job.claim.vehicle if job.claim and job.claim.vehicle else None,
            order_no=job.part_order_no or "",
            order_date=job.part_order_date,
            status="Pending",
        )

    parts = job.parts.all()

    if part_ids:
        parts = parts.filter(id__in=part_ids)

    for part in parts:
        order, created = PartOrder.objects.get_or_create(
            order=header,
            job=job,
            part=part,
            defaults={
                "ordered_qty": part.qty,
                "status": "Pending",
            }
        )

        if order.order_id is None:
            order.order = header
            order.save(update_fields=["order"])

        if created:
            created_count += 1

    return created_count


def get_part_order_lines_status(orders, completed_status="Received"):
    orders = list(orders)

    if not orders:
        return "Pending"

    statuses = {order.status for order in orders}

    if statuses == {"Received"}:
        return completed_status

    if "Back Order" in statuses:
        return "Back Order"

    if "Received" in statuses:
        return "Partially Received"

    if "In Transit" in statuses:
        return "In Transit"

    if "Order Placed" in statuses:
        return "Order Placed"

    if "Cancelled" in statuses and len(statuses) == 1:
        return "Cancelled"

    return "Pending"


def sync_part_order_header(header):
    if not header:
        return None

    header.status = get_part_order_lines_status(
        header.lines.all(),
        completed_status="Received"
    )
    header.save(update_fields=["status", "updated_at"])
    return header


@never_cache
@login_required
def part_order_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    orders = PartOrder.objects.select_related(
        "job",
        "job__claim",
        "job__claim__vehicle",
        "job__claim__vehicle__customer",
        "part",
    )

    if q:
        orders = orders.filter(
            Q(job__job_no__icontains=q)
            | Q(job__claim__claim_no__icontains=q)
            | Q(job__claim__vehicle__registration_no__icontains=q)
            | Q(job__claim__vehicle__customer__name__icontains=q)
            | Q(part__part_no__icontains=q)
            | Q(part__description__icontains=q)
        )

    if status:
        orders = orders.filter(status=status)

    summary = {
        "pending": orders.filter(status="Pending").count(),
        "ordered": orders.filter(status="Order Placed").count(),
        "transit": orders.filter(status="In Transit").count(),
        "received": orders.filter(status="Received").count(),
        "back_order": orders.filter(status="Back Order").count(),
    }

    return render(request, "parts/partOrderList.html", {
        "orders": orders.order_by("expected_date", "-updated_at"),
        "statuses": PartOrder.STATUS_CHOICES,
        "status_values": [
            value for value, label in PartOrder.STATUS_CHOICES
        ],
        "selected_status": status,
        "q": q,
        "summary": summary,
    })


@never_cache
@login_required
def part_order_create(request):
    jobs = JobCard.objects.select_related(
        "claim",
        "claim__vehicle",
        "claim__vehicle__customer",
    ).order_by("-id")
    vehicles = Vehicle.objects.select_related(
        "customer",
        "model",
    ).order_by("registration_no")

    if request.method == "POST":
        job_id = request.POST.get("job_id") or ""
        vehicle_id = request.POST.get("vehicle_id") or ""
        order_no = request.POST.get("order_no", "").strip()
        order_date = request.POST.get("order_date") or None
        expected_date = request.POST.get("expected_date") or None
        supplier = request.POST.get("supplier", "").strip()
        remarks = request.POST.get("remarks", "").strip()
        part_no_list = request.POST.getlist("part_no[]")
        part_desc_list = request.POST.getlist("part_desc[]")
        qty_list = request.POST.getlist("qty[]")

        job = JobCard.objects.filter(id=job_id).select_related(
            "claim",
            "claim__vehicle",
        ).first() if job_id else None
        vehicle = None

        if job and job.claim:
            vehicle = job.claim.vehicle
        elif vehicle_id:
            vehicle = Vehicle.objects.filter(id=vehicle_id).first()

        valid_lines = []

        for index, part_no in enumerate(part_no_list):
            part_no = part_no.strip()
            description = (
                part_desc_list[index].strip()
                if index < len(part_desc_list)
                else ""
            )
            qty = (
                qty_list[index]
                if index < len(qty_list)
                else "0"
            )

            if not part_no and not description:
                continue

            valid_lines.append({
                "part_no": part_no,
                "description": description,
                "qty": Decimal(qty or "0"),
            })

        if not job and not vehicle:
            messages.error(
                request,
                "Select either Job Card or Vehicle Registration No."
            )
        elif not valid_lines:
            messages.error(
                request,
                "Enter at least one part line."
            )
        else:
            with transaction.atomic():
                header = PartOrderHeader.objects.create(
                    job=job,
                    vehicle=vehicle,
                    order_no=order_no,
                    order_date=order_date,
                    expected_date=expected_date,
                    supplier=supplier,
                    status="Pending",
                    remarks=remarks,
                )

                for line in valid_lines:
                    PartOrder.objects.create(
                        order=header,
                        job=job,
                        part=None,
                        manual_part_no=line["part_no"],
                        manual_description=line["description"],
                        ordered_qty=line["qty"],
                        status="Pending",
                    )

                sync_part_order_header(header)

            messages.success(request, "Part order saved successfully.")
            if request.POST.get("print_after_save") == "1":
                return redirect("part_order_print", header_id=header.id)
            return redirect("part_order_list")

    return render(request, "parts/partOrderCreate.html", {
        "jobs": jobs,
        "vehicles": vehicles,
    })


@never_cache
@login_required
def part_order_print(request, header_id):
    header = get_object_or_404(
        PartOrderHeader.objects.select_related(
            "job",
            "job__claim",
            "job__claim__vehicle",
            "job__claim__vehicle__customer",
            "job__claim__vehicle__model",
            "vehicle",
            "vehicle__customer",
            "vehicle__model",
        ),
        id=header_id
    )
    job = header.job
    claim = job.claim if job else None
    vehicle = claim.vehicle if claim and claim.vehicle else header.vehicle
    lines = list(header.lines.select_related("part").order_by("id"))

    return render(request, "parts/partOrderPrint.html", {
        "header": header,
        "job": job,
        "job_created_date_value": datetime_local_value(job.job_date),
        "claim": claim,
        "vehicle": vehicle,
        "lines": lines,
    })


@never_cache
@require_POST
@login_required
def create_part_order_from_job(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)
    data = {}

    if request.body:
        data = json.loads(request.body.decode("utf-8"))

    header = PartOrderHeader.objects.create(
        job=job,
        vehicle=job.claim.vehicle if job.claim and job.claim.vehicle else None,
        order_no=data.get("order_no") or "",
        order_date=data.get("order_date") or None,
        expected_date=data.get("expected_date") or None,
        supplier=data.get("supplier") or "",
        status="Pending",
    )
    part_ids = data.get("part_ids") or None
    created_count = sync_part_orders(
        job,
        header=header,
        part_ids=part_ids
    )

    sync_part_order_header(header)

    return JsonResponse({
        "status": "success",
        "order_id": header.id,
        "created_count": created_count,
        "redirect_url": reverse(
            "part_order_job_detail",
            args=[job.id]
        ) + f"?order_id={header.id}"
    })

@never_cache
@login_required
def part_order_job_detail(request, job_id):
    job = get_object_or_404(
        JobCard.objects.select_related(
            "claim",
            "claim__vehicle",
            "claim__vehicle__customer",
            "claim__vehicle__model",
            "advisor",
        ),
        id=job_id
    )

    selected_order_id = request.GET.get("order_id")

    if request.method == "POST":
        order_ids = request.POST.getlist("order_id[]")
        touched_headers = set()

        for order_id in order_ids:
            order = PartOrder.objects.filter(
                id=order_id,
                job=job
            ).first()

            if not order:
                continue

            prefix = f"order_{order_id}_"
            order.order_no = request.POST.get(prefix + "order_no", "").strip()
            order.supplier = request.POST.get(prefix + "supplier", "").strip()
            order.order_date = request.POST.get(prefix + "order_date") or None
            order.expected_date = request.POST.get(prefix + "expected_date") or None
            order.received_date = request.POST.get(prefix + "received_date") or None
            order.ordered_qty = Decimal(request.POST.get(prefix + "ordered_qty") or "0")
            order.received_qty = Decimal(request.POST.get(prefix + "received_qty") or "0")
            order.status = request.POST.get(prefix + "status") or "Pending"
            order.tracking_ref = request.POST.get(prefix + "tracking_ref", "").strip()
            order.remarks = request.POST.get(prefix + "remarks", "").strip()

            if (
                order.ordered_qty
                and order.received_qty >= order.ordered_qty
                and order.status not in ["Cancelled", "Back Order"]
            ):
                order.status = "Received"

            order.save()
            if order.order_id:
                touched_headers.add(order.order_id)

        for header in PartOrderHeader.objects.filter(id__in=touched_headers):
            sync_part_order_header(header)

        if request.POST.get("print_after_save") == "1":
            print_header_id = selected_order_id or (
                next(iter(touched_headers)) if touched_headers else ""
            )

            if print_header_id:
                return redirect(
                    "part_order_print",
                    header_id=print_header_id
                )

        redirect_url = reverse("part_order_job_detail", args=[job.id])
        if selected_order_id:
            redirect_url += f"?order_id={selected_order_id}"
        return redirect(redirect_url)

    headers = job.part_order_headers.order_by("-id")
    selected_header = None

    if selected_order_id:
        selected_header = headers.filter(id=selected_order_id).first()

    if selected_header is None:
        selected_header = headers.first()

    orders = PartOrder.objects.filter(job=job).select_related("part")

    if selected_header:
        orders = orders.filter(order=selected_header)
    else:
        orders = orders.none()

    orders = orders.order_by("part__id")

    return render(request, "parts/partOrderDetail.html", {
        "job": job,
        "headers": headers,
        "selected_header": selected_header,
        "orders": orders,
        "job_part_order_status": get_job_part_order_status(job),
        "statuses": PartOrder.STATUS_CHOICES,
    })


def get_job_part_order_status(job):
    return get_part_order_lines_status(
        job.part_orders.all(),
        completed_status="Completed"
    )


@login_required
@never_cache
def part_order_jobs_api(request):
    jobs = JobCard.objects.select_related(
        "claim",
        "claim__vehicle",
        "claim__vehicle__customer",
        "claim__vehicle__model",
        "advisor",
    ).prefetch_related("parts", "part_orders").order_by("-id")

    data = []

    for job in jobs:
        orders = list(job.part_orders.all())
        header = job.part_order_headers.order_by("-id").first()
        total_parts = job.parts.count()
        ordered_parts = len(orders)
        received_parts = sum(1 for order in orders if order.status == "Received")
        back_order_parts = sum(1 for order in orders if order.status == "Back Order")

        data.append({
            "id": job.id,
            "job_no": job.job_no,
            "claim_no": job.claim.claim_no if job.claim else "",
            "reg_no": job.claim.vehicle.registration_no if job.claim and job.claim.vehicle else "",
            "model": job.claim.vehicle.model.name if job.claim and job.claim.vehicle and job.claim.vehicle.model else "",
            "customer": job.claim.vehicle.customer.name if job.claim and job.claim.vehicle and job.claim.vehicle.customer else "",
            "advisor": job.advisor.name if job.advisor else "",
            "job_date": job.job_date.strftime("%d-%m-%Y") if job.job_date else "",
            "order_status": get_job_part_order_status(job),
            "order_no": header.order_no if header else "",
            "order_date": header.order_date.strftime("%d-%m-%Y") if header and header.order_date else "",
            "order_count": job.part_order_headers.count(),
            "total_parts": total_parts,
            "ordered_parts": ordered_parts,
            "received_parts": received_parts,
            "back_order_parts": back_order_parts,
            "has_order": ordered_parts > 0,
        })

    return JsonResponse(data, safe=False)


@login_required
@never_cache
def part_order_headers_api(request):
    headers = PartOrderHeader.objects.select_related(
        "job",
        "job__claim",
        "job__claim__vehicle",
        "job__claim__vehicle__customer",
        "job__claim__vehicle__model",
        "vehicle",
        "vehicle__customer",
        "vehicle__model",
    ).prefetch_related("lines").order_by("-id")

    data = []

    for header in headers:
        job = header.job
        claim = job.claim if job else None
        vehicle = claim.vehicle if claim and claim.vehicle else header.vehicle
        line_count = header.lines.count()
        received_count = header.lines.filter(status="Received").count()
        back_order_count = header.lines.filter(status="Back Order").count()

        data.append({
            "id": header.id,
            "job_id": job.id if job else "",
            "order_no": header.order_no or f"Order #{header.id}",
            "order_date": header.order_date.strftime("%d-%m-%Y") if header.order_date else "",
            "expected_date": header.expected_date.strftime("%d-%m-%Y") if header.expected_date else "",
            "supplier": header.supplier,
            "status": header.status,
            "line_count": line_count,
            "received_count": received_count,
            "back_order_count": back_order_count,
            "job_no": job.job_no if job else "",
            "claim_no": claim.claim_no if claim else "",
            "reg_no": vehicle.registration_no if vehicle else "",
            "model": vehicle.model.name if vehicle and vehicle.model else "",
            "customer": vehicle.customer.name if vehicle and vehicle.customer else "",
        })

    return JsonResponse(data, safe=False)


@login_required
@never_cache
def part_order_job_headers_api(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)
    headers = job.part_order_headers.order_by("-id")

    data = []

    for header in headers:
        line_count = header.lines.count()
        data.append({
            "id": header.id,
            "order_no": header.order_no or f"Order #{header.id}",
            "order_date": header.order_date.strftime("%Y-%m-%d") if header.order_date else "",
            "expected_date": header.expected_date.strftime("%Y-%m-%d") if header.expected_date else "",
            "supplier": header.supplier,
            "status": header.status,
            "line_count": line_count,
        })

    return JsonResponse(data, safe=False)


@login_required
@never_cache
def part_order_job_orders_api(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)
    order_id = request.GET.get("order_id")
    orders = PartOrder.objects.filter(
        job=job
    ).select_related("part").order_by("part__id")

    if order_id:
        orders = orders.filter(order_id=order_id)
    else:
        header = job.part_order_headers.order_by("-id").first()
        orders = orders.filter(order=header) if header else orders.none()

    data = []

    for order in orders:
        part_no = order.part.part_no if order.part else order.manual_part_no
        description = order.part.description if order.part else order.manual_description
        estimated_qty = order.part.qty if order.part else order.ordered_qty

        data.append({
            "id": order.id,
            "part_no": part_no,
            "description": description,
            "estimated_qty": str(estimated_qty),
            "ordered_qty": str(order.ordered_qty),
            "received_qty": str(order.received_qty),
            "status": order.status,
            "order_no": order.order_no,
            "supplier": order.supplier,
            "order_date": order.order_date.strftime("%Y-%m-%d") if order.order_date else "",
            "expected_date": order.expected_date.strftime("%Y-%m-%d") if order.expected_date else "",
            "received_date": order.received_date.strftime("%Y-%m-%d") if order.received_date else "",
            "tracking_ref": order.tracking_ref,
            "remarks": order.remarks,
        })

    return JsonResponse(data, safe=False)


@login_required
@never_cache
def part_order_header_lines_api(request, header_id):
    header = get_object_or_404(PartOrderHeader, id=header_id)
    orders = header.lines.select_related("part").order_by("part__id")

    data = []

    for order in orders:
        part_no = order.part.part_no if order.part else order.manual_part_no
        description = order.part.description if order.part else order.manual_description
        estimated_qty = order.part.qty if order.part else order.ordered_qty

        data.append({
            "id": order.id,
            "part_no": part_no,
            "description": description,
            "estimated_qty": str(estimated_qty),
            "ordered_qty": str(order.ordered_qty),
            "received_qty": str(order.received_qty),
            "status": order.status,
            "order_no": order.order_no,
            "supplier": order.supplier,
            "order_date": order.order_date.strftime("%Y-%m-%d") if order.order_date else "",
            "expected_date": order.expected_date.strftime("%Y-%m-%d") if order.expected_date else "",
            "received_date": order.received_date.strftime("%Y-%m-%d") if order.received_date else "",
            "tracking_ref": order.tracking_ref,
            "remarks": order.remarks,
        })

    return JsonResponse(data, safe=False)


@require_POST
@login_required
@never_cache
def update_part_order_line_api(request, order_id):
    order = get_object_or_404(PartOrder, id=order_id)
    data = json.loads(request.body.decode("utf-8"))

    for field in [
        "order_no",
        "supplier",
        "status",
        "tracking_ref",
        "remarks",
    ]:
        if field in data:
            setattr(order, field, data.get(field) or "")

    for field in ["order_date", "expected_date", "received_date"]:
        if field in data:
            setattr(order, field, data.get(field) or None)

    if "ordered_qty" in data:
        order.ordered_qty = Decimal(str(data.get("ordered_qty") or "0"))

    if "received_qty" in data:
        order.received_qty = Decimal(str(data.get("received_qty") or "0"))

    if (
        order.ordered_qty
        and order.received_qty >= order.ordered_qty
        and order.status not in ["Cancelled", "Back Order"]
    ):
        order.status = "Received"

    order.save()
    sync_part_order_header(order.order)
    job_status = get_job_part_order_status(order.job) if order.job else ""

    return JsonResponse({
        "status": "success",
        "job_status": job_status,
        "line_status": order.status,
    })


@require_POST
@login_required
@never_cache
def delete_part_order_line_api(request, order_id):
    order = get_object_or_404(PartOrder, id=order_id)
    job = order.job
    header = order.order
    order.delete()

    if header:
        sync_part_order_header(header)

    return JsonResponse({
        "status": "success",
        "job_status": get_job_part_order_status(job) if job else "",
    })


@login_required
@never_cache
def jobcard_assessment_api(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)

    parts = []
    for p in job.parts.all():
        ass = JobCardAssessmentPart.objects.filter(
            job=job,
            part=p
        ).first()

        parts.append({
            "id": p.id,
            "part_no": p.part_no,
            "description": p.description,
            "amount": str(p.amount),
            "decision": ass.decision if ass else "None",
            "revised_amount": str(ass.revised_amount) if ass else str(p.amount),
        })

    labours = []
    for l in job.labours.all():
        ass = JobCardAssessmentLabour.objects.filter(
            job=job,
            labour=l
        ).first()

        labours.append({
            "id": l.id,
            "job_code": l.job_code,
            "description": l.description,
            "amount": str(l.amount),
            "decision": ass.decision if ass else "None",
            "deduction_percent": str(ass.deduction_percent) if ass else "0",
            "revised_amount": str(ass.revised_amount) if ass else str(l.amount),
        })

    return JsonResponse({
        "parts": parts,
        "labours": labours,
        "job_no": job.job_no,
        "requires_dms_job_no": job.job_no.startswith("JOB-"),
    })


@require_POST
@login_required
@never_cache
def save_jobcard_assessment(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)

    data = json.loads(request.body.decode("utf-8"))

    parts = data.get("parts", [])
    labours = data.get("labours", [])
    dms_job_no = str(data.get("job_no") or "").strip()

    if not parts and not labours:
        return JsonResponse({
            "status": "error",
            "message": "Add at least one Part or Labour line before saving assessment."
        })

    if job.job_no.startswith("JOB-"):
        if not dms_job_no:
            return JsonResponse({
                "status": "error",
                "message": "DMS Jobcard No required before saving assessment."
            })

        duplicate = JobCard.objects.filter(job_no__iexact=dms_job_no).exclude(id=job.id).exists()
        if duplicate:
            return JsonResponse({
                "status": "error",
                "message": "DMS Jobcard No already exists."
            })

    with transaction.atomic():
        if job.job_no.startswith("JOB-") and dms_job_no:
            job.job_no = dms_job_no
            job.save(update_fields=["job_no"])

        for p in parts:
            if p.get("is_new"):
                part = JobCardPart.objects.create(
                    job=job,
                    part_no=p.get("part_no", ""),
                    description=p.get("description", ""),
                    qty=Decimal("1"),
                    rate=Decimal(p.get("amount") or "0"),
                    amount=Decimal(p.get("amount") or "0"),
                )
            else:
                part_id = p.get("id")

                if not part_id:
                    continue

                part = get_object_or_404(
                    JobCardPart,
                    id=part_id,
                    job=job
                )

            JobCardAssessmentPart.objects.update_or_create(
                job=job,
                part=part,
                defaults={
                    "decision": p.get("decision", "New"),
                    "revised_amount": Decimal(p.get("revised_amount") or "0"),
                }
            )
        for l in labours:
            if l.get("is_new"):
                labour = JobCardLabour.objects.create(
                    job=job,
                    job_code=l.get("job_code", ""),
                    description=l.get("description", ""),
                    labour_hrs=Decimal("1"),
                    rate=Decimal(l.get("amount") or "0"),
                    amount=Decimal(l.get("amount") or "0"),
                )
            else:
                labour_id = l.get("id")

                if not labour_id:
                    continue

                labour = get_object_or_404(
                    JobCardLabour,
                    id=labour_id,
                    job=job
                )

            JobCardAssessmentLabour.objects.update_or_create(
                job=job,
                labour=labour,
                defaults={
                    "decision": l.get("decision"),
                    "deduction_percent": Decimal(l.get("deduction_percent") or "0"),
                    "revised_amount": Decimal(l.get("revised_amount") or "0"),
                }
            )

    return JsonResponse({
        "status": "success"
    })


@login_required
@never_cache
def assessment_print(request, pk):
    job = get_object_or_404(
        JobCard.objects.select_related(
            "claim",
            "claim__vehicle",
            "claim__vehicle__customer",
            "claim__vehicle__model",
            "claim__vehicle__variant",
            "advisor",
        ),
        pk=pk
    )

    assessed_parts = JobCardAssessmentPart.objects.filter(
        job=job
    ).select_related("part").order_by("part__id")

    assessed_labours = JobCardAssessmentLabour.objects.filter(
        job=job
    ).select_related("labour").order_by("labour__id")
    new_panel_parts = [
        item for item in assessed_parts
        if item.decision in ["New", "KO"]
    ]
    repair_panel_parts = [
        item for item in assessed_parts
        if item.decision == "Repair"
    ]
    new_panel_rows = new_panel_parts[:11] + [None] * max(0, 11 - len(new_panel_parts))
    repair_panel_rows = repair_panel_parts[:10] + [None] * max(0, 10 - len(repair_panel_parts))

    allocation = getattr(job, "allocation", None)
    progress_by_stage = {}

    if allocation:
        for progress in allocation.progress.select_related("employee").all():
            progress_by_stage[progress.stage] = progress

    repair_progress = progress_by_stage.get("Repair")
    painting_progress = progress_by_stage.get("Painting")
    fitting_progress = progress_by_stage.get("Fitting")

    parts_total = sum(
        (item.part.amount for item in assessed_parts),
        Decimal("0")
    )
    parts_revised_total = sum(
        (item.revised_amount for item in assessed_parts),
        Decimal("0")
    )
    labour_total = sum(
        (item.labour.amount for item in assessed_labours),
        Decimal("0")
    )
    labour_revised_total = sum(
        (item.revised_amount for item in assessed_labours),
        Decimal("0")
    )

    return render(request, "jobcard/assessmentPrint.html", {
        "job": job,
        "claim": job.claim,
        "assessed_parts": assessed_parts,
        "assessed_labours": assessed_labours,
        "allocation": allocation,
        "new_panel_rows": new_panel_rows,
        "repair_panel_rows": repair_panel_rows,
        "repair_progress": repair_progress,
        "painting_progress": painting_progress,
        "fitting_progress": fitting_progress,
        "parts_total": parts_total,
        "parts_revised_total": parts_revised_total,
        "labour_total": labour_total,
        "labour_revised_total": labour_revised_total,
        "grand_total": parts_total + labour_total,
        "grand_revised_total": parts_revised_total + labour_revised_total,
    })


from django.http import JsonResponse, HttpResponse
from .models import ItemData


@login_required
def part_lookup(request):
    part_no = request.GET.get("item_code", "").strip()

    item = ItemData.objects.filter(
        item_code__iexact=part_no
    ).first()

    if not item:
        return JsonResponse({
            "status": "error",
            "message": "Part not found"
        })

    return JsonResponse({
        "status": "success",
        "description": item.item_name,
        "rate": str(item.rate),
    })


from django.http import HttpResponseForbidden
from django.shortcuts import render
from .models import JobCard, JobCardInventory


@never_cache
def jobcard_print_preview(request, pk, token=None):
    # allow if token is correct OR user is logged in
    if token != settings.PDF_SECRET_TOKEN and not request.user.is_authenticated:
        return HttpResponseForbidden("Not allowed")

    job = get_object_or_404(JobCard, pk=pk)
    variant_name = ""
    claim = job.claim
    if (
            claim
            and claim.vehicle
            and claim.vehicle.variant
    ):
        variant_name = claim.vehicle.variant.name or ""

    is_cng_vehicle = "CNG" in variant_name.upper()

    inventory = JobCardInventory.objects.filter(job=job).first()

    raw_damages = inventory.damage_marks if inventory else []

    damages = [
        d for d in raw_damages
        if d.get("x") not in [None, "", 0, "0"]
           and d.get("y") not in [None, "", 0, "0"]
    ]

    # if your FK is jobcard, use:
    # inventory = JobCardInventory.objects.filter(jobcard=job).first()

    return render(request, "jobcard/jobcardPrint.html", {
        "job": job,
        "claim": job.claim,
        "parts": job.parts.all(),
        "labours": job.labours.all(),
        "inventory": inventory,
        "is_cng_vehicle": is_cng_vehicle,
        "damages": inventory.damage_marks if inventory else [],
        "fuel_percent": inventory.fuel_percent if inventory else 0,
        **get_inventory_context(job),
    })

@login_required
def estimate_print(request, pk):
    job = get_object_or_404(
        JobCard.objects.select_related(
            "claim",
            "claim__vehicle",
            "claim__vehicle__model",
            "claim__vehicle__customer",
            "advisor"
        ),
        pk=pk
    )

    return render(request, "jobcard/estimatePrint.html", {
        "job": job,
        "claim": job.claim,
        "parts": job.parts.all(),
        "labours": job.labours.all(),
    })


import json
from decimal import Decimal, InvalidOperation


def save_job_inventory(request, job):
    damage_marks_raw = request.POST.get("damage_marks", "[]")

    try:
        damage_marks = json.loads(damage_marks_raw)
    except json.JSONDecodeError:
        damage_marks = []

    JobCardInventory.objects.update_or_create(
        job=job,
        defaults={
            "lh_mirror": int(request.POST.get("lh_mirror") == "on"),
            "mud_flap_count": int(request.POST.get("mud_flap_count") or 0),
            "floor_mat_count": int(request.POST.get("floor_mat_count") or 0),
            "rh_mirror": int(request.POST.get("rh_mirror") == "on"),
            "center_mirror": int(request.POST.get("center_mirror") == "on"),
            "frt_wiper": int(request.POST.get("frt_wiper") == "on"),
            "rr_wiper": int(request.POST.get("rr_wiper") == "on"),
            "accessories": int(request.POST.get("accessories") == "on"),
            "spare_wheel": request.POST.get("spare_wheel") == "on",
            "jack": request.POST.get("jack") == "on",
            "tool_kit": request.POST.get("tool_kit") == "on",
            "stereo": request.POST.get("stereo") == "on",
            "battery": request.POST.get("battery") == "on",
            "number_plate": request.POST.get("number_plate") == "on",

            "fuel_percent": int(request.POST.get("fuel_percent") or 0),
            "cng_percent": int(request.POST.get("cng_percent") or 0),
            "damage_marks": damage_marks,

            "remarks": request.POST.get("inventory_remarks", ""),
        }
    )

    save_tyre_inventory(request, job)


def save_tyre_inventory(request, job):
    positions = request.POST.getlist("tyre_position[]")
    makes = request.POST.getlist("tyre_make[]")
    sizes = request.POST.getlist("tyre_size[]")
    depths = request.POST.getlist("tyre_depth[]")
    wheel_cap = request.POST.getlist("tyre_wheel_cap[]")

    for i in range(len(positions)):

        depth_value = None

        if depths[i]:
            try:
                depth_value = Decimal(depths[i])
            except InvalidOperation:
                depth_value = None
        print(wheel_cap[i])
        JobCardTyreInventory.objects.update_or_create(
            job=job,
            position=positions[i],
            defaults={
                "make": makes[i],
                "size": sizes[i],
                "depth": depth_value,
                "wheel_cap": wheel_cap[i],
            }
        )


def link_callback(uri, rel):
    # MEDIA files
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        if os.path.exists(path):
            return path

    # STATIC files
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        if os.path.exists(path):
            return path

    return uri


def generate_jobcard_pdf(job):
    template = get_template("jobcard/jobcardPrint.html")

    html = template.render({
        "job": job,
        "claim": job.claim,
        "parts": job.parts.all(),
        "labours": job.labours.all(),
        **get_inventory_context(job),
    })
    result = BytesIO()

    pisa_status = pisa.CreatePDF(
        html,
        dest=result,
        link_callback=link_callback
    )

    if pisa_status.err:
        return None

    return result.getvalue()


import requests
from django.core.files.base import ContentFile
from django.utils import timezone


def send_jobcard_whatsapp(job):
    customer = job.claim.vehicle.customer
    mobile = customer.mobile_no

    if not mobile:
        return None

    mobile = "91" + mobile[-10:]

    pdf_bytes = generate_jobcard_pdf(job)

    if not pdf_bytes:
        return None

    filename = get_next_jobcard_pdf_filename(job)

    log = CommunicationLog.objects.create(
        job=job,
        channel="WhatsApp",
        mobile_no=mobile,
        message=f"Job Card {job.job_no}",
        status="Pending"
    )

    log.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    pdf_url = settings.SITE_URL.rstrip("/") + log.pdf_file.url

    print("PDF URL:", pdf_url)

    url = (
        f"https://graph.facebook.com/v23.0/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": mobile,
        "type": "document",
        "document": {
            "link": pdf_url,
            "filename": filename,
            "caption": (
                f"Dear {customer.name},\n"
                f"Your Job Card {job.job_no} has been created.\n"
                f"Vehicle: {job.claim.vehicle.registration_no}\n"
                f"Thank you."
            )
        }
    }

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )

        print("WHATSAPP STATUS:", response.status_code)
        print("WHATSAPP RESPONSE:", response.text)

        log.response = response.text

        if response.status_code in [200, 201]:
            log.status = "Sent"
            log.sent_at = timezone.now()
        else:
            log.status = "Failed"

        log.save()
        return log

    except Exception as e:
        print("WHATSAPP ERROR:", str(e))

        log.status = "Failed"
        log.response = str(e)
        log.save()
        return log


from django.shortcuts import get_object_or_404
from django.shortcuts import redirect


@login_required
def whatsapp_text_link(request, pk):
    job = get_object_or_404(JobCard, pk=pk)

    customer = job.claim.vehicle.customer

    if not customer.mobile_no:
        return redirect("jobcard_edit", pk=pk)

    mobile = "91" + customer.mobile_no[-10:]

    latest_log = (
        job.communications
        .exclude(pdf_file="")
        .order_by("-id")
        .first()
    )

    pdf_url = ""

    if latest_log and latest_log.pdf_file:
        pdf_url = (
                settings.SITE_URL.rstrip("/")
                + latest_log.pdf_file.url
        )

    message = (
        f"Dear {customer.name},\n"
        f"Your Job Card {job.job_no} has been created.\n"
        f"Vehicle: {job.claim.vehicle.registration_no}\n\n"
        f"PDF Copy:\n{pdf_url}"
    )

    whatsapp_url = (
        "https://web.whatsapp.com/send"
        f"?phone={mobile}"
        f"&text={quote(message)}"
    )

    return redirect(whatsapp_url)


from urllib.parse import urlencode, quote
from django.urls import reverse

from playwright.sync_api import sync_playwright
import time


def generate_jobcard_pdf(job):
    url = (
            settings.SITE_URL
            + reverse("jobcard_print", args=[job.id, settings.PDF_SECRET_TOKEN])

            + "?"
            + urlencode({"v": int(time.time())})
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            ignore_https_errors=True
        )

        page = context.new_page()

        page.goto(
            url,
            wait_until="networkidle"
        )

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={
                "top": "8mm",
                "right": "8mm",
                "bottom": "8mm",
                "left": "8mm",
            }
        )

        context.close()
        browser.close()

    return pdf_bytes


import os
from django.conf import settings


def get_next_jobcard_pdf_filename(job):
    job_no = job.job_no

    folder = os.path.join(
        settings.MEDIA_ROOT,
        "jobcard_pdfs",
        job_no
    )

    os.makedirs(folder, exist_ok=True)

    existing = [
        f for f in os.listdir(folder)
        if f.endswith(".pdf")
    ]

    version = len(existing) + 1

    return f"jobcard_{job_no}_v{version}.pdf"


@login_required
def vehicle_detail_api(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)

    return JsonResponse({
        "id": vehicle.id,
        "registration_no": vehicle.registration_no,
        "id_chassis_no": vehicle.chassis_no,
        "id_engine_no": vehicle.engine_no,
        "id_vehicle_type": vehicle.vehicle_type,
        "model": vehicle.model_id,
        "variant": vehicle.variant_id,
        "id_color": vehicle.color,
        "id_sale_date": vehicle.sale_date,
        "customer": vehicle.customer_id,
        "customer_name": vehicle.customer.name if vehicle.customer else "",
    })


@login_required
def unread_notifications(request):
    queryset = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by("-created_at")

    notifications = queryset[:10]

    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "url": n.url,
        }
        for n in notifications
    ]

    return JsonResponse({
        "count": queryset.count(),
        "notifications": data,
    })


@login_required
def mark_notification_read(request, pk):
    UserNotification.objects.filter(
        id=pk,
        user=request.user
    ).update(is_read=True)

    return JsonResponse({"status": "success"})


from django.contrib import messages


def validate_claim_stage_before_next(claim):
    missing = []
    # stage 3 → before going to stage 4
    if claim.claim_stage == ClaimStageCode.ADVISOR_ASSIGNED:

        has_jobcard = JobCard.objects.filter(
            claim=claim
        ).exists()

        if not has_jobcard:
            missing.append(
                "Job Card / Estimation not created"
            )

        if missing:
            return False, missing
    if claim.claim_stage == 3:

        if not claim.intimation_date:
            missing.append("Claim Intimation Date")

        if not claim.insurance_company:
            missing.append("Insurance Company")

        if not claim.policy_no:
            missing.append("Policy No")

        if not claim.ic_claim_no:
            missing.append("Insurance Claim No")

        if missing:
            return False, missing

    # stage 4 → before going to stage 5
    if claim.claim_stage == 4:

        missing = []

        if not claim.survey_date:
            missing.append("Survey Date")

        if not claim.surveyor:
            missing.append("Surveyor")

        if not claim.survey_status:
            missing.append("Survey Status")

        if missing:
            return False, missing

    # stage 5 → before going to stage 6
    if claim.claim_stage == 5:

        missing = []

        if not claim.insurance_approval_date:
            missing.append("Insurance Approval Date")

        if not claim.assessment_file:
            missing.append("Assessment File")

        if missing:
            return False, missing

    if claim.claim_stage == ClaimStageCode.WORK_ALLOCATION:
        has_progress_started = WorkProgress.objects.filter(
            allocation__job__claim=claim,
            start_time__isnull=False,
        ).exists()

        if not has_progress_started:
            return False, [
                "Start at least one progress stage from Work Allocation"
            ]

    if claim.claim_stage == ClaimStageCode.REPAIR_IN_PROGRESS:
        return False, [
            "Work Completed must be marked from Work Allocation"
        ]

    if claim.claim_stage == ClaimStageCode.INVOICED:

        missing = []

        if not claim.invoice_datetime:
            missing.append("Invoice Date & Time")

        if not claim.invoice_amount or claim.invoice_amount <= 0:
            missing.append("Invoice Amount")

        if not claim.payment_mode:
            missing.append("Payment Mode")

        if missing:
            return False, missing

    if claim.claim_stage == ClaimStageCode.DELIVERY:

        missing = []

        if not claim.delivery_datetime:
            missing.append("Delivery Date & Time")

        if not claim.delivered_by:
            missing.append("Delivered By")

        if not claim.delivered_to:
            missing.append("Delivered To")

        if claim.delivered_to == "Drop By Driver" and not claim.delivery_driver_name:
            missing.append("Driver Name")

        if missing:
            return False, missing

    return True, []


def get_work_progress_status(allocation):
    if not allocation:
        return "Work Not Started"

    progress_by_stage = {
        progress.stage: progress
        for progress in allocation.progress.all()
    }
    latest_started = None
    all_finished = True

    for stage_key, stage_label in WorkProgress.STAGES:
        progress = progress_by_stage.get(stage_key)

        if progress and progress.start_time:
            latest_started = (
                stage_label,
                "Completed" if progress.finish_time else "Started"
            )
            if not progress.finish_time:
                all_finished = False
            continue

        all_finished = False

    if not latest_started:
        return "Work Not Started"

    if all_finished:
        return "Work Completed"

    stage_label, status_text = latest_started
    return f"{stage_label} {status_text}"


def get_jobcard_main_status(job):
    if not job:
        return "Open"

    claim = job.claim

    if claim and claim.status == "Cancelled":
        return "Cancellation"

    if job.repair_status == "Closed":
        return "Closed"

    if claim and int(claim.claim_stage or 0) == ClaimStageCode.CLOSED:
        return "Closed"

    allocation = getattr(job, "allocation", None)

    if not allocation:
        return "Open"

    has_started = False
    all_finished = True

    for progress in allocation.progress.all():
        if progress.start_time:
            has_started = True

            if not progress.finish_time:
                all_finished = False
        else:
            all_finished = False

    if has_started and all_finished:
        return "Completed"

    return "Open"


def can_close_jobcard(job):
    return all(get_jobcard_close_ready_status(job).values())


def get_jobcard_close_ready_status(job):
    if not job:
        return {
            "work_completed": False,
            "qc_done": False,
            "ri_done": False,
            "part_entry_complete": False,
        }

    allocation = getattr(job, "allocation", None)

    work_completed = (
        job.repair_status in ["Completed", "Closed"]
        or (
            job.claim
            and int(job.claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
        )
    )

    ri_done = bool(job.reinspection_done) or (
        job.claim
        and int(job.claim.claim_stage or 0) >= ClaimStageCode.LIABILITY
    )

    return {
        "work_completed": work_completed,
        "qc_done": bool(job.qc_done),
        "ri_done": ri_done,
        "part_entry_complete": bool(allocation and allocation.part_entry_complete),
    }


def get_jobcard_close_pending_items(job):
    status = get_jobcard_close_ready_status(job)
    labels = {
        "work_completed": "Work Completed",
        "qc_done": "QC Done",
        "ri_done": "RI Done",
        "part_entry_complete": "Part Entry Complete",
    }

    return [
        labels[key]
        for key, is_ready in status.items()
        if not is_ready
    ]


def sync_jobcard_main_status(job):
    status = get_jobcard_main_status(job)

    if job and job.repair_status != status:
        job.repair_status = status
        job.save(update_fields=["repair_status"])

    return status


def get_parts_not_available_status(allocation):
    if not allocation:
        return "No PNA"

    pna_count = sum(
        1
        for part in allocation.parts.all()
        if part.decision in ["New", "KO"] and not part.pick_from_store
    )

    if pna_count:
        return f"{pna_count} Parts Not Available"

    return "No PNA"


def get_control_board_allocated_at(allocation):
    if not allocation:
        return None

    first_progress = (
        allocation.progress
        .filter(start_time__isnull=False)
        .order_by("start_time")
        .first()
    )

    if first_progress:
        return first_progress.start_time

    return allocation.allotment_date


def get_control_board_current_status(allocation):
    if not allocation:
        return "Work Allocation Pending", "bg-warning text-dark"

    job = allocation.job
    if (
        job.repair_status == "Completed"
        or int(job.claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
    ):
        return "Work Completed", "bg-success"

    running_progress = (
        allocation.progress
        .filter(start_time__isnull=False, finish_time__isnull=True)
        .order_by("-start_time", "-id")
        .first()
    )
    if running_progress:
        return f"{running_progress.get_stage_display()} Running", "bg-primary"

    finished_progress = (
        allocation.progress
        .filter(finish_time__isnull=False)
        .order_by("-finish_time", "-id")
        .first()
    )
    if finished_progress:
        return f"{finished_progress.get_stage_display()} Completed", "bg-info text-dark"

    status = get_work_progress_status(allocation)
    return status, "bg-warning text-dark" if status == "Work Allocation Pending" else "bg-info text-dark"


def control_board_date_value(value):
    if not value:
        return None

    if hasattr(value, "date"):
        return timezone.localdate(value)

    return value


def get_control_board_in_date(job):
    return control_board_date_value(job.gate_in_datetime) or job.job_date


def get_control_board_promise_date(job):
    return (
        control_board_date_value(job.expected_delivery_datetime)
        or control_board_date_value(job.estimated_delivery)
    )


def get_control_board_tat_days(job):
    in_date = get_control_board_in_date(job)

    if not in_date:
        return ""

    claim = job.claim
    is_closed = (
        job.repair_status == "Closed"
        and int(claim.claim_stage or 0) == ClaimStageCode.CLOSED
    )

    end_date = timezone.localdate()
    if is_closed:
        end_date = (
            control_board_date_value(claim.delivery_datetime)
            or control_board_date_value(job.actual_delivery)
            or end_date
        )

    return max((end_date - in_date).days, 0)


def get_control_board_promise_class(job):
    promise_date = get_control_board_promise_date(job)
    if not promise_date:
        return ""

    today = timezone.localdate()
    days_left = (promise_date - today).days

    if days_left < 0:
        return "promise-overdue"

    if days_left <= 2:
        return "promise-warning"

    return ""


def control_board_datetime_value(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value)

    value = datetime.combine(value, datetime_time.min)
    return timezone.make_aware(value)


def control_board_timeline_created_at(claim, keywords):
    if not claim:
        return None

    keywords = [keyword.upper() for keyword in keywords]
    timeline_rows = list(getattr(claim, "_prefetched_objects_cache", {}).get("timeline", []))
    if not timeline_rows:
        timeline_rows = list(claim.timeline.all())

    for row in timeline_rows:
        text = f"{row.stage or ''} {row.remarks or ''}".upper()
        if all(keyword in text for keyword in keywords):
            return row.created_at

    return None


def control_board_duration_text(start_at, end_at):
    if not start_at or not end_at:
        return "Not recorded"

    seconds = max(int((end_at - start_at).total_seconds()), 0)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    return f"{days}d {hours}h {minutes}m"


def get_control_board_tat_timeline(job):
    claim = job.claim
    allocation = getattr(job, "allocation", None)
    first_progress = None
    last_progress = None

    if allocation:
        first_progress = (
            allocation.progress
            .filter(start_time__isnull=False)
            .order_by("start_time")
            .first()
        )
        last_progress = (
            allocation.progress
            .filter(finish_time__isnull=False)
            .order_by("-finish_time")
            .first()
        )

    events = [
        ("Gate In", control_board_datetime_value(job.gate_in_datetime)),
        ("Claim Created", control_board_datetime_value(claim.created_at)),
        (
            "Advisor Assigned",
            control_board_timeline_created_at(claim, ["ADVISOR"])
            or control_board_timeline_created_at(claim, ["ASSIGNED"]),
        ),
        ("Jobcard Created", control_board_datetime_value(job.created_at)),
        ("Claim Intimation", control_board_datetime_value(claim.intimation_date)),
        ("Survey Done", control_board_datetime_value(claim.survey_date)),
        ("Insurance Approval", control_board_datetime_value(claim.insurance_approval_date)),
        ("Work Allocation", control_board_datetime_value(allocation.allotment_date) if allocation else None),
        ("Repair Started", first_progress.start_time if first_progress else None),
        ("Work Completed", last_progress.finish_time if last_progress else None),
        ("Re Inspection", control_board_datetime_value(job.reinspection_date)),
        ("Liability", control_board_datetime_value(claim.liability_received_at)),
        ("Invoiced", control_board_datetime_value(claim.invoice_datetime)),
        ("Delivery / Closed", control_board_datetime_value(claim.delivery_datetime)),
    ]

    rows = []
    for index in range(1, len(events)):
        start_label, start_at = events[index - 1]
        end_label, end_at = events[index]
        rows.append({
            "label": f"{start_label} → {end_label}",
            "start_at": start_at,
            "end_at": end_at,
            "duration": control_board_duration_text(start_at, end_at),
        })

    return rows


def get_control_board_stage_and_status(allocation, pna_parts):
    job = allocation.job
    claim = job.claim

    if (
        job.repair_status == "Closed"
        and int(claim.claim_stage or 0) == ClaimStageCode.CLOSED
    ):
        return "Delivered", "🟢 Delivered", "status-ready"

    if (
        job.repair_status == "Completed"
        or int(claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
    ):
        return "Work Completed", "🟢 Work Completed", "status-ready"

    if pna_parts:
        return "Parts Ordered", "🟠 Waiting Parts", "status-waiting"

    if job.ready_for_delivery or int(claim.claim_stage or 0) >= ClaimStageCode.DELIVERY:
        return "Ready For Delivery", "🟢 Ready For Delivery", "status-ready"

    if job.qc_done:
        return "QC Done", "🟢 Ready For Delivery", "status-ready"

    running_progress = (
        allocation.progress
        .filter(start_time__isnull=False, finish_time__isnull=True)
        .order_by("-start_time", "-id")
        .first()
    )
    if running_progress:
        return running_progress.get_stage_display(), "🔵 In Process", "status-process"

    return claim.get_claim_stage_display(), "🟡 Pending", "status-pending"


def get_control_board_progress_status(allocation):
    job = allocation.job

    if job.reinspection_done:
        return "RI Done"

    if job.qc_done:
        return "QC Done"

    if (
        job.repair_status == "Completed"
        or int(job.claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
    ):
        return "Work Completed"

    running_progress = (
        allocation.progress
        .filter(start_time__isnull=False, finish_time__isnull=True)
        .order_by("-start_time", "-id")
        .first()
    )
    if running_progress:
        return f"{running_progress.get_stage_display()} Running"

    finished_progress = (
        allocation.progress
        .filter(finish_time__isnull=False)
        .order_by("-finish_time", "-id")
        .first()
    )
    if finished_progress:
        return f"{finished_progress.get_stage_display()} Completed"

    allocated_progress = (
        allocation.progress
        .filter(employee__isnull=False)
        .order_by("-id")
        .first()
    )
    if allocated_progress:
        return f"{allocated_progress.get_stage_display()} Allocated"

    return "Progress Not Started"


def get_control_board_pna_parts(allocation):
    if not allocation:
        return []

    return [
        part
        for part in allocation.parts.all()
        if part.decision in ["New", "KO"] and not part.pick_from_store
    ]


def progress_row_has_data(progress):
    return bool(
        progress
        and (
            progress.start_time
            or progress.finish_time
            or progress.employee_id
            or (progress.remarks or "").strip()
            or progress.photos.exists()
        )
    )


def claim_has_repair_progress_data(claim):
    if not claim:
        return False

    progress_qs = WorkProgress.objects.filter(
        allocation__job__claim=claim
    ).prefetch_related("photos")

    return any(progress_row_has_data(progress) for progress in progress_qs)


def workshop_resource_queryset():
    return Employee.objects.filter(
        is_active=True
    ).filter(
        Q(designation__icontains="Denter")
        | Q(designation__icontains="Painter")
        | Q(designation__icontains="Technician")
        | Q(designation__icontains="Paint")
        | Q(employee_type__icontains="Denter")
        | Q(employee_type__icontains="Painter")
        | Q(employee_type__icontains="Technician")
    ).order_by("designation", "name")


def clamp_hour(value, default):
    try:
        hour = int(value)
    except (TypeError, ValueError):
        return default

    return max(0, min(hour, 23))


def resource_slot_payload(progress):
    job = progress.allocation.job
    claim = job.claim
    vehicle = claim.vehicle if claim else None

    return {
        "job_id": job.id,
        "job_no": job.job_no,
        "claim_no": claim.claim_no if claim else "",
        "registration_no": vehicle.registration_no if vehicle else "",
        "model": (
            vehicle.model.name
            if vehicle and vehicle.model
            else ""
        ),
        "stage": progress.get_stage_display(),
        "is_running": not bool(progress.finish_time),
    }


@never_cache
@xframe_options_sameorigin
@login_required
def workshop_resource_view(request):
    from datetime import time, timedelta

    logged_emp = Employee.objects.filter(user=request.user).first()

    if not (
        request.user.is_superuser
        or is_admin_or_manager_user(request.user, logged_emp)
        or is_floor_supervisor(logged_emp)
    ):
        messages.error(request, "You are not allowed to access Workshop Resource.")
        return redirect("dashboard")

    today = timezone.localdate()
    from_date = parse_date(request.GET.get("from_date") or "") or today
    to_date = parse_date(request.GET.get("to_date") or "") or from_date

    if to_date < from_date:
        to_date = from_date

    max_days = 7
    if (to_date - from_date).days >= max_days:
        to_date = from_date + timedelta(days=max_days - 1)
        messages.info(request, "Workshop resource view is limited to 7 days at a time.")

    start_hour = clamp_hour(request.GET.get("start_hour"), 9)
    end_hour = clamp_hour(request.GET.get("end_hour"), 19)
    selected_employee_id = request.GET.get("employee_id") or ""
    resource_query = (request.GET.get("resource_q") or "").strip()
    role_filter = (request.GET.get("role") or "").strip()

    if end_hour <= start_hour:
        end_hour = min(start_hour + 1, 23)

    previous_from_date = from_date - timedelta(days=1)
    previous_to_date = to_date - timedelta(days=1)
    next_from_date = from_date + timedelta(days=1)
    next_to_date = to_date + timedelta(days=1)
    hours = list(range(start_hour, end_hour))
    base_resources = list(workshop_resource_queryset())
    resource_roles = sorted({
        resource.designation or resource.employee_type
        for resource in base_resources
        if resource.designation or resource.employee_type
    })
    filtered_resources = base_resources

    if resource_query:
        query = resource_query.lower()
        filtered_resources = [
            resource
            for resource in filtered_resources
            if query in (resource.name or "").lower()
            or query in (resource.employee_code or "").lower()
            or query in (resource.designation or "").lower()
        ]

    if role_filter:
        filtered_resources = [
            resource
            for resource in filtered_resources
            if (resource.designation or resource.employee_type) == role_filter
        ]

    resources = filtered_resources
    current_tz = timezone.get_current_timezone()
    range_start = timezone.make_aware(
        datetime.combine(from_date, time(start_hour, 0)),
        current_tz,
    )
    range_end = timezone.make_aware(
        datetime.combine(to_date, time(end_hour, 0)),
        current_tz,
    )

    progress_rows = list(
        WorkProgress.objects.select_related(
            "employee",
            "allocation",
            "allocation__job",
            "allocation__job__claim",
            "allocation__job__claim__vehicle",
            "allocation__job__claim__vehicle__model",
        )
        .filter(
            employee__in=resources,
            start_time__isnull=False,
            start_time__lt=range_end,
        )
        .filter(
            Q(finish_time__isnull=True)
            | Q(finish_time__gt=range_start)
        )
        .order_by("start_time", "id")
    )

    progress_by_employee = {}
    for progress in progress_rows:
        progress_by_employee.setdefault(progress.employee_id, []).append(progress)

    days = []
    current_day = from_date
    now = timezone.now()

    while current_day <= to_date:
        day_rows = []

        for employee in resources:
            cells = []
            busy_hours = 0

            for hour in hours:
                slot_start = timezone.make_aware(
                    datetime.combine(current_day, time(hour, 0)),
                    current_tz,
                )
                slot_end = slot_start + timedelta(hours=1)
                items = []

                for progress in progress_by_employee.get(employee.id, []):
                    progress_start = progress.start_time
                    progress_end = progress.finish_time or now

                    if progress_end < progress_start:
                        progress_end = progress_start

                    if progress_start < slot_end and progress_end > slot_start:
                        items.append(resource_slot_payload(progress))

                if items:
                    busy_hours += 1

                cells.append({
                    "label": f"{hour:02d}:00",
                    "items": items,
                })

            day_rows.append({
                "employee": employee,
                "role": employee.designation or employee.employee_type,
                "busy_hours": busy_hours,
                "available_hours": len(hours) - busy_hours,
                "cells": cells,
                "is_selected": str(employee.id) == selected_employee_id,
            })

        busy_resource_count = sum(1 for row in day_rows if row["busy_hours"] > 0)
        days.append({
            "date": current_day,
            "rows": day_rows,
            "busy_resource_count": busy_resource_count,
            "free_resource_count": len(day_rows) - busy_resource_count,
        })
        current_day += timedelta(days=1)

    return render(request, "floor/workshopResource.html", {
        "days": days,
        "hours": hours,
        "filter_from_date": from_date.strftime("%Y-%m-%d"),
        "filter_to_date": to_date.strftime("%Y-%m-%d"),
        "start_hour": start_hour,
        "end_hour": end_hour,
        "previous_from_date": previous_from_date.strftime("%Y-%m-%d"),
        "previous_to_date": previous_to_date.strftime("%Y-%m-%d"),
        "next_from_date": next_from_date.strftime("%Y-%m-%d"),
        "next_to_date": next_to_date.strftime("%Y-%m-%d"),
        "resource_count": len(resources),
        "total_resource_count": len(base_resources),
        "resource_query": resource_query,
        "role_filter": role_filter,
        "resource_roles": resource_roles,
        "selected_employee_id": selected_employee_id,
        "modal_mode": request.GET.get("modal") == "1",
        "breadcrumbs": [
            {
                "title": "WorkShop / Floor",
                "url": "",
                "icon": "fa fa-list",
            },
            {
                "title": "Workshop Resource",
                "icon": "fa fa-calendar",
            },
        ],
    })


@never_cache
@login_required
def work_allocation_list(request):
    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    if not is_floor_supervisor(logged_emp):
        messages.error(request, "You are not allowed to access Work Allocation")
        return redirect("dashboard")

    jobs = JobCard.objects.select_related(
        "claim",
        "claim__vehicle",
        "claim__vehicle__customer",
        "claim__vehicle__model",
        "advisor",
        "allocation",
    ).filter(
        claim__claim_stage__gte=ClaimStageCode.WORK_ALLOCATION,
        claim__claim_stage__lt=ClaimStageCode.CLOSED,
    ).prefetch_related(
        "allocation__progress"
    ).order_by("-id")

    for job in jobs:
        allocation = getattr(job, "allocation", None)
        job.work_allocation_action = "Allocate"
        job.work_allocation_status = "Work Allocation Pending"
        job.work_allocation_status_class = "bg-warning text-dark"

        if not allocation:
            continue

        job.work_allocation_action = "Edit"
        if (
            job.repair_status == "Completed"
            or int(job.claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
        ):
            job.work_allocation_status = "Work Completed"
            job.work_allocation_status_class = "bg-success"
        elif (
            job.additional_approval_required
            and (job.second_approval_status or "Pending") == "Pending"
        ):
            job.work_allocation_status = (
                f"2nd Approval {job.second_approval_status or 'Pending'}"
            )
            job.work_allocation_status_class = "bg-danger"
        else:
            job.work_allocation_status = get_work_progress_status(allocation)
            job.work_allocation_status_class = (
                "bg-success"
                if job.work_allocation_status == "Work Completed"
                else "bg-info text-dark"
            )

    work_progress_count = sum(
        1
        for job in jobs
        if getattr(job, "work_allocation_status", "") not in [
            "Work Allocation Pending",
            "Work Completed",
        ]
    )
    pending_count = sum(
        1
        for job in jobs
        if getattr(job, "work_allocation_status", "") == "Work Allocation Pending"
    )
    completed_count = sum(
        1
        for job in jobs
        if getattr(job, "work_allocation_status", "") == "Work Completed"
    )

    return render(request, "floor/workAllocationList.html", {
        "jobs": jobs,
        "logged_emp": logged_emp,
        "work_progress_count": work_progress_count,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "breadcrumbs": [
            {
                "title": "WorkShop/Floor",
                "url": "",
                "icon": "fa fa-list"
            },
            {
                "title": "Work Allocation",
                "icon": "fa fa-tools"
            }
        ]
    })


@never_cache
@login_required
def bodyshop_control_menu(request):
    logged_emp = Employee.objects.filter(user=request.user).first()

    if not (
        request.user.is_superuser
        or is_admin_or_manager_user(request.user, logged_emp)
        or is_floor_supervisor(logged_emp)
    ):
        messages.error(request, "You are not allowed to access Bodyshop Control Board")
        return redirect("dashboard")

    today = timezone.localdate()
    allocations = (
        WorkAllocation.objects
        .select_related(
            "job",
            "job__claim",
            "job__claim__vehicle",
            "job__claim__vehicle__customer",
            "job__claim__vehicle__model",
            "job__claim__insurance_company",
            "job__claim__surveyor",
            "job__advisor",
        )
        .prefetch_related("progress", "parts", "parts__job_part")
        .filter(job__claim__claim_stage__lt=ClaimStageCode.CLOSED)
        .exclude(job__repair_status="Closed")
    )

    status_counts = {
        "pending": 0,
        "waiting_parts": 0,
        "in_process": 0,
        "work_completed": 0,
        "ready": 0,
        "delivered": 0,
    }
    delay_count = 0
    today_delivery_count = 0
    parts_pending_count = 0
    technician_workload = {}
    tat_buckets = {
        "0-2 Days": 0,
        "3-5 Days": 0,
        "6-10 Days": 0,
        "10+ Days": 0,
    }

    for allocation in allocations:
        job = allocation.job
        pna_parts = get_control_board_pna_parts(allocation)
        _, board_status, _ = get_control_board_stage_and_status(allocation, pna_parts)
        status_key = "pending"

        if "Waiting Parts" in board_status:
            status_key = "waiting_parts"
        elif "In Process" in board_status:
            status_key = "in_process"
        elif "Work Completed" in board_status:
            status_key = "work_completed"
        elif "Ready For Delivery" in board_status:
            status_key = "ready"
        elif "Delivered" in board_status:
            status_key = "delivered"

        status_counts[status_key] += 1

        promise_date = get_control_board_promise_date(job)
        if promise_date and promise_date < today:
            delay_count += 1
        if promise_date == today or (
            job.claim.delivery_datetime
            and workflow_date_value(job.claim.delivery_datetime).date() == today
        ):
            today_delivery_count += 1

        if pna_parts:
            parts_pending_count += 1

        tat_days = get_control_board_tat_days(job)
        if tat_days != "":
            if tat_days <= 2:
                tat_buckets["0-2 Days"] += 1
            elif tat_days <= 5:
                tat_buckets["3-5 Days"] += 1
            elif tat_days <= 10:
                tat_buckets["6-10 Days"] += 1
            else:
                tat_buckets["10+ Days"] += 1

        running_rows = allocation.progress.filter(
            start_time__isnull=False,
            finish_time__isnull=True,
            employee__isnull=False,
        )
        for progress in running_rows:
            name = progress.employee.name if progress.employee else "Unassigned"
            technician_workload[name] = technician_workload.get(name, 0) + 1

    insurance_approval_pending = Claim.objects.filter(
        claim_stage__gte=ClaimStageCode.SURVEY,
        claim_stage__lt=ClaimStageCode.INSURANCE_APPROVAL,
    ).count()

    workload_rows = sorted(
        [
            {"name": name, "count": count}
            for name, count in technician_workload.items()
        ],
        key=lambda row: row["count"],
        reverse=True,
    )[:8]

    tat_rows = [
        {"label": label, "count": count}
        for label, count in tat_buckets.items()
    ]
    max_tat_count = max([row["count"] for row in tat_rows] + [1])
    for row in tat_rows:
        row["width"] = max(int((row["count"] / max_tat_count) * 100), 6) if row["count"] else 0

    module_cards = [
        {
            "title": "Stage-wise Kanban Board",
            "subtitle": "Live vehicle stage board",
            "count": allocations.count(),
            "class": "module-primary",
            "url": reverse("bodyshop_control_board"),
        },
        {
            "title": "Delay Vehicles",
            "subtitle": "Promise date overdue",
            "count": delay_count,
            "class": "module-danger",
            "url": f"{reverse('bodyshop_control_board')}?status=open",
        },
        {
            "title": "Today's Delivery List",
            "subtitle": "Due or delivered today",
            "count": today_delivery_count,
            "class": "module-success",
            "url": f"{reverse('bodyshop_control_board')}?status=open",
        },
        {
            "title": "Insurance Approval Pending",
            "subtitle": "Survey done, approval pending",
            "count": insurance_approval_pending,
            "class": "module-warning",
            "url": f"{reverse('bodyshop_control_board')}?status=open",
        },
        {
            "title": "Parts Pending",
            "subtitle": "PNA / waiting parts",
            "count": parts_pending_count,
            "class": "module-orange",
            "url": reverse("part_order_list"),
        },
        {
            "title": "Technician Workload",
            "subtitle": "Running jobs by resource",
            "count": sum(row["count"] for row in workload_rows),
            "class": "module-info",
            "url": reverse("workshop_resource"),
        },
        {
            "title": "TAT Graph",
            "subtitle": "Ageing by in-date",
            "count": sum(row["count"] for row in tat_rows),
            "class": "module-purple",
            "url": reverse("bodyshop_control_board"),
        },
        {
            "title": "Live Vehicle Count by Status",
            "subtitle": "Current board summary",
            "count": sum(status_counts.values()),
            "class": "module-dark",
            "url": reverse("bodyshop_control_board"),
        },
    ]

    status_rows = [
        {"label": "Pending", "count": status_counts["pending"], "class": "status-pending"},
        {"label": "Waiting Parts", "count": status_counts["waiting_parts"], "class": "status-waiting"},
        {"label": "In Process", "count": status_counts["in_process"], "class": "status-process"},
        {"label": "Work Completed", "count": status_counts["work_completed"], "class": "status-completed"},
        {"label": "Ready For Delivery", "count": status_counts["ready"], "class": "status-ready"},
        {"label": "Delivered", "count": status_counts["delivered"], "class": "status-delivered"},
    ]

    return render(request, "floor/bodyshopControlMenu.html", {
        "module_cards": module_cards,
        "status_rows": status_rows,
        "tat_rows": tat_rows,
        "workload_rows": workload_rows,
        "breadcrumbs": [
            {
                "title": "WorkShop/Floor",
                "url": "",
                "icon": "fa fa-list",
            },
            {
                "title": "Control Board",
                "icon": "fa fa-table",
            },
        ],
    })


@never_cache
@login_required
def bodyshop_control_board(request):
    logged_emp = Employee.objects.filter(user=request.user).first()

    if not (
        request.user.is_superuser
        or is_admin_or_manager_user(request.user, logged_emp)
        or is_floor_supervisor(logged_emp)
    ):
        messages.error(request, "You are not allowed to access Bodyshop Control Board")
        return redirect("dashboard")

    search = (request.GET.get("search") or "").strip()
    status_filter = request.GET.get("status") or "open"
    insurance_filter = request.GET.get("insurance") or ""
    advisor_filter = request.GET.get("advisor") or ""
    surveyor_filter = request.GET.get("surveyor") or ""

    allocations = (
        WorkAllocation.objects
        .select_related(
            "job",
            "job__claim",
            "job__claim__vehicle",
            "job__claim__vehicle__customer",
            "job__claim__vehicle__model",
            "job__claim__insurance_company",
            "job__claim__surveyor",
            "job__advisor",
        )
        .prefetch_related(
            "progress",
            "parts",
            "parts__job_part",
            "job__claim__timeline",
        )
        .order_by("-allotment_date", "-job__id")
    )

    if status_filter == "open":
        allocations = allocations.filter(
            job__claim__claim_stage__lt=ClaimStageCode.CLOSED
        ).exclude(job__repair_status="Closed")
    elif status_filter == "completed":
        allocations = allocations.filter(job__repair_status="Completed")
    elif status_filter == "closed":
        allocations = allocations.filter(
            Q(job__claim__claim_stage=ClaimStageCode.CLOSED)
            | Q(job__repair_status="Closed")
        )

    if search:
        allocations = allocations.filter(
            Q(job__job_no__icontains=search)
            | Q(job__claim__claim_no__icontains=search)
            | Q(job__claim__vehicle__registration_no__icontains=search)
            | Q(job__claim__vehicle__customer__name__icontains=search)
            | Q(job__claim__vehicle__model__name__icontains=search)
        )

    if insurance_filter:
        allocations = allocations.filter(job__claim__insurance_company_id=insurance_filter)

    if advisor_filter:
        allocations = allocations.filter(job__advisor_id=advisor_filter)

    if surveyor_filter:
        allocations = allocations.filter(job__claim__surveyor_id=surveyor_filter)

    rows = []
    pna_count = 0
    work_completed_count = 0
    running_count = 0

    for allocation in allocations:
        status_text, status_class = get_control_board_current_status(allocation)
        pna_parts = get_control_board_pna_parts(allocation)
        current_stage, board_status, board_status_class = (
            get_control_board_stage_and_status(allocation, pna_parts)
        )

        if pna_parts:
            pna_count += 1
        if status_text == "Work Completed":
            work_completed_count += 1
        if "Running" in status_text:
            running_count += 1

        rows.append({
            "allocation": allocation,
            "job": allocation.job,
            "allocated_at": get_control_board_allocated_at(allocation),
            "in_date": get_control_board_in_date(allocation.job),
            "promise_date": get_control_board_promise_date(allocation.job),
            "promise_class": get_control_board_promise_class(allocation.job),
            "tat_days": get_control_board_tat_days(allocation.job),
            "tat_timeline": get_control_board_tat_timeline(allocation.job),
            "current_stage": current_stage,
            "claim_stage": allocation.job.claim.get_claim_stage_display(),
            "progress_status": get_control_board_progress_status(allocation),
            "board_status": board_status,
            "board_status_class": board_status_class,
            "status_text": status_text,
            "status_class": status_class,
            "pna_parts": pna_parts,
        })

    return render(request, "floor/bodyshopControlBoard.html", {
        "rows": rows,
        "search": search,
        "status_filter": status_filter,
        "insurance_filter": insurance_filter,
        "advisor_filter": advisor_filter,
        "surveyor_filter": surveyor_filter,
        "insurance_options": InsuranceCompany.objects.all().order_by("ins_co_name"),
        "advisor_options": Employee.objects.filter(
            is_active=True
        ).filter(
            Q(employee_type__iexact="Advisor")
            | Q(designation__iexact="Advisor")
        ).order_by("name"),
        "surveyor_options": Surveyor.objects.all().order_by("name"),
        "total_count": len(rows),
        "pna_count": pna_count,
        "work_completed_count": work_completed_count,
        "running_count": running_count,
        "breadcrumbs": [
            {
                "title": "WorkShop/Floor",
                "url": "",
                "icon": "fa fa-list",
            },
            {
                "title": "Bodyshop Control Board",
                "icon": "fa fa-table",
            },
        ],
    })


@never_cache
@login_required
def work_allocation_entry(request, job_id):
    from django.utils.dateparse import parse_date, parse_datetime

    job = get_object_or_404(
        JobCard,
        id=job_id
    )

    allocation, created = (
        WorkAllocation
        .objects
        .get_or_create(
            job=job
        )
    )
    progress_qs = allocation.progress.all().prefetch_related("photos")
    progress_map = {
        p.id: p
        for p in progress_qs
    }
    existing_reinspection_photo_count = job.reinspection_photos.count()
    existing_reinspection_photo_size = get_reinspection_photo_storage_size(job)

    if request.method == "POST":
        had_allocated_progress = any(
            progress.stage or progress.employee_id
            for progress in progress_qs
        )
        old_progress_state = {
            stage: {
                "start_time": progress.start_time,
                "finish_time": progress.finish_time,
                "employee_id": progress.employee_id,
                "has_data": progress_row_has_data(progress),
            }
            for stage, progress in progress_map.items()
        }
        uploaded_reinspection_images = request.FILES.getlist("reinspection_images")

        if uploaded_reinspection_images:
            total_photo_count = existing_reinspection_photo_count + len(uploaded_reinspection_images)

            if total_photo_count > REINSPECTION_MAX_PHOTOS_PER_JOBCARD:
                messages.error(
                    request,
                    "Re-inspection image limit exceeded. "
                    f"Maximum {REINSPECTION_MAX_PHOTOS_PER_JOBCARD} images are allowed per jobcard."
                )
                return redirect("work_allocation_entry", job_id=job.id)

            oversized_image = next(
                (
                    image for image in uploaded_reinspection_images
                    if image.size > REINSPECTION_MAX_IMAGE_SIZE_BYTES
                ),
                None
            )

            if oversized_image:
                messages.error(
                    request,
                    f"{oversized_image.name} is too large. "
                    f"Maximum {REINSPECTION_MAX_IMAGE_SIZE_MB} MB is allowed per image."
                )
                return redirect("work_allocation_entry", job_id=job.id)

            upload_total_size = sum(image.size for image in uploaded_reinspection_images)
            total_storage_size = existing_reinspection_photo_size + upload_total_size

            if total_storage_size > REINSPECTION_MAX_TOTAL_SIZE_BYTES:
                messages.error(
                    request,
                    "Re-inspection image storage limit exceeded. "
                    f"Maximum {REINSPECTION_MAX_TOTAL_SIZE_MB} MB is allowed per jobcard."
                )
                return redirect("work_allocation_entry", job_id=job.id)

        posted_work_completed = request.POST.get("mark_work_completed") == "1"
        posted_qc_done = request.POST.get("mark_qc_done") == "1"
        posted_reinspection_done = request.POST.get("reinspection_done") == "1"
        posted_part_entry_complete = request.POST.get("part_entry_complete") == "1"
        posted_reinspection_date = parse_workflow_datetime(
            request.POST.get("reinspection_date") or ""
        )
        posted_reinspection_done_by = request.POST.get(
            "reinspection_done_by",
            ""
        ).strip()
        posted_allotment_date = (
            parse_workflow_datetime(request.POST.get("allotment_date") or "")
            or allocation.allotment_date
        )
        validate_labels = set()
        if workflow_date_changed(allocation.allotment_date, posted_allotment_date):
            validate_labels.add("Work Allocation Date")
        if workflow_date_changed(job.reinspection_date, posted_reinspection_date):
            validate_labels.add("Re-Inspection Date")

        date_error = validate_workflow_dates([
            ("Gate In Date", job.gate_in_datetime),
            ("Claim Created Date", job.claim.created_at if job.claim else None),
            ("Jobcard Created Date", job.job_date or job.created_at),
            ("Claim Intimation Date", job.claim.intimation_date if job.claim else None),
            ("Survey Date", job.claim.survey_date if job.claim else None),
            ("Insurance Approval Date", job.claim.insurance_approval_date if job.claim else None),
            ("Work Allocation Date", posted_allotment_date),
            ("Re-Inspection Date", posted_reinspection_date),
            ("Liability Received Date", job.claim.liability_received_at if job.claim else None),
            ("Invoice Date", job.claim.invoice_datetime if job.claim else None),
            ("Delivery Date", job.claim.delivery_datetime if job.claim else None),
        ], validate_labels=validate_labels)
        if date_error:
            messages.error(request, date_error)
            return redirect("work_allocation_entry", job_id=job.id)

        future_error = validate_no_future_workflow_dates([
            ("Work Allocation Date", posted_allotment_date),
            ("Re-Inspection Date", posted_reinspection_date),
        ])
        if future_error:
            messages.error(request, future_error)
            return redirect("work_allocation_entry", job_id=job.id)

        if posted_work_completed and not (
            posted_qc_done
            and posted_reinspection_done
            and posted_part_entry_complete
        ):
            messages.error(
                request,
                "Tick QC Done, Re-Inspection and Part Entry before Work Completed."
            )
            return redirect("work_allocation_entry", job_id=job.id)

        if (
            posted_work_completed
            and job.additional_approval_required
            and (job.second_approval_status or "Pending") == "Pending"
        ):
            messages.error(
                request,
                "2nd Approval is pending. Advisor approval is required before Work Completed."
            )
            return redirect("work_allocation_entry", job_id=job.id)

        allocation.allotment_date = posted_allotment_date
        allocation.delivery_date = parse_date(
            request.POST.get("delivery_date") or ""
        )
        allocation.parts_slip_no = request.POST.get(
            "parts_slip_no",
            ""
        ).strip()
        allocation.remarks = request.POST.get(
            "remarks",
            ""
        ).strip()
        allocation.part_entry_complete = posted_part_entry_complete
        allocation.save()
        additional_approval_reasons = []

        progress_ids = request.POST.getlist("progress_id[]")
        progress_photo_keys = request.POST.getlist("progress_photo_key[]")
        stages = request.POST.getlist("stage[]")
        start_times = request.POST.getlist("start_time[]")
        finish_times = request.POST.getlist("finish_time[]")
        employee_ids = request.POST.getlist("employee[]")
        progress_remarks = request.POST.getlist("progress_remarks[]")
        clear_progress_photo_stages = set(
            request.POST.getlist("clear_progress_photo_stage[]")
        )
        clear_progress_photo_ids = set(
            request.POST.getlist("clear_progress_photo_id[]")
        )
        delete_progress_ids = {
            value
            for value in request.POST.getlist("delete_progress_id[]")
            if value.isdigit()
        }

        if delete_progress_ids:
            WorkProgress.objects.filter(
                allocation=allocation,
                id__in=delete_progress_ids,
            ).delete()
            progress_map = {
                key: value
                for key, value in progress_map.items()
                if str(key) not in delete_progress_ids
            }

        for index, start_time in enumerate(start_times):
            employee_id = (
                employee_ids[index]
                if index < len(employee_ids)
                else ""
            )

            if start_time and not employee_id:
                stage_key = stages[index] if index < len(stages) else ""
                stage_label = dict(WorkProgress.STAGES).get(
                    stage_key,
                    stage_key or "progress row"
                )
                messages.error(
                    request,
                    f"Select employee for {stage_label} before saving."
                )
                return redirect("work_allocation_entry", job_id=job.id)

        if posted_work_completed:
            unfinished_stages = []
            for index, start_time in enumerate(start_times):
                finish_time = (
                    finish_times[index]
                    if index < len(finish_times)
                    else ""
                )
                if start_time and not finish_time:
                    stage_key = (
                        stages[index]
                        if index < len(stages)
                        else ""
                    )
                    unfinished_stages.append(
                        dict(WorkProgress.STAGES).get(
                            stage_key,
                            stage_key or "progress row"
                        )
                    )

            if unfinished_stages:
                messages.error(
                    request,
                    "Finish started progress before Work Completed: "
                    + ", ".join(unfinished_stages)
                )
                return redirect("work_allocation_entry", job_id=job.id)

            posted_allocation_labour_ids = request.POST.getlist("allocation_labour_id[]")
            posted_labour_employee_ids = request.POST.getlist("labour_employee[]")
            missing_labour_employee_labels = []

            for index, labour_id in enumerate(posted_allocation_labour_ids):
                employee_id = (
                    posted_labour_employee_ids[index]
                    if index < len(posted_labour_employee_ids)
                    else ""
                )

                if employee_id:
                    continue

                labour = JobCardLabour.objects.filter(
                    id=labour_id,
                    job=job,
                ).first()
                missing_labour_employee_labels.append(
                    labour.job_code if labour else f"line {index + 1}"
                )

            if missing_labour_employee_labels:
                messages.error(
                    request,
                    "Select employee for labour line before Work Completed: "
                    + ", ".join(missing_labour_employee_labels)
                )
                return redirect("work_allocation_entry", job_id=job.id)

        for index, stage in enumerate(stages):
            progress_id = (
                progress_ids[index]
                if index < len(progress_ids)
                else ""
            )
            start_time = (
                start_times[index]
                if index < len(start_times)
                else ""
            )
            finish_time = (
                finish_times[index]
                if index < len(finish_times)
                else ""
            )
            employee_id = (
                employee_ids[index]
                if index < len(employee_ids)
                else ""
            )
            remarks = (
                progress_remarks[index].strip()
                if index < len(progress_remarks)
                else ""
            )
            has_uploaded_photos = bool(
                request.FILES.getlist(
                    progress_photo_input_name(
                        progress_photo_keys[index]
                        if index < len(progress_photo_keys)
                        else progress_id
                    )
                )
            )

            if not stage and not any([
                start_time,
                finish_time,
                employee_id,
                remarks,
                has_uploaded_photos,
            ]):
                continue

            if not stage:
                messages.error(
                    request,
                    "Select Progress Type before saving progress row."
                )
                return redirect("work_allocation_entry", job_id=job.id)

            progress = None
            if progress_id:
                progress = progress_map.get(int(progress_id)) if progress_id.isdigit() else None

                if progress is None:
                    messages.error(request, "Invalid progress row.")
                    return redirect("work_allocation_entry", job_id=job.id)

            if progress is None:
                progress = WorkProgress.objects.create(
                    allocation=allocation,
                    stage=stage
                )

            progress.stage = stage
            progress.start_time = parse_datetime(start_time) if start_time else None
            progress.finish_time = parse_datetime(finish_time) if finish_time else None
            progress.employee_id = employee_id or None
            progress.remarks = remarks
            progress.save()

            if (
                stage in clear_progress_photo_stages
                or str(progress.id) in clear_progress_photo_ids
            ):
                for photo in progress.photos.all():
                    if photo.image:
                        photo.image.delete(save=False)
                    photo.delete()

            for image in request.FILES.getlist(
                progress_photo_input_name(
                    progress_photo_keys[index]
                    if index < len(progress_photo_keys)
                    else progress_id
                )
            ):
                WorkProgressPhoto.objects.create(
                    progress=progress,
                    image=image
                )

            old_state = old_progress_state.get(progress.id, {})
            if old_state.get("has_data") and not progress_row_has_data(progress):
                notify_work_progress_change(progress, "cleared")
            elif not old_state.get("start_time") and progress.start_time:
                notify_work_progress_change(progress, "started")
            elif not old_state.get("finish_time") and progress.finish_time:
                notify_work_progress_change(progress, "finished")
            elif old_state.get("employee_id") != progress.employee_id and progress.employee_id:
                notify_work_progress_change(progress, "assigned")

            if old_state.get("employee_id") != progress.employee_id and progress.employee_id:
                notify_progress_employee_assigned(progress)

        sync_jobcard_main_status(job)

        has_allocated_progress = WorkProgress.objects.filter(
            allocation=allocation,
        ).filter(
            Q(stage__gt="")
            | Q(employee__isnull=False)
        ).exists()

        if not had_allocated_progress and has_allocated_progress:
            notify_floor_incharge_work_allocated(job)

        has_progress_started = WorkProgress.objects.filter(
            allocation=allocation,
            start_time__isnull=False,
        ).exists()
        has_any_progress_data = any(
            progress_row_has_data(row)
            for row in allocation.progress.all()
        )

        if not has_any_progress_data and job.claim:
            if int(job.claim.claim_stage or 0) in [
                ClaimStageCode.REPAIR_IN_PROGRESS,
                ClaimStageCode.WORK_COMPLETED,
                ClaimStageCode.RE_INSPECTION,
            ]:
                job.claim.claim_stage = ClaimStageCode.WORK_ALLOCATION
                job.claim.save(update_fields=["claim_stage"])

            job.qc_done = False
            job.reinspection_done = False
            job.reinspection_date = None
            job.reinspection_done_by = ""
            job.save(update_fields=[
                "qc_done",
                "reinspection_done",
                "reinspection_date",
                "reinspection_done_by",
            ])

            allocation.part_entry_complete = False
            allocation.save(update_fields=["part_entry_complete"])

        if (
            has_progress_started
            and job.claim
            and int(job.claim.claim_stage or 0) < ClaimStageCode.WORK_COMPLETED
        ):
            job.claim.claim_stage = ClaimStageCode.REPAIR_IN_PROGRESS
            job.claim.save(update_fields=["claim_stage"])

        allocation_part_ids = request.POST.getlist("allocation_part_id[]")
        decisions = request.POST.getlist("decision[]")
        pick_from_store = request.POST.getlist("pick_from_store[]")
        pick_dates = request.POST.getlist("pick_date[]")
        picker_names = request.POST.getlist("picker_name[]")
        ko_order_dates = request.POST.getlist("ko_order_date[]")
        ko_order_nos = request.POST.getlist("ko_order_no[]")
        etas = request.POST.getlist("eta[]")
        part_remarks = request.POST.getlist("part_remarks[]")

        for index, assessment_id in enumerate(allocation_part_ids):
            assessment = JobCardAssessmentPart.objects.filter(
                id=assessment_id,
                job=job,
            ).select_related("part").first()

            if not assessment:
                continue

            posted_decision = (
                decisions[index]
                if index < len(decisions)
                else assessment.decision
            )

            current_allocation_part = WorkAllocationPart.objects.filter(
                allocation=allocation,
                job_part=assessment.part,
            ).first()
            current_decision = (
                current_allocation_part.decision
                if current_allocation_part
                else assessment.decision
            )

            if current_decision == "KO" and posted_decision in ["New", "Repair"]:
                part_label = (
                    assessment.part.part_no
                    if assessment.part
                    else f"part line {index + 1}"
                )
                additional_approval_reasons.append(
                    f"KO part changed to {posted_decision}: {part_label}"
                )

            allocation_part, _ = WorkAllocationPart.objects.get_or_create(
                allocation=allocation,
                job_part=assessment.part,
                defaults={
                    "decision": assessment.decision,
                }
            )
            allocation_part.decision = posted_decision
            allocation_part.pick_from_store = (
                index < len(pick_from_store)
                and pick_from_store[index] == "Yes"
            )
            allocation_part.pick_date = parse_date(
                pick_dates[index]
            ) if index < len(pick_dates) and pick_dates[index] else None
            allocation_part.picker_name = (
                picker_names[index].strip()
                if index < len(picker_names)
                else ""
            )
            allocation_part.ko_order_date = parse_date(
                ko_order_dates[index]
            ) if index < len(ko_order_dates) and ko_order_dates[index] else None
            allocation_part.ko_order_no = (
                ko_order_nos[index].strip()
                if index < len(ko_order_nos)
                else ""
            )
            allocation_part.eta = parse_date(
                etas[index]
            ) if index < len(etas) and etas[index] else None
            allocation_part.remarks = (
                part_remarks[index].strip()
                if index < len(part_remarks)
                else ""
            )
            allocation_part.save()

        new_part_nos = request.POST.getlist("new_part_no[]")
        new_part_descriptions = request.POST.getlist("new_part_description[]")
        new_part_qtys = request.POST.getlist("new_part_qty[]")
        new_part_rates = request.POST.getlist("new_part_rate[]")
        new_part_decisions = request.POST.getlist("new_part_decision[]")
        new_part_pick_from_store = request.POST.getlist("new_part_pick_from_store[]")
        new_part_pick_dates = request.POST.getlist("new_part_pick_date[]")
        new_part_picker_names = request.POST.getlist("new_part_picker_name[]")
        new_part_ko_order_dates = request.POST.getlist("new_part_ko_order_date[]")
        new_part_ko_order_nos = request.POST.getlist("new_part_ko_order_no[]")
        new_part_etas = request.POST.getlist("new_part_eta[]")
        new_part_remarks = request.POST.getlist("new_part_remarks[]")
        new_part_photo_keys = request.POST.getlist("new_part_photo_key[]")
        has_new_part_lines = any(
            (part_no or "").strip()
            or (
                new_part_descriptions[index].strip()
                if index < len(new_part_descriptions)
                else ""
            )
            for index, part_no in enumerate(new_part_nos)
        )

        if has_new_part_lines:
            for index, part_no in enumerate(new_part_nos):
                description = (
                    new_part_descriptions[index].strip()
                    if index < len(new_part_descriptions)
                    else ""
                )

                if not (part_no or "").strip() and not description:
                    continue

                photo_key = (
                    new_part_photo_keys[index]
                    if index < len(new_part_photo_keys)
                    else str(index)
                )

                if not request.FILES.getlist(f"new_part_photo_{photo_key}"):
                    messages.error(
                        request,
                        "Upload photo(s) on each additional part line."
                    )
                    return redirect("work_allocation_entry", job_id=job.id)

        for index, part_no in enumerate(new_part_nos):
            part_no = part_no.strip()
            description = (
                new_part_descriptions[index].strip()
                if index < len(new_part_descriptions)
                else ""
            )

            if not part_no and not description:
                continue

            qty = int(
                Decimal(
                    new_part_qtys[index]
                    if index < len(new_part_qtys) and new_part_qtys[index]
                    else "1"
                )
            )
            rate = Decimal(
                new_part_rates[index]
                if index < len(new_part_rates) and new_part_rates[index]
                else "0"
            )
            decision = (
                new_part_decisions[index]
                if index < len(new_part_decisions) and new_part_decisions[index]
                else "New"
            )

            job_part = JobCardPart.objects.create(
                job=job,
                part_no=part_no or "Additional",
                description=description or part_no or "Additional part",
                qty=qty,
                rate=rate,
            )
            JobCardAssessmentPart.objects.create(
                job=job,
                part=job_part,
                decision=decision,
                revised_amount=job_part.amount,
            )
            allocation_part = WorkAllocationPart.objects.create(
                allocation=allocation,
                job_part=job_part,
                decision=decision,
                is_additional=True,
                advisor_approval_status="Pending",
                pick_from_store=(
                    index < len(new_part_pick_from_store)
                    and new_part_pick_from_store[index] == "Yes"
                ),
                pick_date=parse_date(
                    new_part_pick_dates[index]
                ) if index < len(new_part_pick_dates) and new_part_pick_dates[index] else None,
                picker_name=(
                    new_part_picker_names[index].strip()
                    if index < len(new_part_picker_names)
                    else ""
                ),
                ko_order_date=parse_date(
                    new_part_ko_order_dates[index]
                ) if index < len(new_part_ko_order_dates) and new_part_ko_order_dates[index] else None,
                ko_order_no=(
                    new_part_ko_order_nos[index].strip()
                    if index < len(new_part_ko_order_nos)
                    else ""
                ),
                eta=parse_date(
                    new_part_etas[index]
                ) if index < len(new_part_etas) and new_part_etas[index] else None,
                remarks=(
                    new_part_remarks[index].strip()
                    if index < len(new_part_remarks)
                    else ""
                ),
            )
            photo_key = (
                new_part_photo_keys[index]
                if index < len(new_part_photo_keys)
                else str(index)
            )
            for image in request.FILES.getlist(f"new_part_photo_{photo_key}"):
                JobCardAdditionalApprovalPhoto.objects.create(
                    job=job,
                    work_allocation_part=allocation_part,
                    image=image,
                )
            additional_approval_reasons.append(
                f"Additional part added: {allocation_part.job_part.part_no}"
            )

        allocation_labour_ids = request.POST.getlist("allocation_labour_id[]")
        labour_decisions = request.POST.getlist("labour_decision[]")
        labour_revised_amounts = request.POST.getlist("labour_revised_amount[]")
        labour_employee_ids = request.POST.getlist("labour_employee[]")
        labour_remarks = request.POST.getlist("labour_remarks[]")

        for index, labour_id in enumerate(allocation_labour_ids):
            labour = JobCardLabour.objects.filter(
                id=labour_id,
                job=job,
            ).first()

            if not labour:
                continue

            allocation_labour, _ = WorkAllocationLabour.objects.get_or_create(
                allocation=allocation,
                job_labour=labour,
                defaults={
                    "revised_amount": labour.amount,
                }
            )
            allocation_labour.decision = (
                labour_decisions[index]
                if index < len(labour_decisions)
                else "Approved"
            )
            allocation_labour.revised_amount = Decimal(
                labour_revised_amounts[index]
                if index < len(labour_revised_amounts)
                and labour_revised_amounts[index]
                else "0"
            )
            employee_id = (
                labour_employee_ids[index]
                if index < len(labour_employee_ids)
                else ""
            )
            allocation_labour.employee_id = employee_id or None
            allocation_labour.remarks = (
                labour_remarks[index].strip()
                if index < len(labour_remarks)
                else ""
            )
            allocation_labour.save()

        new_labour_codes = request.POST.getlist("new_labour_code[]")
        new_labour_descriptions = request.POST.getlist("new_labour_description[]")
        new_labour_amounts = request.POST.getlist("new_labour_amount[]")
        new_labour_hours = request.POST.getlist("new_labour_hrs[]")
        new_labour_rates = request.POST.getlist("new_labour_rate[]")
        new_labour_decisions = request.POST.getlist("new_labour_decision[]")
        new_labour_employees = request.POST.getlist("new_labour_employee[]")
        new_labour_remarks = request.POST.getlist("new_labour_remarks[]")
        new_labour_photo_keys = request.POST.getlist("new_labour_photo_key[]")
        has_new_labour_lines = any(
            (labour_code or "").strip()
            or (
                new_labour_descriptions[index].strip()
                if index < len(new_labour_descriptions)
                else ""
            )
            for index, labour_code in enumerate(new_labour_codes)
        )

        if has_new_labour_lines:
            for index, labour_code in enumerate(new_labour_codes):
                description = (
                    new_labour_descriptions[index].strip()
                    if index < len(new_labour_descriptions)
                    else ""
                )

                if not (labour_code or "").strip() and not description:
                    continue

                photo_key = (
                    new_labour_photo_keys[index]
                    if index < len(new_labour_photo_keys)
                    else str(index)
                )

                if not request.FILES.getlist(f"new_labour_photo_{photo_key}"):
                    messages.error(
                        request,
                        "Upload photo(s) on each additional labour line."
                    )
                    return redirect("work_allocation_entry", job_id=job.id)

        for index, labour_code in enumerate(new_labour_codes):
            labour_code = labour_code.strip()
            description = (
                new_labour_descriptions[index].strip()
                if index < len(new_labour_descriptions)
                else ""
            )

            if not labour_code and not description:
                continue

            if index < len(new_labour_amounts) and new_labour_amounts[index]:
                labour_hrs = Decimal("1")
                labour_rate = Decimal(new_labour_amounts[index])
            else:
                labour_hrs = Decimal(
                    new_labour_hours[index]
                    if index < len(new_labour_hours) and new_labour_hours[index]
                    else "1"
                )
                labour_rate = Decimal(
                    new_labour_rates[index]
                    if index < len(new_labour_rates) and new_labour_rates[index]
                    else "0"
                )

            if labour_hrs >= Decimal("1000"):
                messages.error(
                    request,
                    "Labour hours must be less than 1000."
                )
                return redirect("work_allocation_entry", job_id=job.id)
            decision = (
                new_labour_decisions[index]
                if index < len(new_labour_decisions) and new_labour_decisions[index]
                else "Approved"
            )
            employee_id = (
                new_labour_employees[index]
                if index < len(new_labour_employees)
                else ""
            )

            job_labour = JobCardLabour.objects.create(
                job=job,
                job_code=labour_code or "Additional",
                description=description or labour_code or "Additional labour",
                labour_hrs=labour_hrs,
                rate=labour_rate,
            )
            JobCardAssessmentLabour.objects.create(
                job=job,
                labour=job_labour,
                decision=decision,
                revised_amount=job_labour.amount,
            )
            allocation_labour = WorkAllocationLabour.objects.create(
                allocation=allocation,
                job_labour=job_labour,
                decision=decision,
                is_additional=True,
                advisor_approval_status="Pending",
                revised_amount=job_labour.amount,
                employee_id=employee_id or None,
                remarks=(
                    new_labour_remarks[index].strip()
                    if index < len(new_labour_remarks)
                    else ""
                ),
            )
            photo_key = (
                new_labour_photo_keys[index]
                if index < len(new_labour_photo_keys)
                else str(index)
            )
            for image in request.FILES.getlist(f"new_labour_photo_{photo_key}"):
                JobCardAdditionalApprovalPhoto.objects.create(
                    job=job,
                    work_allocation_labour=allocation_labour,
                    image=image,
                )
            additional_approval_reasons.append(
                f"Additional labour added: {job_labour.job_code}"
            )

        if additional_approval_reasons:
            existing_reason = (job.additional_approval_reason or "").strip()
            reason_text = "\n".join(additional_approval_reasons)
            job.additional_approval_required = True
            job.second_approval_status = "Pending"
            job.repair_status = "Open"
            job.additional_approval_reason = (
                f"{existing_reason}\n{reason_text}".strip()
                if existing_reason
                else reason_text
            )
            job.save(update_fields=[
                "additional_approval_required",
                "second_approval_status",
                "repair_status",
                "additional_approval_reason",
            ])
            posted_work_completed = False
            posted_qc_done = False
            posted_reinspection_done = False
            posted_part_entry_complete = False
            allocation.part_entry_complete = False
            allocation.save(update_fields=["part_entry_complete"])

            if job.claim:
                job.claim.claim_stage = ClaimStageCode.REPAIR_IN_PROGRESS
                job.claim.save(update_fields=["claim_stage"])

            notify_jobcard_advisor(
                job,
                "2nd Approval Required",
                f"Jobcard {job.job_no} needs Advisor approval for additional work.",
            )

        if posted_work_completed:
            job.repair_status = "Completed"
            job.save(update_fields=["repair_status"])

            if job.claim:
                job.claim.claim_stage = ClaimStageCode.WORK_COMPLETED
                job.claim.save(update_fields=["claim_stage"])

            notify_jobcard_advisor(
                job,
                "Jobcard Work Completed",
                f"Jobcard {job.job_no} repair work completed",
            )
        elif (
            job.claim
            and int(job.claim.claim_stage or 0) == ClaimStageCode.WORK_COMPLETED
        ):
            job.claim.claim_stage = (
                ClaimStageCode.REPAIR_IN_PROGRESS
                if has_progress_started
                else ClaimStageCode.WORK_ALLOCATION
            )
            job.claim.save(update_fields=["claim_stage"])
            sync_jobcard_main_status(job)

        job.qc_done = posted_qc_done
        job.save(update_fields=["qc_done"])

        job.reinspection_done = posted_reinspection_done
        job.reinspection_date = posted_reinspection_date
        job.reinspection_done_by = posted_reinspection_done_by
        job.save(update_fields=[
            "reinspection_done",
            "reinspection_date",
            "reinspection_done_by",
        ])

        for image in uploaded_reinspection_images:
            JobCardReInspectionPhoto.objects.create(
                job=job,
                image=image
            )

        if job.reinspection_done and job.claim:
            job.claim.claim_stage = ClaimStageCode.LIABILITY
            job.claim.save(update_fields=["claim_stage"])

            notify_jobcard_advisor(
                job,
                "Jobcard Re-Inspection Done",
                f"Jobcard {job.job_no} re-inspection completed",
            )

        messages.success(request, "Work allocation saved successfully")
        return redirect("work_allocation_entry", job_id=job.id)

    progress_rows = []

    for p in progress_qs:
        if not progress_row_has_data(p):
            continue

        progress_rows.append({
            "id": p.id,
            "stage": p.stage,
            "label": p.get_stage_display(),
            "start_time": p.start_time if p else None,
            "finish_time": p.finish_time if p else None,
            "employee_id": p.employee_id if p else None,
            "remarks": p.remarks if p else "",
            "progress_id": p.id if p else "",
            "photo_count": p.photos.count() if p else 0,
            "photo_input_name": progress_photo_input_name(p.id),
        })
    assessed_parts = list(JobCardAssessmentPart.objects.filter(
        job=job,
        decision__in=["New", "Repair", "KO"]
    ).select_related("part"))

    allocation_parts_by_part_id = {
        part.job_part_id: part
        for part in allocation.parts.all()
    }

    for assessment in assessed_parts:
        saved_part = allocation_parts_by_part_id.get(assessment.part_id)

        if saved_part:
            assessment.decision = saved_part.decision
            assessment.pick_from_store = saved_part.pick_from_store
            assessment.pick_date = saved_part.pick_date
            assessment.picker_name = saved_part.picker_name
            assessment.ko_order_date = saved_part.ko_order_date
            assessment.ko_order_no = saved_part.ko_order_no
            assessment.eta = saved_part.eta
            assessment.remarks = saved_part.remarks
            assessment.is_additional = saved_part.is_additional
            assessment.advisor_approval_status = saved_part.advisor_approval_status
            assessment.additional_approval_photos = list(
                saved_part.additional_approval_photos.all()
            )
        else:
            assessment.pick_from_store = False
            assessment.pick_date = None
            assessment.picker_name = ""
            assessment.ko_order_date = None
            assessment.ko_order_no = ""
            assessment.eta = None
            assessment.remarks = ""
            assessment.is_additional = False
            assessment.advisor_approval_status = ""
            assessment.additional_approval_photos = []

    assessed_labours = list(job.labours.filter(
        jobcardassessmentlabour__decision="Approved"
    ))
    allocation_labours_by_labour_id = {
        labour.job_labour_id: labour
        for labour in allocation.labours.all()
    }

    for labour in assessed_labours:
        saved_labour = allocation_labours_by_labour_id.get(labour.id)
        assessment = JobCardAssessmentLabour.objects.filter(
            job=job,
            labour=labour,
        ).first()

        labour.decision = (
            saved_labour.decision
            if saved_labour
            else "Approved"
        )
        labour.revised_amount = (
            saved_labour.revised_amount
            if saved_labour
            else (
                assessment.revised_amount
                if assessment
                else labour.amount
            )
        )
        labour.employee_id = (
            saved_labour.employee_id
            if saved_labour
            else None
        )
        labour.remarks = (
            saved_labour.remarks
            if saved_labour
            else ""
        )
        labour.is_additional = saved_labour.is_additional if saved_labour else False
        labour.advisor_approval_status = (
            saved_labour.advisor_approval_status
            if saved_labour
            else ""
        )
        labour.additional_approval_photos = (
            list(saved_labour.additional_approval_photos.all())
            if saved_labour
            else []
        )
    technicians = Employee.objects.filter(
        designation__in=['Technician', 'Denter', 'Painter']
    )
    return render(
        request,

        "floor/workAllocationEntry.html",

        {

            "job": job,
            "technicians": technicians,
            "allocation": allocation,
            "can_print_work_report": (
                (
                    job.repair_status == "Completed"
                    or (
                        job.claim
                        and int(job.claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
                    )
                )
                and job.qc_done
                and job.reinspection_done
            ),
            "is_work_completed": (
                job.repair_status == "Completed"
                or (
                    job.claim
                    and int(job.claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
                )
            ),
            "progress_rows": progress_rows,
            "rows": rows,
            "allocation_parts": assessed_parts,
            "existing_reinspection_photo_count": existing_reinspection_photo_count,
            "existing_reinspection_photo_size_mb": round(
                existing_reinspection_photo_size / (1024 * 1024),
                2
            ),
            "reinspection_max_photos": REINSPECTION_MAX_PHOTOS_PER_JOBCARD,
            "reinspection_max_image_size_mb": REINSPECTION_MAX_IMAGE_SIZE_MB,
            "reinspection_max_total_size_mb": REINSPECTION_MAX_TOTAL_SIZE_MB,

            "allocation_labours": assessed_labours,

            "stages":
                WorkProgress.STAGES,

        }
    )


@never_cache
@login_required
def work_completion_report(request, job_id):
    job = get_object_or_404(
        JobCard.objects.select_related(
            "claim",
            "claim__vehicle",
            "claim__vehicle__customer",
            "claim__vehicle__model",
            "claim__vehicle__variant",
            "advisor",
            "allocation",
        ),
        id=job_id
    )
    allocation = getattr(job, "allocation", None)

    if not allocation:
        messages.error(request, "Work allocation is not available for this jobcard.")
        return redirect("work_allocation_entry", job_id=job.id)

    can_print = (
        (
            job.repair_status == "Completed"
            or (
                job.claim
                and int(job.claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED
            )
        )
        and job.qc_done
        and job.reinspection_done
    )

    if not can_print:
        messages.error(
            request,
            "Complete Work Completed, QC, and Re-Inspection before printing the report."
        )
        return redirect("work_allocation_entry", job_id=job.id)

    progress_rows = (
        allocation.progress
        .select_related("employee")
        .filter(finish_time__isnull=False)
        .order_by("finish_time", "id")
    )
    parts = allocation.parts.select_related("job_part").order_by("id")
    labours = allocation.labours.select_related("job_labour", "employee").order_by("id")

    return render(request, "floor/workCompletionReport.html", {
        "job": job,
        "claim": job.claim,
        "allocation": allocation,
        "progress_rows": progress_rows,
        "parts": parts,
        "labours": labours,
        "work_status": get_work_progress_status(allocation),
    })


@login_required
def check_work_allocation_employee(request):
    employee_id = request.GET.get("employee_id")
    allocation_id = request.GET.get("allocation_id")

    if not employee_id:
        return JsonResponse({"assigned": False})

    progress = (
        WorkProgress.objects
        .select_related(
            "allocation",
            "allocation__job",
            "allocation__job__claim",
            "allocation__job__claim__vehicle",
            "employee"
        )
        .filter(
            employee_id=employee_id,
            start_time__isnull=False,
            finish_time__isnull=True,
        )
    )

    if allocation_id:
        progress = progress.exclude(allocation_id=allocation_id)

    progress = progress.first()

    if not progress:
        return JsonResponse({"assigned": False})

    return JsonResponse({
        "assigned": True,
        "employee": progress.employee.name if progress.employee else "",
        "job_no": progress.allocation.job.job_no if progress.allocation and progress.allocation.job else "",
        "registration_no": progress.allocation.job.claim.vehicle.registration_no if (
            progress.allocation
            and progress.allocation.job
            and progress.allocation.job.claim
            and progress.allocation.job.claim.vehicle
        ) else "",
        "stage": progress.get_stage_display(),
    })


@never_cache
@login_required
def reinspection_photo_view(request, job_id):
    job = get_object_or_404(
        JobCard.objects.select_related(
            "claim",
            "claim__vehicle",
        ),
        id=job_id
    )

    if request.method == "POST":
        photo_ids = request.POST.getlist("photo_ids")
        photos_to_delete = job.reinspection_photos.filter(id__in=photo_ids)

        if not photos_to_delete.exists():
            messages.error(request, "Select at least one image to delete.")
            return redirect("reinspection_photo_view", job_id=job.id)

        deleted_count = 0

        for photo in photos_to_delete:
            if photo.image:
                photo.image.delete(save=False)

            photo.delete()
            deleted_count += 1

        messages.success(request, f"{deleted_count} re-inspection image(s) deleted successfully.")

        return redirect("reinspection_photo_view", job_id=job.id)

    photos = job.reinspection_photos.order_by("uploaded_at")

    return render(request, "floor/reinspectionPhotos.html", {
        "job": job,
        "photos": photos,
    })


@login_required
def download_reinspection_photos(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)
    photo_ids = request.POST.getlist("photo_ids")
    photos = job.reinspection_photos.filter(id__in=photo_ids).order_by("uploaded_at")

    if not photos.exists():
        messages.error(request, "Select at least one image to download.")
        return redirect("reinspection_photo_view", job_id=job.id)

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for index, photo in enumerate(photos, start=1):
            if not photo.image:
                continue

            filename = os.path.basename(photo.image.name)
            _, ext = os.path.splitext(filename)
            zip_name = f"reinspection_{index}{ext or '.jpg'}"

            photo.image.open("rb")
            zip_file.writestr(zip_name, photo.image.read())
            photo.image.close()

    buffer.seek(0)
    claim_no = job.claim.claim_no if job.claim else job.job_no
    safe_claim_no = "".join(
        char if char.isalnum() or char in ["-", "_"] else "_"
        for char in claim_no
    )
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="reinspection_{safe_claim_no}.zip"'
    )

    return response


@login_required
def delete_reinspection_photo(request, job_id, photo_id):
    if request.method != "POST":
        return redirect("reinspection_photo_view", job_id=job_id)

    job = get_object_or_404(JobCard, id=job_id)
    photo = get_object_or_404(JobCardReInspectionPhoto, id=photo_id, job=job)

    if photo.image:
        photo.image.delete(save=False)

    photo.delete()
    messages.success(request, "Re-inspection image deleted successfully.")

    return redirect("reinspection_photo_view", job_id=job.id)


@never_cache
@login_required
def work_progress_photo_view(request, progress_id):
    progress = get_object_or_404(
        WorkProgress.objects.select_related(
            "allocation",
            "allocation__job",
            "allocation__job__claim",
            "allocation__job__claim__vehicle",
        ),
        id=progress_id
    )
    job = progress.allocation.job

    if request.method == "POST":
        photo_ids = request.POST.getlist("photo_ids")
        photos_to_delete = progress.photos.filter(id__in=photo_ids)

        if not photos_to_delete.exists():
            messages.error(request, "Select at least one image to delete.")
            return redirect("work_progress_photo_view", progress_id=progress.id)

        deleted_count = 0
        for photo in photos_to_delete:
            if photo.image:
                photo.image.delete(save=False)
            photo.delete()
            deleted_count += 1

        messages.success(request, f"{deleted_count} progress image(s) deleted successfully.")
        return redirect("work_progress_photo_view", progress_id=progress.id)

    return render(request, "floor/workProgressPhotos.html", {
        "job": job,
        "progress": progress,
        "photos": progress.photos.order_by("uploaded_at"),
    })


@never_cache
@login_required
def my_work_list(request):
    logged_emp = Employee.objects.filter(user=request.user).first()

    if not is_repair_resource(logged_emp):
        messages.error(request, "Only Technician, Denter or Painter can access My Work.")
        return redirect("dashboard")

    today = timezone.localdate()
    month_start = today.replace(day=1)
    from_date = parse_date(request.GET.get("from_date") or "") or month_start
    to_date = parse_date(request.GET.get("to_date") or "") or today
    status_filter = request.GET.get("status") or "new"

    base_progress = my_work_base_queryset(logged_emp, from_date, to_date)
    rows = [
        my_work_row_payload(progress)
        for progress in apply_my_work_status_filter(base_progress, status_filter).order_by(
            "start_time",
            "allocation__job__job_no",
            "id",
        )
    ]

    counts = {
        "new": base_progress.filter(start_time__isnull=True).count(),
        "wip": base_progress.filter(start_time__isnull=False, finish_time__isnull=True).count(),
        "completed": base_progress.filter(finish_time__isnull=False).count(),
    }

    return render(request, "floor/myWorkList.html", {
        "logged_emp": logged_emp,
        "rows": rows,
        "counts": counts,
        "status_filter": status_filter,
        "filter_from_date": from_date.strftime("%Y-%m-%d"),
        "filter_to_date": to_date.strftime("%Y-%m-%d"),
        "breadcrumbs": [
            {
                "title": "WorkShop / Floor",
                "url": "",
                "icon": "fa fa-list"
            },
            {
                "title": "My Work",
                "icon": "fa fa-tools"
            }
        ]
    })


@require_POST
@never_cache
@login_required
def my_work_action(request, progress_id):
    logged_emp = Employee.objects.filter(user=request.user).first()

    if not is_repair_resource(logged_emp):
        messages.error(request, "Only Technician, Denter or Painter can update My Work.")
        return redirect("dashboard")

    progress = get_object_or_404(
        WorkProgress.objects.select_related("allocation", "allocation__job"),
        id=progress_id,
        employee=logged_emp,
    )
    action = request.POST.get("action") or ""

    if action == "start":
        if start_work_progress(progress):
            notify_work_progress_change(progress, "started")
        messages.success(request, "Work progress started.")
    elif action == "finish":
        if finish_work_progress(progress):
            notify_work_progress_change(progress, "finished")
        messages.success(request, "Work progress finished.")

    save_work_progress_uploaded_photos(request, progress)

    if request.FILES.getlist("progress_photos") and action not in ["start", "finish"]:
        messages.success(request, "Progress photo(s) uploaded.")

    return redirect(request.POST.get("next") or "my_work_list")


@never_cache
@login_required
def vehicle_condition_photo_view(request, job_id):
    job = get_object_or_404(
        JobCard.objects.select_related(
            "claim",
            "claim__vehicle",
        ),
        id=job_id
    )

    if request.method == "POST":
        photo_ids = request.POST.getlist("photo_ids")
        photos_to_delete = job.vehicle_condition_photos.filter(id__in=photo_ids)

        if not photos_to_delete.exists():
            messages.error(request, "Select at least one image to delete.")
            return redirect("vehicle_condition_photo_view", job_id=job.id)

        deleted_count = 0

        for photo in photos_to_delete:
            if photo.image:
                photo.image.delete(save=False)

            photo.delete()
            deleted_count += 1

        messages.success(request, f"{deleted_count} vehicle condition image(s) deleted successfully.")

        return redirect("vehicle_condition_photo_view", job_id=job.id)

    photos = job.vehicle_condition_photos.order_by("id")

    return render(request, "jobcard/vehicleConditionPhotos.html", {
        "job": job,
        "photos": photos,
    })


@login_required
def download_vehicle_condition_photos(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)
    photo_ids = request.POST.getlist("photo_ids")
    photos = job.vehicle_condition_photos.filter(id__in=photo_ids).order_by("id")

    if not photos.exists():
        messages.error(request, "Select at least one image to download.")
        return redirect("vehicle_condition_photo_view", job_id=job.id)

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for index, photo in enumerate(photos, start=1):
            if not photo.image:
                continue

            filename = os.path.basename(photo.image.name)
            _, ext = os.path.splitext(filename)
            safe_caption = "".join(
                char if char.isalnum() or char in ["-", "_"] else "_"
                for char in photo.caption
            )
            zip_name = f"{index:02d}_{safe_caption}{ext or '.jpg'}"

            photo.image.open("rb")
            zip_file.writestr(zip_name, photo.image.read())
            photo.image.close()

    buffer.seek(0)
    claim_no = job.claim.claim_no if job.claim else job.job_no
    safe_claim_no = "".join(
        char if char.isalnum() or char in ["-", "_"] else "_"
        for char in claim_no
    )
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="vehicle_condition_{safe_claim_no}.zip"'
    )

    return response


@login_required
def check_open_claim(request):
    vehicle_id = request.GET.get("vehicle_id")

    claim = Claim.objects.filter(
        vehicle_id=vehicle_id
    ).exclude(
        claim_stage=ClaimStageCode.CLOSED
    ).first()

    if claim:
        return JsonResponse({
            "exists": True,
            "claim_no": claim.claim_no,
            "claim_id": claim.id,
        })

    return JsonResponse({
        "exists": False
    })


@login_required
def unread_announcements(request):
    read_ids = AnnouncementRead.objects.filter(
        user=request.user
    ).values_list(
        "announcement_id",
        flat=True
    )

    notices = Announcement.objects.filter(
        is_active=True
    ).exclude(
        id__in=read_ids
    ).order_by("-created_at")[:3]

    data = []

    for n in notices:
        data.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notice_type,
        })

    return JsonResponse(data, safe=False)


@login_required
def mark_announcement_read(request, pk):
    announcement = get_object_or_404(
        Announcement,
        pk=pk
    )

    AnnouncementRead.objects.get_or_create(
        announcement=announcement,
        user=request.user
    )

    return JsonResponse({
        "status": "success"
    })
from django.http import HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.conf import settings
from playwright.sync_api import sync_playwright
import time


@login_required
def jobcard_print_pdf(request, pk, token):

    if token != settings.PDF_SECRET_TOKEN:
        return HttpResponseForbidden("Invalid token")

    job = get_object_or_404(JobCard, pk=pk)

    preview_url = (
        settings.SITE_URL.rstrip("/")
        + reverse(
            "jobcard_print_preview",
            args=[job.id, settings.PDF_SECRET_TOKEN]
        )
        + f"?v={int(time.time())}"
    )

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        page.goto(
            preview_url,
            wait_until="load",
            timeout=60000
        )

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={
                "top": "8mm",
                "right": "8mm",
                "bottom": "8mm",
                "left": "8mm",
            }
        )

        browser.close()

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="jobcard_{job.job_no}.pdf"'
    )

    return response
