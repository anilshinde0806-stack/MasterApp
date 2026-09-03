"""Claim related views.

This module keeps claim screens and claim APIs out of core.views. Shared
workflow helpers still live in core.views until the next cleanup pass.
"""
from requests import get

from .views import *  # noqa: F401,F403
from .forms import advisor_queryset_for_user
from apps.claims.repositories.claim_queries import ClaimQueryService
from apps.claims.services.claim_helpers import desktop_claim_list_payload
from apps.claims.services.claim_upsert_service import ClaimUpsertService


def protect_entry_page_response(view_func):
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "same-origin"
        response["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        return response

    return wrapper


@login_required
def advisor_workload_api(request):
    advisor_id = request.GET.get("advisor_id") or ""
    advisors = advisor_queryset_for_user(request.user)

    if advisor_id:
        advisors = advisors.filter(id=advisor_id)

    advisor_ids = list(advisors.values_list("id", flat=True))
    open_claims = Claim.objects.filter(
        employee_id__in=advisor_ids,
    ).exclude(
        claim_stage=ClaimStageCode.CLOSED
    )
    jobcards = {
        job.claim_id: job
        for job in JobCard.objects.filter(
            claim_id__in=open_claims.values_list("id", flat=True)
        )
    }

    summary_rows = []
    total_open = 0
    total_today = 0
    total_inward_counts = {
        "Walk-in": 0,
        "Pickup": 0,
        "Breakdown": 0,
        "Jobcard Pending": 0,
    }

    today = timezone.localdate()
    for advisor in advisors:
        advisor_claims = [claim for claim in open_claims if claim.employee_id == advisor.id]
        inward_counts = {
            "Walk-in": 0,
            "Pickup": 0,
            "Breakdown": 0,
            "Jobcard Pending": 0,
        }

        for claim in advisor_claims:
            job = jobcards.get(claim.id)
            inward_type = job.vehicle_inward_type if job else "Jobcard Pending"
            inward_counts[inward_type] = inward_counts.get(inward_type, 0) + 1
            total_inward_counts[inward_type] = total_inward_counts.get(inward_type, 0) + 1

        today_count = sum(
            1
            for claim in advisor_claims
            if workflow_date_value(claim.created_at).date() == today
        )
        open_count = len(advisor_claims)
        total_open += open_count
        total_today += today_count

        summary_rows.append({
            "advisor": advisor.name,
            "open_count": open_count,
            "today_assigned_count": today_count,
            "inward_counts": inward_counts,
        })

    return JsonResponse({
        "status": "success",
        "advisor": "All Advisors",
        "open_count": total_open,
        "today_assigned_count": total_today,
        "inward_counts": total_inward_counts,
        "summary_rows": summary_rows,
    })




@protect_entry_page_response
@never_cache
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
        request.user.is_superuser
        or request.user.is_staff
        or request.user.groups.filter(name__iexact="Admin").exists()
        or request.user.groups.filter(name__iexact="Manager").exists()
        or (
            logged_emp
            and logged_emp.employee_type.upper() != "ADVISOR"
        )
    )

    # =====================================
    # FORM
    # =====================================

    current_stage = 1
    pending_days = 0

    claim_form = ClaimForm(initial={
        'claim_no': generate_claim_no_for_user(request.user),
        'employee': logged_emp.id if logged_emp else None
    }, user=request.user)

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
        "prefill_registration_no": (request.GET.get("registration_no") or "").strip().upper(),
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
        "claim_no": generate_claim_no_for_user(request.user)
    }, user=request.user)

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
            instance=claim,
            user=request.user
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
            if not obj.branch_id:
                obj.branch = branch_for_user(request.user)
            if not obj.claim_no:
                obj.claim_no = next_claim_no(branch_for_claim(obj))

            obj.save()

            return JsonResponse({
                "status": "success",
                "id": obj.id
            })

        return JsonResponse({
            "status": "error",
            "errors": form.errors
        })

    form = ClaimForm(instance=claim, user=request.user)

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
    claims = branch_scoped_queryset_for_user(
        Claim.objects.select_related(
            'vehicle',
            'customer',
            'insurance_company',
            'surveyor'
        ),
        request.user,
    )
    data = claims.values(
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
    claims = ClaimQueryService.filtered(
        request.user,
        branch_id=request.GET.get("branch"),
        from_date=request.GET.get("from_date"),
        to_date=request.GET.get("to_date"),
        status=request.GET.get("claim_status", "open"),
        advisor_blank=request.GET.get("advisor_blank") == "1",
        advisor_assigned=request.GET.get("advisor_assigned") == "1",
    )
    return JsonResponse(
        [desktop_claim_list_payload(claim) for claim in claims],
        safe=False,
    )




@never_cache
@protect_entry_page_response
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

        old_advisor_id = claim.employee_id if claim and claim.employee_id else None
        old_stage = claim.claim_stage if claim else None
        old_status = claim.status if claim else None

        form = ClaimForm(
            request.POST,
            request.FILES,
            instance=claim,
            user=request.user
        )

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
            # SHARED CREATE / UPDATE POLICY
            # =====================================

            is_new = obj.pk is None

            # Shared create/update rules used by both desktop and Flutter.
            ClaimUpsertService.prepare(
                obj,
                user=request.user,
                previous_stage=old_stage,
            )

            obj.save()
            jobcard = JobCard.objects.filter(claim=obj).first()
            save_claim_documents(request, obj)
            if jobcard and obj.self_survey:
                save_vehicle_condition_photos(request, jobcard)
            if claim_created_date:
                obj.created_at = claim_created_date
                obj.save(update_fields=["created_at"])

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
                whatsapp_result = send_advisor_assigned_whatsapp(obj)
                if not get("success"):
                    messages.warning(
                        request,
                        "Claim saved, but WhatsApp advisor message was not sent: "
                        + str(get("response", ""))[:180]
                    )
                else:
                    messages.success(request, "WhatsApp advisor message sent to customer.")

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
    start_intimation = request.GET.get("start_intimation")
    if claim and start_intimation == "1" and int(claim.claim_stage or 0) == ClaimStageCode.ADVISOR_ASSIGNED:
        jobcard = JobCard.objects.filter(claim=claim).first()
        if not jobcard or not jobcard.labours.exists():
            messages.error(request, "Add at least one Labour line item before sending to Claim Intimation.")
            return redirect("jobcard_edit", pk=jobcard.id) if jobcard else redirect("claim_edit", pk=claim.id)
        claim.claim_stage = ClaimStageCode.ESTIMATE_CREATED
        claim.save(update_fields=["claim_stage"])
        messages.info(request, "Claim Intimation details are ready for entry.")
        return redirect("claim_edit", pk=claim.id)

    move_stage = request.GET.get("move_stage")

    if claim and move_stage:

        current = int(
            claim.claim_stage or
            ClaimStageCode.CLAIM_CREATED
        )
        old_stage_before_move = current

        if move_stage == "next":

            if current == ClaimStageCode.ADVISOR_ASSIGNED:
                messages.error(
                    request,
                    "Use Send to Claim Intimation from the Job Card before moving to the next claim stage."
                )
                return redirect("claim_edit", pk=claim.id)

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
    can_change_advisor = (
        request.user.is_superuser
        or request.user.is_staff
        or request.user.groups.filter(name__iexact="Admin").exists()
        or request.user.groups.filter(name__iexact="Manager").exists()
        or role != "ADVISOR"
    )

    form = ClaimForm(instance=claim, user=request.user)
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

    form.fields['employee'].queryset = advisor_queryset_for_user(request.user)
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


