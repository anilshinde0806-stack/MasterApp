import math
import os
import zipfile
from io import BytesIO

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.sites import requests
from django.db import IntegrityError
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.template.loader import get_template
from django.views.decorators.cache import never_cache
from psycopg import rows
from xhtml2pdf import pisa

from config import settings
from .forms import VehicleForm, InsuranceCompanyForm, CustomerForm, SurveyorForm, EmployeeForm, JobCardForm
from .models import InsuranceCompany, VehicleModel, Customer, ColumnPreference, Surveyor, JobCardPart, \
    JobCardLabour, JobCardAssessmentPart, JobCardAssessmentLabour, JobCardTyreInventory, \
    CommunicationLog, UserNotification, ClaimStageCode, WorkProgress, WorkAllocation, AnnouncementRead, Announcement, \
    PartOrder, PartOrderHeader, WorkAllocationPart, WorkAllocationLabour, JobCardReInspectionPhoto


REINSPECTION_MAX_PHOTOS_PER_JOBCARD = getattr(settings, "REINSPECTION_MAX_PHOTOS_PER_JOBCARD", 25)
REINSPECTION_MAX_IMAGE_SIZE_MB = getattr(settings, "REINSPECTION_MAX_IMAGE_SIZE_MB", 8)
REINSPECTION_MAX_TOTAL_SIZE_MB = getattr(settings, "REINSPECTION_MAX_TOTAL_SIZE_MB", 50)
REINSPECTION_MAX_IMAGE_SIZE_BYTES = REINSPECTION_MAX_IMAGE_SIZE_MB * 1024 * 1024
REINSPECTION_MAX_TOTAL_SIZE_BYTES = REINSPECTION_MAX_TOTAL_SIZE_MB * 1024 * 1024


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


# Create your views here.
@login_required
@login_required
def dashboard(request):
    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

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

    # MANAGER REPORT DEFAULTS
    total_claims = 0
    pending_claims = 0
    work_allocation_pending = 0
    repair_in_progress = 0
    total_estimate_value = 0

    stage_counts = []
    advisor_counts = []
    recent_jobs = []

    if show_manager_dashboard:
        total_claims = Claim.objects.count()

        pending_claims = Claim.objects.exclude(
            claim_stage=ClaimStageCode.CLOSED
        ).count()

        work_allocation_pending = Claim.objects.filter(
            claim_stage=ClaimStageCode.WORK_ALLOCATION
        ).count()

        repair_in_progress = Claim.objects.filter(
            claim_stage=ClaimStageCode.REPAIR_IN_PROGRESS
        ).count()

        stage_counts = (
            Claim.objects
            .values("claim_stage")
            .annotate(total=Count("id"))
            .order_by("claim_stage")
        )

        advisor_counts = (
            Claim.objects
            .values("employee__name")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )

        recent_jobs = (
            JobCard.objects
            .select_related(
                "claim",
                "claim__vehicle",
                "advisor"
            )
            .order_by("-id")[:10]
        )

        total_estimate_value = (
                JobCard.objects
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
        "work_allocation_pending": work_allocation_pending,
        "repair_in_progress": repair_in_progress,
        "stage_counts": stage_counts,
        "advisor_counts": advisor_counts,
        "recent_jobs": recent_jobs,
        "total_estimate_value": total_estimate_value,
    })


def register_view(request):
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


def insurance_data(request):
    data = list(InsuranceCompany.objects.values())
    return JsonResponse({'data': data})


def insurance_get(request, pk):
    obj = get_object_or_404(InsuranceCompany, pk=pk)
    return JsonResponse({
        'id': obj.id,
        'ins_co_name': obj.ins_co_name,
        'city': obj.city,
        'mobile_no': obj.mobile_no,
    })


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


def insurance_edit(request, pk):
    obj = get_object_or_404(InsuranceCompany, pk=pk)
    form = InsuranceCompanyForm(request.POST or None, instance=obj)

    if form.is_valid():
        form.save()
        return redirect('insurance')

    return render(request, 'insurance/edit.html', {'form': form})


def vehicle_list(request):
    return render(request, 'master/vehicle_list.html')


from .models import VehicleVariant


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


from django.views.decorators.csrf import csrf_exempt
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


def check_registration(request):
    reg = request.GET.get('registration_no')

    exists = Vehicle.objects.filter(
        registration_no__iexact=reg
    ).exists()

    return JsonResponse({
        'exists': exists
    })


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


def check_customer(request):
    name = request.GET.get("name", "").strip()
    mobile = request.GET.get("mobile", "").strip()

    exists = Customer.objects.filter(
        name__iexact=name,
        mobile_no=mobile
    ).exists()

    return JsonResponse({"exists": exists})


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


