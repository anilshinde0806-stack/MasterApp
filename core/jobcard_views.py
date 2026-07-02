"""Jobcard related views.

This module keeps jobcard screens, APIs, print views, and WhatsApp jobcard
helpers out of core.views. Shared workflow helpers still live in core.views
until the next cleanup pass.
"""

from .views import *  # noqa: F401,F403


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


def jobcard_driver_options_for_branch(branch=None, user=None):
    drivers = Employee.objects.filter(is_active=True).filter(
        Q(employee_type__icontains="Driver")
        | Q(designation__icontains="Driver")
        | Q(department__icontains="Driver")
    )
    if branch and not is_admin_user(user, Employee.objects.filter(user=user).first() if user else None):
        drivers = drivers.filter(branch=branch)
    return drivers.order_by("name")


def move_claim_to_intimation_after_jobcard(claim):
    if not claim or not claim.employee_id:
        return

    if int(claim.claim_stage or 0) < ClaimStageCode.INTIMATION:
        claim.claim_stage = ClaimStageCode.INTIMATION
        claim.save(update_fields=["claim_stage"])


@never_cache
@login_required
def jobList_page(request):
    job_form = JobCardForm(initial={
        'job_no': generate_job_no_for_user(request.user)}, user=request.user)
    claim_form = ClaimForm(user=request.user)

    context = {
        "form": job_form,
        "claimform": claim_form,
    }

    return render(request, "jobcard/jobList.html", context)

