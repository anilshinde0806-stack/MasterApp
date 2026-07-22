"""Shared financial read model for desktop and Flutter dashboards."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.claims.repositories.claim_queries import ClaimQueryService
from apps.claims.repositories.dashboard_financial_repository import (
    DashboardFinancialRepository,
)
from core.models import Claim, JobCardAssessmentLabour, JobCardAssessmentPart


ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=18, decimal_places=2)


class DashboardFinancialService:
    def __init__(
        self,
        *,
        user=None,
        claims=None,
        branch=None,
        period=None,
        start_date=None,
        end_date=None,
    ):
        self.user = user
        self.claims = claims
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date

    def _queryset(self):
        queryset = self.claims
        if queryset is None:
            queryset = (
                ClaimQueryService.visible_to(self.user)
                if self.user is not None
                else Claim.objects.none()
            )
        if self.branch is not None:
            queryset = queryset.filter(branch=self.branch)

        return queryset

    def _for_period(self, queryset, field):
        start, end = self._date_range()
        if start:
            queryset = queryset.filter(**{f"{field}__date__gte": start})
        if end:
            queryset = queryset.filter(**{f"{field}__date__lte": end})
        return queryset

    def _date_range(self):
        start = self._as_date(self.start_date)
        end = self._as_date(self.end_date)
        if start or end:
            return start, end

        today = timezone.localdate()
        period = (self.period or "").lower()
        if period == "today":
            return today, today
        if period == "yesterday":
            day = today - timedelta(days=1)
            return day, day
        if period == "this_week":
            return today - timedelta(days=today.weekday()), today
        if period == "this_month":
            return today.replace(day=1), today
        if period == "last_month":
            last_day = today.replace(day=1) - timedelta(days=1)
            return last_day.replace(day=1), last_day
        if period == "this_year":
            return today.replace(month=1, day=1), today
        return None, None

    @staticmethod
    def _as_date(value):
        if not value:
            return None
        if hasattr(value, "year") and not isinstance(value, str):
            return value
        return parse_date(str(value))

    def get(self):
        queryset = self._queryset()
        start, end = self._date_range()
        if DashboardFinancialRepository.is_available():
            values = DashboardFinancialRepository.get(
                claim_ids=queryset.values_list("pk", flat=True),
                start_date=start,
                end_date=end,
            )
            return self._result(values)
        return self._get_with_orm(queryset)

    @staticmethod
    def _result(values):
        money = DashboardFinancialRepository.decimal
        invoice = money(values.get("invoice"))
        collection = money(values.get("collection"))
        return {
            "estimate": float(money(values.get("estimate"))),
            "approved": float(money(values.get("approved"))),
            "approved_parts": float(money(values.get("approved_parts"))),
            "approved_labour": float(money(values.get("approved_labour"))),
            "liability": float(money(values.get("liability"))),
            "invoice": float(invoice),
            "parts": float(money(values.get("parts"))),
            "labour": float(money(values.get("labour"))),
            "collection": float(collection),
            "outstanding": float(money(values.get("outstanding"))),
            "average_job_value": float(money(values.get("average_job_value"))),
            "gross_profit": 0.0,
            "net_profit": 0.0,
            "profit_available": False,
            "collection_basis": "Invoice with payment mode recorded",
        }

    def _get_with_orm(self, queryset):
        estimate_queryset = self._for_period(queryset, "created_at")
        approval_queryset = self._for_period(
            queryset,
            "insurance_approval_date",
        )
        liability_queryset = self._for_period(
            queryset,
            "liability_received_at",
        )
        invoice_queryset = self._for_period(queryset, "invoice_datetime")

        estimate = estimate_queryset.aggregate(
            estimate=Coalesce(
                Sum(
                    Case(
                        When(estimated_amount__gt=0, then=F("estimated_amount")),
                        default=F("jobcard__grand_total"),
                        output_field=MONEY,
                    )
                ),
                ZERO,
                output_field=MONEY,
            ),
        )["estimate"] or ZERO
        approved_direct = approval_queryset.aggregate(
            approved=Coalesce(
                Sum(
                    Case(
                        When(approved_amount__gt=0, then=F("approved_amount")),
                        When(liability_do_amount__gt=0, then=F("liability_do_amount")),
                        default=ZERO,
                        output_field=MONEY,
                    )
                ),
                ZERO,
                output_field=MONEY,
            ),
        )["approved"] or ZERO
        liability = liability_queryset.aggregate(
            total=Coalesce(Sum("liability_do_amount"), ZERO, output_field=MONEY),
        )["total"] or ZERO
        invoice_values = invoice_queryset.aggregate(
            invoice=Coalesce(Sum("invoice_amount"), ZERO, output_field=MONEY),
            parts=Coalesce(Sum("invoice_parts_amount"), ZERO, output_field=MONEY),
            labour=Coalesce(Sum("invoice_labour_amount"), ZERO, output_field=MONEY),
            collection=Coalesce(
                Sum(
                    Case(
                        When(
                            Q(payment_mode__isnull=False) & ~Q(payment_mode=""),
                            then=F("invoice_amount"),
                        ),
                        default=ZERO,
                        output_field=MONEY,
                    )
                ),
                ZERO,
                output_field=MONEY,
            ),
        )
        invoice = invoice_values["invoice"] or ZERO
        collection = invoice_values["collection"] or ZERO
        invoice_count = invoice_queryset.filter(invoice_amount__gt=0).count()
        assessment_fallback_claims = self._for_period(
            queryset,
            "jobcard__created_at",
        ).filter(
            Q(approved_amount__isnull=True) | Q(approved_amount__lte=0),
            Q(liability_do_amount__isnull=True) | Q(liability_do_amount__lte=0),
        ).distinct()
        approved_parts = (
            JobCardAssessmentPart.objects.filter(
                job__claim__in=assessment_fallback_claims,
                decision__in=["New", "Repair", "KO"],
            ).aggregate(total=Coalesce(Sum("revised_amount"), ZERO))["total"]
            or ZERO
        )
        approved_labour = (
            JobCardAssessmentLabour.objects.filter(
                job__claim__in=assessment_fallback_claims,
                decision="Approved",
            ).aggregate(total=Coalesce(Sum("revised_amount"), ZERO))["total"]
            or ZERO
        )
        approved = approved_direct + approved_parts + approved_labour

        return {
            "estimate": float(estimate),
            "approved": float(approved),
            "approved_parts": float(approved_parts),
            "approved_labour": float(approved_labour),
            "liability": float(liability),
            "invoice": float(invoice),
            "parts": float(invoice_values["parts"] or ZERO),
            "labour": float(invoice_values["labour"] or ZERO),
            "collection": float(collection),
            "outstanding": float(max(invoice - collection, ZERO)),
            "average_job_value": float(
                invoice / invoice_count if invoice_count else ZERO
            ),
            "gross_profit": 0.0,
            "net_profit": 0.0,
            "profit_available": False,
            "collection_basis": "Invoice with payment mode recorded",
        }
