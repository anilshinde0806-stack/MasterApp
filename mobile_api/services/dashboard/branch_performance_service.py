from django.db.models import Count, Sum, Avg

from core.models import JobCard


class BranchPerformanceService:

    def __init__(self, employee, branch=None, period="today", start_date=None, end_date=None):
        self.employee = employee
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date

    def get(self):
        return []