@protect_entry_page_response
@never_cache
@login_required
def jobcard_create(request, claim_id=None):
    from django.utils import timezone
    from django.utils.dateparse import parse_date

    claim = None
    job = None
    if claim_id:
        claim = get_object_or_404(Claim, id=claim_id)

    gate_entry = latest_pending_gate_entry_for_claim(claim)
    job_branch = branch_for_claim(claim) if claim else branch_for_user(request.user)
    job_no = generate_job_no_for_claim(claim) if claim else generate_job_no_for_user(request.user)
    initial_jobcard_type = claim.claim_type if claim and claim.claim_type in dict(JobCard.JOBCARD_TYPE_CHOICES) else "Paid"

    form = JobCardForm(initial={
        "job_no": job_no,
        "jobcard_type": initial_jobcard_type,
        "claim": claim.id if claim else None,
        "advisor": claim.employee if claim else None,
        "gate_in_datetime": gate_entry.gate_in_datetime if gate_entry else None,
        "km": gate_entry.current_km if gate_entry else None,
    }, user=request.user)
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

        form = JobCardForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():

            obj = form.save(commit=False)
            direct_gate_entry = None
            obj.repair_instructions = "\n".join(
                item.strip()
                for item in request.POST.getlist("repair_instruction[]")
                if item.strip()
            )

            if claim:
                obj.claim = claim
                obj.advisor = claim.employee
                obj.vehicle = claim.vehicle
                obj.branch = branch_for_claim(claim)
            else:
                direct_vehicle_id = request.POST.get("direct_vehicle") or ""
                direct_vehicle = Vehicle.objects.filter(pk=direct_vehicle_id).first()
                if not direct_vehicle:
                    messages.error(request, "Select Vehicle before creating direct Jobcard.")
                    return redirect("jobCreate")

                direct_branch = branch_for_user(request.user)
                direct_gate_entry = latest_pending_gate_entry_for_vehicle(
                    direct_vehicle,
                    branch=None if is_admin_user(request.user, logged_emp) else direct_branch,
                )
                if not direct_gate_entry:
                    messages.error(request, "First Gate In Entry then continue.")
                    return redirect("jobCreate")

                direct_claim_type = (
                    obj.jobcard_type
                    if obj.jobcard_type in dict(Claim.CLAIM_TYPE_CHOICES)
                    else "Paid"
                )
                obj.vehicle = direct_vehicle
                obj.branch = direct_branch
                if direct_claim_type in ["Cashless", "NonCashless"]:
                    claim = Claim.objects.create(
                        claim_no=generate_claim_no_for_user(request.user),
                        vehicle=direct_vehicle,
                        branch=obj.branch,
                        employee=obj.advisor,
                        claim_type=direct_claim_type,
                        claim_stage=(
                            ClaimStageCode.INTIMATION
                            if obj.advisor_id
                            else ClaimStageCode.CLAIM_CREATED
                        ),
                        status="Open",
                    )
                    obj.claim = claim
                else:
                    obj.claim = None

            gate_entry = GateInEntry.objects.filter(
                pk=request.POST.get("gate_entry_id") or 0,
                status="Pending",
            ).first() or direct_gate_entry or latest_pending_gate_entry_for_claim(obj.claim)

            if gate_entry:
                obj.gate_in_datetime = obj.gate_in_datetime or gate_entry.gate_in_datetime
                obj.km = obj.km or gate_entry.current_km
                obj.vehicle_inward_by = obj.vehicle_inward_by or "Gate Security"

            if not obj.job_no:
                obj.job_no = (
                    generate_job_no_for_claim(obj.claim)
                    if obj.claim_id
                    else generate_job_no_for_user(request.user)
                )

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

            if gate_entry:
                gate_entry.jobcard = obj
                gate_entry.status = "Converted"
                gate_entry.save(update_fields=["jobcard", "status", "updated_at"])

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
            labour_paint_panel_type = request.POST.getlist("labour_paint_panel_type[]")

            labour_total = Decimal("0")

            for i in range(len(job_code)):
                panel_type = labour_paint_panel_type[i] if i < len(labour_paint_panel_type) else ""
                if panel_type not in ["New", "Repair"]:
                    panel_type = ""
                amount = Decimal(hrs[i]) * Decimal(lab_rate[i])

                JobCardLabour.objects.create(
                    job=obj,
                    job_code=job_code[i],
                    description=lab_desc[i],
                    labour_hrs=hrs[i],
                    rate=lab_rate[i],
                    amount=amount,
                    paint_panel_type=panel_type
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
            move_claim_to_intimation_after_jobcard(claim)

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
        "gate_entry": gate_entry,
        "job_created_date_value": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        **get_inventory_context(None),
        "can_change_advisor": can_change_advisor,
        "can_edit_jobcard_entries": can_edit_jobcard_entries,
        "is_cng_vehicle": is_cng_vehicle,
        "logged_emp": logged_emp,
        "driver_options": jobcard_driver_options_for_branch(job_branch, request.user),
        "vehicle_inward_by_value": "",
        "vehicle_form": VehicleForm(),
        "direct_jobcard": claim is None,
        "direct_vehicle": None,
        "display_vehicle": None,
        "vehicle_photo_slots": get_vehicle_condition_photo_slots(None),
        "claim_document_slots": get_claim_document_slots(claim),
        "repair_instruction_rows": [""],
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
@protect_entry_page_response
@login_required
def jobcard_edit(request, pk):
    from django.utils.dateparse import parse_date

    job = get_object_or_404(JobCard, pk=pk)
    claim = job.claim
    job_branch = branch_for_claim(claim) if claim else (job.branch or branch_for_user(request.user))
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
            instance=job,
            user=request.user,
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
                obj.repair_instructions = "\n".join(
                    item.strip()
                    for item in request.POST.getlist("repair_instruction[]")
                    if item.strip()
                )
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
                labour_paint_panel_type = request.POST.getlist("labour_paint_panel_type[]")

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

                    panel_type = labour_paint_panel_type[i] if i < len(labour_paint_panel_type) else ""
                    if panel_type not in ["New", "Repair"]:
                        panel_type = ""

                    labour.job_code = job_code[i]
                    labour.description = lab_desc[i]
                    labour.labour_hrs = h
                    labour.rate = r
                    labour.amount = amount
                    labour.paint_panel_type = panel_type
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
        form = JobCardForm(instance=job, user=request.user)

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
        "driver_options": jobcard_driver_options_for_branch(job_branch, request.user),
        "vehicle_inward_by_value": job.vehicle_inward_by or "",
        "vehicle_form": VehicleForm(),
        "direct_jobcard": claim is None,
        "direct_vehicle": job.vehicle,
        "display_vehicle": claim.vehicle if claim and claim.vehicle_id else job.vehicle,
        "insurance_companies": insurance_companies,
        "is_cng_vehicle": is_cng_vehicle,
        "parts": job.parts.all(),
        "labours": job.labours.all(),
        "job_progress_rows": job_progress_rows,
        "repair_instruction_rows": [
            line for line in (job.repair_instructions or "").splitlines() if line.strip()
        ] or [""],
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
        "vehicle",
        "vehicle__model",
        "vehicle__customer",
        "claim__vehicle",
        "claim__vehicle__model",
        "claim__vehicle__customer"
    ).prefetch_related(
        "allocation__progress",
        "allocation__parts",
    )
    if not is_admin_user(request.user, logged_emp):
        if logged_emp and logged_emp.branch_id:
            jobs = jobs.filter(Q(claim__branch=logged_emp.branch) | Q(branch=logged_emp.branch))
        else:
            jobs = jobs.none()

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
    if (
        not is_admin_user(request.user, logged_emp)
        and logged_emp
        and logged_emp.employee_type.upper() == "ADVISOR"
    ):
        jobs = jobs.filter(advisor=logged_emp)
    data = []

    for job in jobs:
        allocation = getattr(job, "allocation", None)
        work_progress_status = get_work_progress_status(allocation)
        vehicle = job.claim.vehicle if job.claim_id and job.claim and job.claim.vehicle_id else job.vehicle

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
            "claim__vehicle__registration_no": vehicle.registration_no if vehicle else "",
            "claim__vehicle__model__name": vehicle.model.name if vehicle and vehicle.model else "",
            "claim__vehicle__customer__name": vehicle.customer.name if vehicle and vehicle.customer else "",
            "advisor__name": job.advisor.name if job.advisor else "",
            "vehicle_inward_type": job.vehicle_inward_type,
            "gate_in_datetime": job.gate_in_datetime,
            "repair_status": job.repair_status,
            "work_progress_status": work_progress_status,
            "parts_not_available_status": get_parts_not_available_status(job),
            "parts_total": job.parts_total,
            "labour_total": job.labour_total,
            "grand_total": job.grand_total,
            "created_at": job.created_at,
        })

    return JsonResponse(data, safe=False)




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
            "paint_panel_type": l.paint_panel_type or "",
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
            panel_type = str(l.get("paint_panel_type") or "").strip()
            if panel_type not in ["New", "Repair"]:
                panel_type = ""

            if l.get("is_new"):
                labour = JobCardLabour.objects.create(
                    job=job,
                    job_code=l.get("job_code", ""),
                    description=l.get("description", ""),
                    labour_hrs=Decimal("1"),
                    rate=Decimal(l.get("amount") or "0"),
                    amount=Decimal(l.get("amount") or "0"),
                    paint_panel_type=panel_type,
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
                if labour.paint_panel_type != panel_type:
                    labour.paint_panel_type = panel_type
                    labour.save(update_fields=["paint_panel_type"])

            JobCardAssessmentLabour.objects.update_or_create(
                job=job,
                labour=labour,
                defaults={
                    "decision": l.get("decision"),
                    "deduction_percent": Decimal(l.get("deduction_percent") or "0"),
                    "revised_amount": Decimal(l.get("revised_amount") or "0"),
                }
            )

        if (
            job.claim
            and int(job.claim.claim_stage or 0) < ClaimStageCode.WORK_ALLOCATION
        ):
            job.claim.claim_stage = ClaimStageCode.WORK_ALLOCATION
            job.claim.save(update_fields=["claim_stage"])
            notify_floor_incharge_work_allocation_pending(job.claim)

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
    new_paint_panel_count = sum(
        1 for item in assessed_labours
        if item.labour.paint_panel_type == "New"
    )
    repair_paint_panel_count = sum(
        1 for item in assessed_labours
        if item.labour.paint_panel_type == "Repair"
    )
    total_paint_panel_count = new_paint_panel_count + repair_paint_panel_count

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
        "new_paint_panel_count": new_paint_panel_count,
        "repair_paint_panel_count": repair_paint_panel_count,
        "total_paint_panel_count": total_paint_panel_count,
        "grand_total": parts_total + labour_total,
        "grand_revised_total": parts_revised_total + labour_revised_total,
    })




