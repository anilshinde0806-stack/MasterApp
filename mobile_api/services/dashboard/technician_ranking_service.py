from django.db.models import Count

from core.models import JobCard


class TopTechnicianService:

    def __init__(self, employee, branch=None):
        self.employee = employee
        self.branch = branch

    def get(self):
        return []