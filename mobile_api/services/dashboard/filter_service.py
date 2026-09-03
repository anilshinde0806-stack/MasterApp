from datetime import timedelta

from django.utils import timezone


class DashboardFilterService:

    def __init__(
        self,
        queryset,
        employee=None,
        branch=None,
        period=None,
        start_date=None,
        end_date=None,
        date_field="created_at",
        branch_field="branch",
    ):

        self.queryset = queryset

        self.employee = employee
        self.branch = branch

        self.period = period

        self.start_date = start_date
        self.end_date = end_date

        # Configurable fields
        self.date_field = date_field
        self.branch_field = branch_field


    # ==========================================
    # MAIN FILTER
    # ==========================================

    def filter(self):

        qs = self.queryset

        qs = self._filter_branch(qs)

        qs = self._filter_period(qs)

        return qs


    # ==========================================
    # BRANCH FILTER
    # ==========================================

    def _filter_branch(self, qs):

        if self.branch:

            qs = qs.filter(
                **{
                    self.branch_field: self.branch
                }
            )

        return qs


    # ==========================================
    # PERIOD FILTER
    # ==========================================

    def _filter_period(self, qs):

        today = timezone.localdate()


        # ======================================
        # TODAY
        # ======================================

        if self.period == "today":

            return qs.filter(
                **{
                    f"{self.date_field}__date": today
                }
            )


        # ======================================
        # YESTERDAY
        # ======================================

        if self.period == "yesterday":

            return qs.filter(
                **{
                    f"{self.date_field}__date":
                        today - timedelta(days=1)
                }
            )


        # ======================================
        # THIS WEEK
        # ======================================

        if self.period == "this_week":

            start = today - timedelta(
                days=today.weekday()
            )

            return qs.filter(
                **{
                    f"{self.date_field}__date__range": [
                        start,
                        today,
                    ]
                }
            )


        # ======================================
        # THIS MONTH
        # ======================================

        if self.period == "this_month":

            return qs.filter(
                **{
                    f"{self.date_field}__year": today.year,
                    f"{self.date_field}__month": today.month,
                }
            )


        # ======================================
        # LAST MONTH
        # ======================================

        if self.period == "last_month":

            first_day = today.replace(day=1)

            last_month = (
                first_day - timedelta(days=1)
            )

            return qs.filter(
                **{
                    f"{self.date_field}__year":
                        last_month.year,

                    f"{self.date_field}__month":
                        last_month.month,
                }
            )


        # ======================================
        # THIS YEAR
        # ======================================

        if self.period == "this_year":

            return qs.filter(
                **{
                    f"{self.date_field}__year":
                        today.year
                }
            )


        # ======================================
        # CUSTOM DATE RANGE
        # ======================================

        if (
            self.period == "custom"
            and self.start_date
            and self.end_date
        ):

            return qs.filter(
                **{
                    f"{self.date_field}__date__range": [
                        self.start_date,
                        self.end_date,
                    ]
                }
            )


        # No period filter
        return qs