@never_cache
def jobcard_print_preview(request, pk, token=None):
    # allow if token is correct OR user is logged in
    if token != settings.PDF_SECRET_TOKEN and not request.user.is_authenticated:
        return HttpResponseForbidden("Not allowed")

    job = get_object_or_404(
        JobCard.objects.select_related(
            "claim",
            "claim__vehicle",
            "claim__vehicle__customer",
            "claim__vehicle__model",
            "claim__vehicle__variant",
            "vehicle",
            "vehicle__customer",
            "vehicle__model",
            "vehicle__variant",
            "advisor",
        ),
        pk=pk,
    )
    variant_name = ""
    claim = job.claim
    vehicle = claim.vehicle if claim and claim.vehicle_id else job.vehicle
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    if (
            vehicle
            and vehicle.variant
    ):
        variant_name = vehicle.variant.name or ""

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
        "claim": claim,
        "vehicle": vehicle,
        "customer": customer,
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




@login_required
def whatsapp_cloud_test(request):
    mobile = request.GET.get("mobile") or request.POST.get("mobile")
    template = request.GET.get("template") or request.POST.get("template") or "hello_world"
    language = request.GET.get("language") or request.POST.get("language") or "en_US"

    if not mobile:
        return JsonResponse(
            {
                "success": False,
                "message": "Pass mobile number, example: /whatsapp-cloud-test/?mobile=91XXXXXXXXXX",
            },
            status=400,
        )

    result = send_whatsapp_template_message(mobile, template, language)
    return JsonResponse(result, status=200 if result["success"] else 400)




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




