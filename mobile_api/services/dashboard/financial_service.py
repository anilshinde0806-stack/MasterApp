from apps.claims.services.dashboard_financial_service import DashboardFinancialService


class FinancialService:

    def __init__(self, employee, branch=None, period=None, start_date=None, end_date=None):
        self.employee = employee
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date

    def get(self):
        return DashboardFinancialService(
            user=self.employee.user if self.employee else None,
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        ).get()
