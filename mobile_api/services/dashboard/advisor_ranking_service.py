from django.db.models import Count, Sum, Avg

from core.models import Claim


class TopAdvisorService:

    def __init__(self, employee, branch=None):
        self.employee = employee
        self.branch = branch

    def get(self):
        return []