def customer_data(request):
    data = list(Customer.objects.values())
    return JsonResponse({'data': data})


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


def surveyor_page(request):
    form = SurveyorForm()
    return render(request, "master/surveyor.html", {"form": form})


def surveyor_data(request):
    data = list(Surveyor.objects.values())
    return JsonResponse({"data": data})


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


def surveyor_get(request, id):
    data = Surveyor.objects.filter(id=id).values().first()
    return JsonResponse(data)


def check_surveyor_mobile(request):
    mobile = request.GET.get("mobile")

    exists = Surveyor.objects.filter(mobile_no=mobile).exists()

    return JsonResponse({"exists": exists})


def employee_page(request):
    form = EmployeeForm()
    return render(request, "master/employee.html", {"form": form})


def employee_data(request):
    data = list(Employee.objects.values())
    return JsonResponse({"data": data})


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
        "claims": claims,
        "breadcrumbs": [

            {
                "title": "Transaction",
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
                "title": "Transaction",
                "icon": "fa fa-list"
            },
            {
                "title": "Claim List",
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
        }
    )


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


@csrf_exempt
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

    # =====================================
    # POST
    # =====================================

    if request.method == "POST":

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
            jobcard = JobCard.objects.filter(claim=obj).first()

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

            logged_emp = Employee.objects.filter(
                user=request.user
            ).first()

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

            # =====================================
            # SAVE
            # =====================================

            is_new = obj.pk is None

            obj.save()
            claim_created_date = parse_date(
                request.POST.get("claim_created_date") or ""
            )
            if claim_created_date:
                obj.created_at = timezone.make_aware(
                    datetime.combine(claim_created_date, time.min),
                    timezone.get_current_timezone()
                )
                obj.save(update_fields=["created_at"])

            if claim and claim.employee:
                old_advisor_id = claim.employee_id

            obj.save()

            new_advisor_id = obj.employee_id
            new_stage = obj.claim_stage
            new_status = obj.status

            if jobcard:
                uploaded_reinspection_images = request.FILES.getlist("reinspection_images")
                has_reinspection_post = (
                    "reinspection_done" in request.POST
                    or "reinspection_date" in request.POST
                    or "reinspection_done_by" in request.POST
                    or bool(uploaded_reinspection_images)
                )

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

                if has_reinspection_post:
                    jobcard.reinspection_done = request.POST.get("reinspection_done") == "1"
                    jobcard.reinspection_date = parse_date(
                        request.POST.get("reinspection_date") or ""
                    )
                    jobcard.reinspection_done_by = request.POST.get(
                        "reinspection_done_by",
                        ""
                    ).strip()
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

                if has_reinspection_post and jobcard.reinspection_done:
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

            current -= 1

        current = max(1, min(current, ClaimStageCode.CLOSED))

        claim.claim_stage = current
        claim.save()
        jobcard = JobCard.objects.filter(claim=claim).first()

        if jobcard:
            sync_jobcard_main_status(jobcard)

        messages.success(
            request,
            f"Stage changed to {claim.get_claim_stage_display()}"
        )

        return redirect(
            "claim_edit",
            pk=claim.id
        )
    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    role = (
        logged_emp.employee_type.upper()
        if logged_emp else ""
    )

    can_change_advisor = role != "ADVISOR"

    form = ClaimForm(instance=claim)
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
        timezone.localdate(claim.created_at).strftime("%Y-%m-%d")
        if claim and claim.created_at
        else timezone.localdate().strftime("%Y-%m-%d")
    )
    is_jobcard_closed = bool(
        jobcard
        and sync_jobcard_main_status(jobcard) == "Closed"
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
            "existing_reinspection_photo_count": existing_reinspection_photo_count,
            "existing_reinspection_photo_size_mb": round(
                existing_reinspection_photo_size / (1024 * 1024),
                2
            ),
            "reinspection_max_photos": REINSPECTION_MAX_PHOTOS_PER_JOBCARD,
            "reinspection_max_image_size_mb": REINSPECTION_MAX_IMAGE_SIZE_MB,
            "reinspection_max_total_size_mb": REINSPECTION_MAX_TOTAL_SIZE_MB,
            "stage_steps": [
                (ClaimStageCode.CLAIM_CREATED, "Claim Created"),
                (ClaimStageCode.ADVISOR_ASSIGNED, "Advisor Assigned"),
                (ClaimStageCode.ESTIMATE_CREATED, "Job Estimation"),
                (ClaimStageCode.INTIMATION, "Claim Intimation"),
                (ClaimStageCode.SURVEY, "Survey"),
                (ClaimStageCode.INSURANCE_APPROVAL, "Approval"),
                (ClaimStageCode.WORK_ALLOCATION, "Work Allocation"),
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
                    "title": "Transaction",
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

        form = JobCardForm(request.POST)

        if form.is_valid():

            obj = form.save(commit=False)

            if claim:
                obj.claim = claim
                obj.advisor = claim.employee

            if not obj.job_no:
                obj.job_no = generate_job_no()

            obj.save()
            job_created_date = parse_date(
                request.POST.get("job_created_date") or ""
            )

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
        "job_created_date_value": timezone.localdate().strftime("%Y-%m-%d"),
        **get_inventory_context(None),
        "can_change_advisor": can_change_advisor,
        "can_edit_jobcard_entries": can_edit_jobcard_entries,
        "is_cng_vehicle": is_cng_vehicle,
        "logged_emp": logged_emp,
        "fuel_percent": JobCardInventory.fuel_percent if JobCardInventory else 0,
        "cng_percent": JobCardInventory.cng_percent if JobCardInventory else 0,
        # ✅ BREADCRUMB
        "breadcrumbs": [

            {
                "title": "Transaction",
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
    is_jobcard_locked = job.repair_status == "Closed" and not can_reopen_jobcard
    can_edit_jobcard_entries = can_edit_jobcard_entries and not is_jobcard_locked

    if request.method == "POST":
        if is_jobcard_locked:
            messages.error(
                request,
                "Closed jobcard cannot be updated. Only Admin or Manager can re-open it."
            )
            return redirect("jobcard_edit", pk=job.id)

        form = JobCardForm(
            request.POST,
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

                job_created_date = parse_date(
                    request.POST.get("job_created_date") or ""
                )

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
                #claim.claim_stage = ClaimStageCode.ESTIMATE_CREATED
                #claim.save()
                if request.POST.get("send_whatsapp") == "on":
                    send_jobcard_whatsapp(obj)
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
        "job_created_date_value": job.job_date.strftime("%Y-%m-%d") if job.job_date else "",
        "can_change_advisor": can_change_advisor,
        "can_edit_jobcard_entries": can_edit_jobcard_entries,
        "can_reopen_jobcard": can_reopen_jobcard,
        "is_jobcard_locked": is_jobcard_locked,
        "logged_emp": logged_emp,
        "insurance_companies": insurance_companies,
        "is_cng_vehicle": is_cng_vehicle,
        "parts": job.parts.all(),
        "labours": job.labours.all(),
        "job_progress_rows": job_progress_rows,
        "can_close_jobcard": can_close_current_jobcard,
        "close_ready_status": close_ready_status,
        "PDF_SECRET_TOKEN": settings.PDF_SECRET_TOKEN,
        **get_inventory_context(job),

        # ✅ BREADCRUMB
        "breadcrumbs": [

            {
                "title": "Transaction",
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


@never_cache
@login_required
def jobcard_list_api(request):
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

    repair_status = request.GET.get("repair_status", "Open").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if repair_status:
        jobs = jobs.filter(repair_status=repair_status)

    if date_from:
        jobs = jobs.filter(job_date__date__gte=date_from)

    if date_to:
        jobs = jobs.filter(job_date__date__lte=date_to)

    data = []

    for job in jobs:
        allocation = getattr(job, "allocation", None)

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
            "work_progress_status": get_work_progress_status(allocation),
            "parts_not_available_status": get_parts_not_available_status(allocation),
            "parts_total": job.parts_total,
            "labour_total": job.labour_total,
            "grand_total": job.grand_total,
            "created_at": job.created_at,
        })

    return JsonResponse(data, safe=False)


from .models import CompanySetup
from .forms import CompanySetupForm


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


def upload_itemdata_excel(request):
    if request.method == "POST":
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
        return redirect("upload_itemdata_excel")

    else:
        form = ItemExcelUploadForm()

    return render(request, "master/partmaster.html", {
        "form": form
    })


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
        "job_created_date_value": job.job_date.strftime("%Y-%m-%d") if job.job_date else "",
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
        "labours": labours
    })


@require_POST
@login_required
@never_cache
def save_jobcard_assessment(request, job_id):
    job = get_object_or_404(JobCard, id=job_id)

    data = json.loads(request.body.decode("utf-8"))

    parts = data.get("parts", [])
    labours = data.get("labours", [])

    with transaction.atomic():

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
    notifications = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by("-created_at")[:5]

    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "url": n.url,
        }
        for n in notifications
    ]

    return JsonResponse(data, safe=False)


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


@never_cache
@login_required
def work_allocation_list(request):
    logged_emp = Employee.objects.filter(
        user=request.user
    ).first()

    if not logged_emp or logged_emp.employee_type != "Floor Supervisor":
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
                "title": "Transaction",
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
    if created:

        for stage_key, stage_label in WorkProgress.STAGES:
            WorkProgress.objects.create(
                allocation=allocation,
                stage=stage_key
            )
    progress_map = {
        p.stage: p
        for p in allocation.progress.all()
    }
    existing_reinspection_photo_count = job.reinspection_photos.count()
    existing_reinspection_photo_size = get_reinspection_photo_storage_size(job)

    if request.method == "POST":
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

        allocation.allotment_date = (
            parse_date(request.POST.get("allotment_date") or "")
            or allocation.allotment_date
        )
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
        allocation.part_entry_complete = request.POST.get("part_entry_complete") == "1"
        allocation.save()

        stages = request.POST.getlist("stage[]")
        start_times = request.POST.getlist("start_time[]")
        finish_times = request.POST.getlist("finish_time[]")
        employee_ids = request.POST.getlist("employee[]")
        progress_remarks = request.POST.getlist("progress_remarks[]")

        for index, start_time in enumerate(start_times):
            employee_id = (
                employee_ids[index]
                if index < len(employee_ids)
                else ""
            )

            if start_time and not employee_id:
                stage_key = (
                    stages[index]
                    if index < len(stages)
                    else ""
                )
                stage_label = dict(WorkProgress.STAGES).get(
                    stage_key,
                    stage_key or "progress row"
                )
                messages.error(
                    request,
                    f"Select employee for {stage_label} before saving."
                )
                return redirect("work_allocation_entry", job_id=job.id)

        for index, stage in enumerate(stages):
            progress = progress_map.get(stage)

            if progress is None:
                progress = WorkProgress.objects.create(
                    allocation=allocation,
                    stage=stage
                )

            progress.start_time = parse_datetime(
                start_times[index]
            ) if index < len(start_times) and start_times[index] else None
            progress.finish_time = parse_datetime(
                finish_times[index]
            ) if index < len(finish_times) and finish_times[index] else None
            employee_id = (
                employee_ids[index]
                if index < len(employee_ids)
                else ""
            )
            progress.employee_id = employee_id or None
            progress.remarks = (
                progress_remarks[index].strip()
                if index < len(progress_remarks)
                else ""
            )
            progress.save()

        sync_jobcard_main_status(job)

        has_progress_started = WorkProgress.objects.filter(
            allocation=allocation,
            start_time__isnull=False,
        ).exists()

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

            allocation_part, _ = WorkAllocationPart.objects.get_or_create(
                allocation=allocation,
                job_part=assessment.part,
                defaults={
                    "decision": assessment.decision,
                }
            )
            allocation_part.decision = (
                decisions[index]
                if index < len(decisions)
                else assessment.decision
            )
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

        if request.POST.get("mark_work_completed") == "1":
            job.repair_status = "Completed"
            job.save(update_fields=["repair_status"])

            if job.claim:
                job.claim.claim_stage = ClaimStageCode.WORK_COMPLETED
                job.claim.save(update_fields=["claim_stage"])
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

        if request.POST.get("mark_qc_done") == "1":
            job.qc_done = True
            job.save(update_fields=["qc_done"])

        job.reinspection_done = request.POST.get("reinspection_done") == "1"
        job.reinspection_date = parse_date(
            request.POST.get("reinspection_date") or ""
        )
        job.reinspection_done_by = request.POST.get(
            "reinspection_done_by",
            ""
        ).strip()
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

        messages.success(request, "Work allocation saved successfully")
        return redirect("work_allocation_entry", job_id=job.id)

    progress_rows = []

    for stage_key, stage_label in WorkProgress.STAGES:
        p = progress_map.get(stage_key)

        progress_rows.append({
            "stage": stage_key,
            "label": stage_label,
            "start_time": p.start_time if p else None,
            "finish_time": p.finish_time if p else None,
            "employee_id": p.employee_id if p else None,
            "remarks": p.remarks if p else "",
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
        else:
            assessment.pick_from_store = False
            assessment.pick_date = None
            assessment.picker_name = ""
            assessment.ko_order_date = None
            assessment.ko_order_no = ""
            assessment.eta = None
            assessment.remarks = ""

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

    progress_rows = allocation.progress.select_related("employee").order_by("id")
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
