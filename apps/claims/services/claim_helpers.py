from core.models import Claim, ClaimStageCode, JobCard, WorkProgress


def mobile_claim_payload(claim):
    vehicle = claim.vehicle if claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    stage_lookup = dict(Claim.CLAIM_STAGES)
    jobcard = JobCard.objects.filter(claim=claim).order_by("-id").first()
    allocation = getattr(jobcard, "allocation", None) if jobcard else None
    raw_repair_progress_started = (
        WorkProgress.objects.filter(
            allocation=allocation,
            start_time__isnull=False,
        ).exists()
        if allocation
        else False
    )
    repair_progress_started = bool(
        raw_repair_progress_started
        and int(claim.claim_stage or 0) >= ClaimStageCode.REPAIR_IN_PROGRESS
    )
    work_completed = bool(
        jobcard and jobcard.repair_status in ["Completed", "Closed"]
    )

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
        "repair_progress_conflict": bool(
            raw_repair_progress_started and not repair_progress_started
        ),
        "work_completed": work_completed,
        "registration_no": vehicle.registration_no if vehicle else "",
        "customer": customer.name if customer else "",
        "customer_name": customer.name if customer else "",
        "mobile_no": customer.mobile_no if customer and customer.mobile_no else "",
        "customer_mobile": customer.mobile_no if customer and customer.mobile_no else "",
        "whatsapp_no": (
            (customer.whatsapp_no or customer.mobile_no or "")
            if customer
            else ""
        ),
        "variant": vehicle.variant.name
        if vehicle and vehicle.variant_id
        else "",
        "advisor": claim.employee_id or "",
        "advisor_name": claim.employee.name if claim.employee_id else "",
        "insurance_company": claim.insurance_company_id or "",
        "insurance_company_name": (
            claim.insurance_company.ins_co_name
            if claim.insurance_company_id
            else ""
        ),
        "policy_no": claim.policy_no or "",
        "ic_claim_no": claim.ic_claim_no or "",
        "claim_type": claim.claim_type or "",
        "accident_date": claim.accident_date.isoformat()
        if claim.accident_date
        else "",
        "intimation_date": claim.intimation_date.isoformat()
        if claim.intimation_date
        else "",
        "survey_date": claim.survey_date.isoformat()
        if claim.survey_date
        else "",
        "surveyor": claim.surveyor_id or "",
        "survey_status": claim.survey_status or "",
        "insurance_approval_date": claim.insurance_approval_date.isoformat()
        if claim.insurance_approval_date
        else "",
        "claim_stage": claim.claim_stage,
        "claim_stage_label": stage_lookup.get(
            claim.claim_stage,
            str(claim.claim_stage),
        ),
        "status": claim.status,
        "pre_invoice_sent_at": claim.pre_invoice_sent_at.isoformat(
            sep=" ",
            timespec="minutes",
        )
        if claim.pre_invoice_sent_at
        else "",
        "pre_invoice_part_amount": float(
            claim.pre_invoice_part_amount or 0
        ),
        "pre_invoice_labour_amount": float(
            claim.pre_invoice_labour_amount or 0
        ),
        "liability_received_at": claim.liability_received_at.isoformat(
            sep=" ",
            timespec="minutes",
        )
        if claim.liability_received_at
        else "",
        "liability_do_amount": float(claim.liability_do_amount or 0),
        "invoice_datetime": claim.invoice_datetime.isoformat(
            sep=" ",
            timespec="minutes",
        )
        if claim.invoice_datetime
        else "",
        "invoice_amount": float(claim.invoice_amount or 0),
        "invoice_parts_amount": float(claim.invoice_parts_amount or 0),
        "invoice_labour_amount": float(claim.invoice_labour_amount or 0),
        "payment_mode": claim.payment_mode or "",
        "payment_details": claim.payment_details or "",
        "delivery_datetime": claim.delivery_datetime.isoformat(
            sep=" ",
            timespec="minutes",
        )
        if claim.delivery_datetime
        else "",
        "delivered_by": claim.delivered_by_id or "",
        "delivered_to": claim.delivered_to or "",
        "delivery_driver_name": claim.delivery_driver_name or "",
        "delivery_remarks": claim.delivery_remarks or "",
    }


def desktop_claim_list_payload(claim):
    """Stable read DTO consumed by the existing desktop Claim table."""
    vehicle = claim.vehicle if claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    jobcard = getattr(claim, "jobcard", None)

    return {
        "id": claim.id,
        "claim_no": claim.claim_no,
        "employee__name": claim.employee.name if claim.employee_id else "",
        "vehicle__registration_no": vehicle.registration_no if vehicle else "",
        "vehicle__model__name": (
            vehicle.model.name if vehicle and vehicle.model_id else ""
        ),
        "vehicle__customer__name": customer.name if customer else "",
        "vehicle__customer__mobile_no": customer.mobile_no if customer else "",
        "insurance_company__ins_co_name": (
            claim.insurance_company.ins_co_name
            if claim.insurance_company_id
            else ""
        ),
        "surveyor__name": claim.surveyor.name if claim.surveyor_id else "",
        "surveyor__mobile_no": (
            claim.surveyor.mobile_no if claim.surveyor_id else ""
        ),
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
        "has_jobcard": bool(jobcard),
        "jobcard_id": jobcard.id if jobcard else None,
    }


def derive_claim_stage(claim):
    if (
            claim.delivery_datetime
            and claim.delivered_by_id
            and claim.delivered_to
    ):
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
