"""Shared Claim create/update business rules used by web and mobile."""

from apps.common.utils.parser_utils import decimal_or_zero
from core.models import ClaimStageCode, Employee, JobCard
from core.numbering import branch_for_claim, branch_for_user, next_claim_no


class ClaimUpsertService:
    @staticmethod
    def has_invoice_data(claim):
        return any([
            claim.invoice_datetime,
            decimal_or_zero(claim.invoice_amount) > 0,
            decimal_or_zero(claim.invoice_parts_amount) > 0,
            decimal_or_zero(claim.invoice_labour_amount) > 0,
            claim.payment_mode,
            claim.payment_details,
        ])

    @staticmethod
    def delivery_complete(claim):
        return bool(
            claim.delivery_datetime
            and claim.delivered_by_id
            and claim.delivered_to
            and (
                claim.delivered_to != "Drop By Driver"
                or claim.delivery_driver_name
            )
        )

    @classmethod
    def calculate_stage(cls, claim, previous_stage=None):
        if cls.delivery_complete(claim):
            return ClaimStageCode.CLOSED
        if cls.has_invoice_data(claim):
            derived = ClaimStageCode.INVOICED
        elif (
            claim.liability_received_at
            and decimal_or_zero(claim.liability_do_amount) > 0
            and claim.liability_document
        ):
            derived = ClaimStageCode.LIABILITY
        elif claim.insurance_approval_date and claim.assessment_file:
            derived = ClaimStageCode.INSURANCE_APPROVAL
        elif claim.survey_date and claim.surveyor_id:
            derived = ClaimStageCode.SURVEY
        elif (
            claim.intimation_date
            and claim.insurance_company_id
            and claim.policy_no
        ):
            derived = ClaimStageCode.INTIMATION
        elif claim.employee_id:
            derived = ClaimStageCode.ADVISOR_ASSIGNED
        else:
            derived = ClaimStageCode.CLAIM_CREATED

        previous = int(previous_stage or 0)
        return max(derived, previous) if previous != ClaimStageCode.CLOSED else derived

    @classmethod
    def prepare(cls, claim, *, user, previous_stage=None):
        employee = Employee.objects.filter(user=user).select_related("branch").first()
        if employee and (employee.employee_type or "").upper() == "ADVISOR":
            claim.employee = employee

        if not claim.branch_id:
            if claim.employee_id and claim.employee.branch_id:
                claim.branch = claim.employee.branch
            else:
                claim.branch = branch_for_user(user)

        if not claim.claim_no:
            claim.claim_no = next_claim_no(branch_for_claim(claim))

        claim.pre_invoice_total_amount = (
            decimal_or_zero(claim.pre_invoice_part_amount)
            + decimal_or_zero(claim.pre_invoice_labour_amount)
        )
        claim.customer_difference_amount = (
            decimal_or_zero(claim.invoice_amount)
            - decimal_or_zero(claim.liability_do_amount)
        )
        claim.claim_stage = cls.calculate_stage(
            claim,
            previous_stage=previous_stage,
        )
        claim.status = (
            "Closed" if claim.claim_stage == ClaimStageCode.CLOSED else "Open"
        )
        return claim

    @classmethod
    def validate_invoice_jobcard(cls, claim):
        if not cls.has_invoice_data(claim):
            return ""
        jobcard = JobCard.objects.filter(claim=claim).first() if claim.pk else None
        if not jobcard or (jobcard.repair_status or "").lower() != "closed":
            return (
                "First close the linked jobcard for this claim before "
                "saving invoice details."
            )
        return ""
