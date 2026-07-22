from .admin_dashboard import AdminDashboardService
from .advisor_dashboard import AdvisorDashboardService
from .technician_dashboard import TechnicianDashboardService
from .security_dashboard import SecurityDashboardService
from .reception_dashboard import ReceptionDashboardService
from .default_dashboard import DefaultDashboardService
from .floor_supervisor_dashboard import FloorSupervisorDashboardService
from apps.claims.repositories.dashboard_repository import DashboardLookupRepository

class DashboardService:

    def __init__(
            self,
            user,
            branch=None,
            period="today",
            start_date=None,
            end_date=None,
    ):
        self.user = user

        self.branch = branch
        self.period = period

        self.start_date = start_date
        self.end_date = end_date

        self.employee = DashboardLookupRepository.employee_for_user(user)
    def get_dashboard(self):

        employee = self.employee

        if employee is None:
            return DefaultDashboardService(self.user).get()

        employee_type = (employee.employee_type or "").upper()
        designation = (employee.designation or "").upper()

        if self.user.is_superuser or employee_type in ["ADMIN", "MANAGER"]:
            return AdminDashboardService(
                user=self.user,
                employee=employee,
                branch=self.branch,
                period=self.period,
                start_date=self.start_date,
                end_date=self.end_date,
            ).get()

        if employee_type == "ADVISOR":
            return AdvisorDashboardService(
                self.user,
                employee=employee,
                branch=self.branch,
                period=self.period,
                start_date=self.start_date,
                end_date=self.end_date,
            ).get()

        if employee_type == "FLOOR SUPERVISOR":
            return FloorSupervisorDashboardService(
                self.user,
                self.branch,
            ).get()

        if employee_type == "STAFF":
            if any(role in designation for role in [
                "TECHNICIAN",
                "PAINTER",
                "DENTER",
            ]):
                return TechnicianDashboardService(
                    self.user,
                    employee=employee,
                    branch=self.branch,
                ).get()

        if employee_type == "GATE SECURITY":
            return SecurityDashboardService(self.user).get()

        if employee_type == "RECEPTION":
            return ReceptionDashboardService(self.user).get()

        return DefaultDashboardService(self.user).get()
