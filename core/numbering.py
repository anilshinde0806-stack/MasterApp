import re

from django.utils import timezone

from .models import Branch, Claim, Employee, JobCard

MAX_DOCUMENT_ALIAS_LENGTH = 16


def financial_year_code(date=None):
    date = date or timezone.localdate()
    start_year = date.year if date.month >= 4 else date.year - 1
    end_year = start_year + 1
    return f"{start_year % 100:02d}{end_year % 100:02d}"


def clean_document_alias(value):
    alias = re.sub(r"[^A-Za-z0-9]", "", str(value or "").strip().upper())
    return (alias or "HO")[:MAX_DOCUMENT_ALIAS_LENGTH]


def branch_number_alias(branch, document_type):
    if branch:
        if document_type == "CLM" and branch.claim_no_alias:
            return clean_document_alias(branch.claim_no_alias)
        if document_type == "JOB" and branch.jobcard_no_alias:
            return clean_document_alias(branch.jobcard_no_alias)
        if branch.code:
            return clean_document_alias(branch.code)
    return clean_document_alias("HO")


def branch_for_user(user):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    if employee and employee.branch_id:
        return employee.branch
    return Branch.objects.filter(is_head_office=True).first() or Branch.objects.order_by("id").first()


def branch_for_claim(claim):
    if claim and claim.branch_id:
        return claim.branch
    if claim and claim.employee_id and claim.employee.branch_id:
        return claim.employee.branch
    return Branch.objects.filter(is_head_office=True).first() or Branch.objects.order_by("id").first()


def next_branch_document_no(model, field_name, branch, document_type):
    alias = branch_number_alias(branch, document_type)
    fy_code = financial_year_code()
    prefix = f"{alias}-{document_type}-{fy_code}-"
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    max_number = 0

    for value in model.objects.filter(**{f"{field_name}__istartswith": prefix}).values_list(field_name, flat=True):
        match = pattern.match(value or "")
        if match:
            max_number = max(max_number, int(match.group(1)))

    return f"{prefix}{max_number + 1:04d}"


def next_claim_no(branch=None):
    return next_branch_document_no(Claim, "claim_no", branch, "CLM")


def next_jobcard_no(branch=None):
    return next_branch_document_no(JobCard, "job_no", branch, "JOB")
