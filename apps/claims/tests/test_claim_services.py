from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from apps.claims.repositories.claim_queries import ClaimQueryService
from apps.claims.services.claim_delete_service import (
    ClaimDeleteForbidden,
    ClaimDeleteService,
    ClaimHasJobCard,
)
from apps.claims.services.claim_upsert_service import ClaimUpsertService
from apps.claims.services.repair_workflow_service import (
    RepairWorkflowBlocked,
    RepairWorkflowService,
)
from apps.claims.services.dashboard_financial_service import DashboardFinancialService
from apps.claims.services.dashboard_metrics_service import DashboardMetricsService
from apps.claims.services.dashboard_kpi_service import DashboardKPIService
from core.models import ClaimStageCode
from django.utils import timezone
from core.models import (
    Branch,
    Claim,
    Customer,
    Employee,
    JobCard,
    WorkAllocation,
    WorkProgress,
    Vehicle,
    VehicleModel,
    VehicleVariant,
)


class ClaimServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.branch_a = Branch.objects.create(name="Branch A", code="BA")
        cls.branch_b = Branch.objects.create(name="Branch B", code="BB")

        cls.manager_user = User.objects.create_user("claim_manager")
        cls.manager = Employee.objects.create(
            user=cls.manager_user,
            name="Manager",
            employee_code="MGR-CLAIM",
            employee_type="MANAGER",
            branch=cls.branch_a,
        )
        cls.advisor_user = User.objects.create_user("claim_advisor")
        cls.advisor = Employee.objects.create(
            user=cls.advisor_user,
            name="Advisor",
            employee_code="ADV-CLAIM",
            employee_type="Advisor",
            branch=cls.branch_a,
        )
        cls.other_advisor_user = User.objects.create_user("other_advisor")
        cls.other_advisor = Employee.objects.create(
            user=cls.other_advisor_user,
            name="Other Advisor",
            employee_code="ADV-OTHER",
            employee_type="Advisor",
            branch=cls.branch_a,
        )

        customer = Customer.objects.create(name="Claim Customer")
        model = VehicleModel.objects.create(name="Claim Model")
        variant = VehicleVariant.objects.create(model=model, name="Claim Variant")

        def vehicle(number):
            return Vehicle.objects.create(
                registration_no=number,
                chassis_no=f"CH-{number}",
                engine_no=f"EN-{number}",
                model=model,
                variant=variant,
                color="White",
                sale_date=date(2026, 1, 1),
                vehicle_type="PV",
                customer=customer,
            )

        cls.advisor_claim = Claim.objects.create(
            claim_no="CLM-SHARED-1",
            vehicle=vehicle("GJ01AA0001"),
            branch=cls.branch_a,
            employee=cls.advisor,
        )
        cls.other_claim = Claim.objects.create(
            claim_no="CLM-SHARED-2",
            vehicle=vehicle("GJ01AA0002"),
            branch=cls.branch_a,
            employee=cls.other_advisor,
        )
        cls.branch_b_claim = Claim.objects.create(
            claim_no="CLM-SHARED-3",
            vehicle=vehicle("GJ01AA0003"),
            branch=cls.branch_b,
        )

    def test_advisor_sees_only_assigned_claims(self):
        ids = set(
            ClaimQueryService.visible_to(self.advisor_user)
            .values_list("id", flat=True)
        )
        self.assertEqual(ids, {self.advisor_claim.id})

    def test_manager_sees_own_branch_only(self):
        ids = set(
            ClaimQueryService.visible_to(self.manager_user)
            .values_list("id", flat=True)
        )
        self.assertEqual(ids, {self.advisor_claim.id, self.other_claim.id})

    def test_advisor_cannot_delete_claim(self):
        with self.assertRaises(ClaimDeleteForbidden):
            ClaimDeleteService.delete(
                claim_id=self.advisor_claim.id,
                user=self.advisor_user,
            )

    def test_claim_with_jobcard_cannot_be_deleted(self):
        JobCard.objects.create(
            claim=self.advisor_claim,
            job_no="JOB-SHARED-1",
        )
        with self.assertRaises(ClaimHasJobCard):
            ClaimDeleteService.delete(
                claim_id=self.advisor_claim.id,
                user=self.manager_user,
            )

    def test_manager_can_delete_unlinked_claim(self):
        claim_id = self.other_claim.id
        ClaimDeleteService.delete(
            claim_id=claim_id,
            user=self.manager_user,
        )
        self.assertFalse(Claim.objects.filter(pk=claim_id).exists())

    def test_upsert_does_not_regress_existing_stage(self):
        claim = self.advisor_claim
        claim.claim_stage = ClaimStageCode.REPAIR_IN_PROGRESS
        claim.survey_date = None
        claim.surveyor = None

        stage = ClaimUpsertService.calculate_stage(
            claim,
            previous_stage=ClaimStageCode.REPAIR_IN_PROGRESS,
        )
        self.assertEqual(stage, ClaimStageCode.REPAIR_IN_PROGRESS)

    def test_driver_delivery_requires_driver_name(self):
        claim = self.advisor_claim
        claim.delivery_datetime = claim.created_at
        claim.delivered_by = self.manager
        claim.delivered_to = "Drop By Driver"
        claim.delivery_driver_name = ""

        self.assertFalse(ClaimUpsertService.delivery_complete(claim))
        claim.delivery_driver_name = "Driver One"
        self.assertTrue(ClaimUpsertService.delivery_complete(claim))

    def test_shared_upsert_calculates_financial_totals(self):
        claim = self.advisor_claim
        claim.pre_invoice_part_amount = 100
        claim.pre_invoice_labour_amount = 50
        claim.invoice_amount = 500
        claim.liability_do_amount = 425

        ClaimUpsertService.prepare(
            claim,
            user=self.manager_user,
            previous_stage=ClaimStageCode.CLAIM_CREATED,
        )
        self.assertEqual(claim.pre_invoice_total_amount, 150)
        self.assertEqual(claim.customer_difference_amount, 75)

    def test_repair_allocation_is_blocked_at_insurance_approval_stage(self):
        self.advisor_claim.claim_stage = ClaimStageCode.INSURANCE_APPROVAL
        self.advisor_claim.save(update_fields=["claim_stage"])
        job = JobCard.objects.create(
            claim=self.advisor_claim,
            job_no="JOB-GATE-1",
        )
        with self.assertRaises(RepairWorkflowBlocked):
            RepairWorkflowService.ensure_allocation_allowed(job)

    def test_repair_start_advances_claim_from_allocation_to_repair(self):
        self.advisor_claim.claim_stage = ClaimStageCode.WORK_ALLOCATION
        self.advisor_claim.save(update_fields=["claim_stage"])
        job = JobCard.objects.create(
            claim=self.advisor_claim,
            job_no="JOB-GATE-2",
        )
        RepairWorkflowService.ensure_start_allowed(job)
        RepairWorkflowService.mark_repair_started(job)
        self.advisor_claim.refresh_from_db()
        self.assertEqual(
            self.advisor_claim.claim_stage,
            ClaimStageCode.REPAIR_IN_PROGRESS,
        )

    def test_premature_progress_does_not_become_effective_repair(self):
        self.advisor_claim.claim_stage = ClaimStageCode.INSURANCE_APPROVAL
        self.advisor_claim.save(update_fields=["claim_stage"])
        job = JobCard.objects.create(
            claim=self.advisor_claim,
            job_no="JOB-GATE-3",
        )
        allocation = WorkAllocation.objects.create(job=job)
        progress = WorkProgress.objects.create(
            allocation=allocation,
            stage=WorkProgress.STAGES[0][0],
            start_time=timezone.now(),
        )
        self.assertFalse(RepairWorkflowService.progress_is_effective(progress))

    def test_dashboard_financial_uses_recorded_claim_values(self):
        claim = self.advisor_claim
        claim.estimated_amount = 1000
        claim.approved_amount = 800
        claim.liability_do_amount = 750
        claim.invoice_amount = 900
        claim.invoice_parts_amount = 500
        claim.invoice_labour_amount = 400
        claim.payment_mode = "UPI"
        claim.save()

        financial = DashboardFinancialService(
            claims=Claim.objects.filter(pk=claim.pk),
        ).get()

        self.assertEqual(financial["estimate"], 1000.0)
        self.assertEqual(financial["approved"], 800.0)
        self.assertEqual(financial["liability"], 750.0)
        self.assertEqual(financial["invoice"], 900.0)
        self.assertEqual(financial["parts"], 500.0)
        self.assertEqual(financial["labour"], 400.0)
        self.assertEqual(financial["collection"], 900.0)
        self.assertEqual(financial["outstanding"], 0.0)

    def test_dashboard_metrics_database_function_matches_orm(self):
        today = timezone.localdate()
        job = JobCard.objects.create(
            claim=self.advisor_claim,
            job_no="JOB-DASHBOARD-METRICS",
            grand_total=1250,
        )
        service = DashboardMetricsService(
            claims=Claim.objects.filter(pk=self.advisor_claim.pk),
            period_claims=Claim.objects.filter(pk=self.advisor_claim.pk),
            jobcards=JobCard.objects.filter(pk=job.pk),
            start_date=today,
            end_date=today,
        )

        self.assertEqual(service.get(), service._get_with_orm())

    def test_dashboard_kpi_database_function_matches_orm(self):
        job = JobCard.objects.create(
            claim=self.advisor_claim,
            job_no="JOB-DASHBOARD-KPI",
            repair_status="Open",
        )
        service = DashboardKPIService(
            claims=Claim.objects.filter(pk=self.advisor_claim.pk),
            jobcards=JobCard.objects.filter(pk=job.pk),
        )

        self.assertEqual(service.get(), service._get_with_orm())