def jobcard_print_pdf(request, pk, token):

    if token != settings.PDF_SECRET_TOKEN:
        return HttpResponseForbidden("Invalid token")

    job = get_object_or_404(JobCard, pk=pk)

    preview_path = (
        reverse(
            "jobcard_print_preview",
            args=[job.id, settings.PDF_SECRET_TOKEN]
        )
        + f"?v={int(time.time())}"
    )
    preview_url = request.build_absolute_uri(preview_path)

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        response = page.goto(
            preview_url,
            wait_until="networkidle",
            timeout=60000
        )
        if not response or response.status >= 400:
            browser.close()
            status = response.status if response else "no response"
            return HttpResponse(
                f"Unable to render Jobcard PDF preview. HTTP status: {status}. URL: {preview_url}",
                status=500,
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
import subprocess
from pathlib import Path
from django.http import FileResponse, Http404
from django.conf import settings

def print_jobcard_jasper(request, jobcard_id):
    base_dir = Path(settings.BASE_DIR)

    report_file = base_dir / "reports" / "jasper" / "jobcard.jasper"
    output_dir = base_dir / "reports" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_name = f"jobcard_{jobcard_id}"
    output_pdf = output_dir / f"{output_name}.pdf"

    jasperstarter = base_dir / "tools" / "jasperstarter" / "bin" / "jasperstarter.exe"
    jdbc_driver = base_dir / "tools" / "jasperstarter" / "jdbc" / "postgresql-42.7.11.jar"
    cmd = [
        str(jasperstarter),
        "process",
        str(report_file),
        "-o",
        str(output_dir / output_name),
        "-f",
        "pdf",
        "-t",
        "postgres",
        "--jdbc-dir",
        str(jdbc_driver.parent),
        "-H",
        "localhost",
        "-n",
        "bodyshop_demo",
        "-u",
        "postgres",
        "-p",
        "Admin@123",
        "-P",
        f"JOBCARD_ID={jobcard_id}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(result.stderr or result.stdout)

    if not output_pdf.exists():
        raise Http404("PDF not generated")

    return FileResponse(
        open(output_pdf, "rb"),
        content_type="application/pdf",
        filename=f"jobcard_{jobcard_id}.pdf",
    )