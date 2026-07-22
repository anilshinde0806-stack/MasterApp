from apps.common.repositories.base_repository import BaseRepository
from core.models import Branch
from core.models import Employee
from core.models import InsuranceCompany
from core.models import Surveyor
from core.models import Vehicle


class MasterRepository(BaseRepository):

    # ----------------------------
    # Vehicle
    # ----------------------------

    @staticmethod
    def get_vehicle(registration_no):

        if not registration_no:
            return None

        return (
            Vehicle.objects
            .filter(registration_no__iexact=registration_no)
            .first()
        )

    # ----------------------------
    # Employee
    # ----------------------------

    @staticmethod
    def get_employee(employee_id):

        if not employee_id:
            return None

        return Employee.objects.filter(
            pk=employee_id
        ).first()

    @staticmethod
    def get_logged_employee(user):

        return (
            Employee.objects
            .select_related("branch")
            .filter(user=user)
            .first()
        )

    # ----------------------------
    # Insurance
    # ----------------------------

    @staticmethod
    def get_insurance_company(company_id):

        if not company_id:
            return None

        return InsuranceCompany.objects.filter(
            pk=company_id
        ).first()

    # ----------------------------
    # Surveyor
    # ----------------------------

    @staticmethod
    def get_surveyor(surveyor_id):

        if not surveyor_id:
            return None

        return Surveyor.objects.filter(
            pk=surveyor_id
        ).first()

    # ----------------------------
    # Branch
    # ----------------------------

    @staticmethod
    def get_head_office():

        return Branch.objects.filter(
            is_head_office=True
        ).first()

    def get_claim_branch(self, advisor, logged_employee):

        if advisor and advisor.branch_id:
            return advisor.branch

        if logged_employee and logged_employee.branch_id:
            return logged_employee.branch

        return Branch.objects.filter(
            is_head_office=True
        ).first()
