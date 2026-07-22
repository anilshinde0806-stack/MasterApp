from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from core.numbering import next_claim_no, next_jobcard_no


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
