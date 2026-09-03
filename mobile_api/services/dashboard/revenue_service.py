from datetime import datetime, timedelta

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from core.models import JobCard


class RevenueService:

    def __init__(
        self,
        employee,
        branch=None,
        period="today",
        start_date=None,
        end_date=None,
    ):

        self.employee = employee
        self.branch = branch

        self.period = period or "today"

        self.start_date = start_date
        self.end_date = end_date


    # ==========================================
    # DATE RANGE
    # ==========================================

    def get_date_range(self):

        today = timezone.localdate()


        # ======================================
        # CUSTOM RANGE
        # ======================================
        print(self.period)
        if self.period == "custom":

            start_date = self._parse_date(
                self.start_date
            )

            end_date = self._parse_date(
                self.end_date
            )


            if start_date and end_date:

                return start_date, end_date


            # Invalid/incomplete custom range
            return None, None


        # ======================================
        # TODAY
        # ======================================

        if self.period == "today":

            return today, today


        # ======================================
        # YESTERDAY
        # ======================================

        if self.period == "yesterday":

            yesterday = today - timedelta(days=1)

            return yesterday, yesterday


        # ======================================
        # THIS WEEK
        # ======================================

        if self.period == "this_week":

            start_date = (
                today -
                timedelta(days=today.weekday())
            )

            return start_date, today


        # ======================================
        # THIS MONTH
        # ======================================

        if self.period == "this_month":

            start_date = today.replace(day=1)

            return start_date, today


        # ======================================
        # LAST MONTH
        # ======================================

        if self.period == "last_month":

            first_day_this_month = (
                today.replace(day=1)
            )

            last_day_last_month = (
                first_day_this_month -
                timedelta(days=1)
            )

            first_day_last_month = (
                last_day_last_month.replace(day=1)
            )

            return (
                first_day_last_month,
                last_day_last_month
            )


        # ======================================
        # THIS YEAR
        # ======================================

        if self.period == "this_year":

            start_date = today.replace(
                month=1,
                day=1
            )

            return start_date, today


        # ======================================
        # FALLBACK
        # ======================================

        return today, today


    # ==========================================
    # DATE PARSER
    # ==========================================

    def _parse_date(self, value):

        if not value:
            return None


        if isinstance(value, str):

            try:

                return datetime.strptime(
                    value,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                return None


        return value


    # ==========================================
    # BASE QUERYSET
    # ==========================================

    def get_queryset(self):

        start_date, end_date = (
            self.get_date_range()
        )


        # ======================================
        # INVALID CUSTOM DATE RANGE
        # ======================================

        if not start_date or not end_date:

            return JobCard.objects.none()


        # ======================================
        # DATE FILTER
        # ======================================

        queryset = JobCard.objects.filter(

            job_date__date__range=(
                start_date,
                end_date
            )

        )


        # ======================================
        # BRANCH FILTER
        # ======================================

        if self.branch:

            queryset = queryset.filter(
                branch=self.branch
            )


        return queryset


    # ==========================================
    # REVENUE DATA
    # ==========================================

    def get(self):

        queryset = self.get_queryset()


        # ======================================
        # TOTAL SUMMARY
        # ======================================

        totals = queryset.aggregate(

            total=Sum("grand_total"),

            parts=Sum("parts_total"),

            labour=Sum("labour_total"),

        )


        total_revenue = float(
            totals["total"] or 0
        )

        parts_revenue = float(
            totals["parts"] or 0
        )

        labour_revenue = float(
            totals["labour"] or 0
        )


        # ======================================
        # REVENUE TREND
        # ======================================

        trend_queryset = (

            queryset

            .annotate(
                date=TruncDate("job_date")
            )

            .values("date")

            .annotate(

                total=Sum("grand_total"),

                parts=Sum("parts_total"),

                labour=Sum("labour_total"),

            )

            .order_by("date")

        )


        trend = []


        for item in trend_queryset:

            date = item["date"]


            if not date:
                continue


            trend.append({

                "date":
                    date.isoformat(),

                "label":
                    date.strftime(
                        "%d %b"
                    ),

                "total":
                    float(
                        item["total"] or 0
                    ),

                "parts":
                    float(
                        item["parts"] or 0
                    ),

                "labour":
                    float(
                        item["labour"] or 0
                    ),

            })


        # ======================================
        # FINAL RESPONSE
        # ======================================

        return {

            "total":
                total_revenue,

            "parts":
                parts_revenue,

            "labour":
                labour_revenue,

            "trend":
                trend,

        }