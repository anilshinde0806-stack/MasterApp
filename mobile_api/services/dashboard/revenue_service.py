class RevenueService:

    def __init__(self, employee, branch=None):
        self.employee = employee
        self.branch = branch

    def get(self):
        return []