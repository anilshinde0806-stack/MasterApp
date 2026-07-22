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
    ):
        self.queryset = queryset
        self.employee = employee
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date

    def filter(self):
        qs = self.queryset
        qs = self._filter_branch(qs)
        qs = self._filter_period(qs)
        return qs

    def _filter_branch(self, qs):

        if self.branch:
            qs = qs.filter(branch=self.branch)

        return qs

    def _filter_period(self, qs):

        today = timezone.localdate()

        if self.period == "today":
            return qs.filter(created_at__date=today)

        if self.period == "yesterday":
            return qs.filter(
                created_at__date=today - timedelta(days=1)
            )

        if self.period == "this_week":

            start = today - timedelta(days=today.weekday())

            return qs.filter(created_at__date__gte=start)

        if self.period == "this_month":

            return qs.filter(
                created_at__year=today.year,
                created_at__month=today.month,
            )

        if self.period == "last_month":

            first = today.replace(day=1)

            last_month = first - timedelta(days=1)

            return qs.filter(
                created_at__year=last_month.year,
                created_at__month=last_month.month,
            )

        if self.period == "this_year":

            return qs.filter(
                created_at__year=today.year
            )

        if (
            self.period == "custom"
            and self.start_date
            and self.end_date
        ):

            return qs.filter(
                created_at__date__range=[
                    self.start_date,
                    self.end_date,
                ]
            )

        return qs
