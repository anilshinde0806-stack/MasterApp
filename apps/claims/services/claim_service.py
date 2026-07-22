from django.db import transaction
from django.forms import model_to_dict

from apps.common.services.base_service import BaseService
from apps.claims.repositories.claim_repository import ClaimRepository
from apps.claims.validators.claim_validator import ClaimValidator
from apps.common.repositories.master_repository import MasterRepository
from apps.common.utils.parser_utils import clean_text, parse_mobile_date, parse_mobile_datetime, decimal_or_zero
from core.models import ClaimStage, ClaimStageCode, JobCard
from core.whatsapp import send_advisor_assigned_whatsapp
from erp.erp.database.services.audit_service import AuditService
from erp.erp.database.services.document_service import DocumentService
from erp.erp.database.services.notification_service import NotificationService
from apps.claims.services.claim_helpers import (
    mobile_claim_payload,
)
from apps.claims.services.claim_upsert_service import ClaimUpsertService


class ClaimService(BaseService):

    def __init__(
            self,
            user,
            master_repository=None,
            claim_repository=None,
            document_service=None,
            audit_service=None,
            notification_service=None,
    ):
        super().__init__(user)

        # repositories
        self.master_repository = (
                master_repository or MasterRepository()
        )

        self.claim_repository = (
                claim_repository or ClaimRepository()
        )

        # ERP Services
        self.document_service = (
                document_service or DocumentService()
        )

        self.audit_service = (
                audit_service or AuditService()
        )

        self.notification_service = (
                notification_service or NotificationService()
        )

        # request
        self.data = {}
        self.pk = None

        # logged user
        self.logged_employee = None
        self.branch = None

        # masters
        self.vehicle = None
        self.advisor = None
        self.insurance_company = None
        self.surveyor = None
        self.delivered_by = None

        # business
        self.claim = None

        self.errors = {}

        self.response = None

    def initialize(self, data, pk=None):
        """
        Initialize request data and reset service state.
        """

        self.data = data or {}
        self.pk = pk

        self.errors = {}

        # Logged-in context
        self.logged_employee = None
        self.branch = None

        # Master objects
        self.vehicle = None
        self.claim = None
        self.advisor = None
        self.insurance_company = None
        self.surveyor = None
        self.delivered_by = None

        # Existing values
        self.old_advisor_id = None
        self.old_claim_stage = 0

        # Response
        self.whatsapp_result = None
        self.message = ""

    def prepare_request_values(self):
        """
        Read and normalize request values.
        """

        self.registration_no = clean_text(
            self.data.get("registrationNo")
        ).upper()

        self.requested_claim_no = clean_text(
            self.data.get("claimNo")
        )

        self.claim_type = (
                clean_text(self.data.get("claimType"))
                or "Cashless"
        )

        self.survey_status = (
                clean_text(self.data.get("surveyStatus"))
                or "Pending"
        )

        self.payment_mode = clean_text(
            self.data.get("paymentMode")
        )

        self.delivered_to = clean_text(
            self.data.get("deliveredTo")
        )

    def load_master_data(self):

        # Vehicle
        registration_no = clean_text(
            self.data.get("registrationNo")
        ).upper()

        if registration_no:
            self.vehicle = self.master_repository.get_vehicle(
                registration_no
            )

        # Existing Claim
        claim_id = (
                self.pk
                or clean_text(
            self.data.get("id")
            or self.data.get("claimId")
            or self.data.get("claim_id")
        )
        )

        if claim_id:
            self.claim = self.claim_repository.get_by_id(claim_id)

        # Masters
        self.insurance_company = (
            self.master_repository.get_insurance_company(
                self.data.get("insuranceCompany")
            )
        )

        self.advisor = (
            self.master_repository.get_employee(
                self.data.get("advisor")
            )
        )

        self.surveyor = (
            self.master_repository.get_surveyor(
                self.data.get("surveyor")
            )
        )

        self.delivered_by = (
            self.master_repository.get_employee(
                self.data.get("deliveredBy")
            )
        )

        self.logged_employee = (
            self.master_repository.get_logged_employee(
                self.user
            )
        )

        self.branch = self.master_repository.get_claim_branch(
            self.advisor,
            self.logged_employee,
        )

        if self.claim:
            self.old_advisor_id = self.claim.employee_id
            self.old_claim_stage = int(
                self.claim.claim_stage or 0
            )

    def validate(self):

        validator = ClaimValidator(self)
        validator.validate()

        validator.raise_if_invalid()

    def save(self, data, pk=None):
        return self.execute(
            lambda: self.process(data, pk)
        )

    def process(self, data, pk=None):

        self.initialize(data, pk)

        self.prepare_request_values()

        self.load_master_data()

        self.validate()

        self.process_transaction()

        self.run_after_save_safely()

        return self.build_response_safely()

    def process_transaction(self):

        with transaction.atomic():
            self.create_claim()

            self.fill_claim()

            self.calculate_claim()

            self.save_claim()

    def create_claim(self):

        if self.claim:
            self.claim.vehicle = self.vehicle

            return

        if (
                self.requested_claim_no
                and self.requested_claim_no.lower() != "auto"
        ):

            claim_no = self.requested_claim_no

        else:

            claim_no = self.document_service.generate_claim_no(
                self.branch
            )

        self.claim = self.claim_repository.create(
            claim_no=claim_no,
            vehicle=self.vehicle,
        )

        if not self.claim.branch_id:
            self.claim.branch = self.branch

    def fill_basic_information(self):

        self.claim.employee = self.advisor

        self.claim.insurance_company = (
            self.insurance_company
        )

        self.claim.claim_type = (
            self.claim_type
        )

    def fill_policy_information(self):

        self.claim.policy_no = clean_text(
            self.data.get("policyNo")
        )

        self.claim.ic_claim_no = clean_text(
            self.data.get("icClaimNo")
        )

    def fill_survey_information(self):

        self.claim.accident_date = parse_mobile_date(
            self.data.get("accidentDate")
        )

        self.claim.intimation_date = parse_mobile_date(
            self.data.get("intimationDate")
        )

        self.claim.survey_date = parse_mobile_date(
            self.data.get("surveyDate")
        )

        self.claim.surveyor = self.surveyor

        self.claim.survey_status = (
            self.survey_status
        )

        self.claim.insurance_approval_date = (
            parse_mobile_date(
                self.data.get(
                    "insuranceApprovalDate"
                )
            )
        )

    def fill_invoice_information(self):

        self.claim.invoice_datetime = parse_mobile_datetime(
            self.data.get("invoiceDateTime")
        )

        self.claim.invoice_amount = decimal_or_zero(
            self.data.get("invoiceAmount")
        )

        self.claim.invoice_parts_amount = decimal_or_zero(
            self.data.get("invoicePartsAmount")
        )

        self.claim.invoice_labour_amount = decimal_or_zero(
            self.data.get("invoiceLabourAmount")
        )

        self.claim.payment_mode = self.payment_mode

        self.claim.payment_details = clean_text(
            self.data.get("paymentDetails")
        )

    def fill_delivery_information(self):

        self.claim.delivery_datetime = (
            parse_mobile_datetime(
                self.data.get(
                    "deliveryDateTime"
                )
            )
        )

        self.claim.delivered_by = (
            self.delivered_by
        )

        self.claim.delivered_to = (
            self.delivered_to
        )

        self.claim.delivery_driver_name = (
            clean_text(
                self.data.get(
                    "driverName"
                )
            )
        )

        self.claim.delivery_remarks = (
            clean_text(
                self.data.get(
                    "deliveryRemarks"
                )
            )
        )

    def fill_pre_invoice_information(self):

        self.claim.pre_invoice_sent_at = parse_mobile_datetime(
            self.data.get("preInvoiceSentAt")
        )

        self.claim.pre_invoice_part_amount = decimal_or_zero(
            self.data.get("preInvoicePart")
        )

        self.claim.pre_invoice_labour_amount = decimal_or_zero(
            self.data.get("preInvoiceLabour")
        )

        self.claim.pre_invoice_total_amount = (
                self.claim.pre_invoice_part_amount
                + self.claim.pre_invoice_labour_amount
        )

    def fill_liability_information(self):

        self.claim.liability_received_at = parse_mobile_datetime(
            self.data.get("liabilityReceivedAt")
        )

        self.claim.liability_do_amount = decimal_or_zero(
            self.data.get("liabilityDoAmount")
        )

    def fill_claim(self):

        self.fill_basic_information()

        self.fill_policy_information()

        self.fill_survey_information()

        self.fill_pre_invoice_information()

        self.fill_liability_information()

        self.fill_invoice_information()

        self.fill_delivery_information()

    def calculate_claim(self):

        self.calculate_pre_invoice_total()

        self.calculate_customer_difference()

        self.calculate_stage()

    def calculate_stage(self):
        ClaimUpsertService.prepare(
            self.claim,
            user=self.user,
            previous_stage=self.old_claim_stage,
        )

    def jobcard_exists(self):

        if not self.claim or not self.claim.pk:
            return False

        return JobCard.objects.filter(
            claim_id=self.claim.id
        ).exists()

   
    def after_save(self):

        try:
            self.send_advisor_notification()

        except Exception as exc:
            self.message = (
                "Claim saved, but advisor notification failed: "
                f"{str(exc)[:180]}"
            )

        try:
            self.write_audit()

        except Exception as exc:
            if not self.message:
                self.message = (
                    "Claim saved, but audit entry was not written: "
                    f"{str(exc)[:180]}"
                )

    def run_after_save_safely(self):
        try:
            self.after_save()

        except Exception as exc:
            self.message = (
                "Claim saved, but post-save processing failed: "
                f"{str(exc)[:180]}"
            )

    def write_audit(self):

        self.audit_service.write(
            module_code="CLAIM",
            document_type="CLAIM",
            document_id=self.claim.id,
            action="SAVE",
            old_data=None,
            new_data=mobile_claim_payload(self.claim),
            user_id=self.user.id,
            branch_id=self.branch.id if self.branch else None,
            remarks="Claim saved from Mobile",
        )

    def build_response(self):

        return self.success(
            message=self.message or "Claim saved successfully.",
            data={
                "claim": mobile_claim_payload(self.claim),
                "whatsapp": self.whatsapp_result or {},
            },
        )

    def build_response_safely(self):
        try:
            return self.build_response()

        except Exception as exc:
            message = (
                "Claim saved, but response details could not be loaded: "
                f"{str(exc)[:180]}"
            )

            return self.success(
                message=message,
                data={
                    "message": message,
                    "claim": {
                        "id": self.claim.id if self.claim else "",
                        "claim_no": (
                            self.claim.claim_no
                            if self.claim
                            else ""
                        ),
                    },
                    "whatsapp": self.whatsapp_result or {},
                },
            )

    def calculate_customer_difference(self):

        invoice = self.claim.invoice_amount or 0

        liability = self.claim.liability_do_amount or 0

        self.claim.customer_difference_amount = (

                invoice - liability
        )

    def save_claim(self):

        self.claim_repository.save(self.claim)

    def send_notifications(self):

        pass

    def calculate_pre_invoice_total(self):

        self.claim.pre_invoice_total_amount = (

                (self.claim.pre_invoice_part_amount or 0)

                +

                (self.claim.pre_invoice_labour_amount or 0)
        )

    def send_advisor_notification(self):

        if (
                self.old_advisor_id != self.claim.employee_id
                and self.claim.employee_id
        ):

            self.whatsapp_result = (
                send_advisor_assigned_whatsapp(
                    self.claim
                )
            )

            if (
                    self.whatsapp_result
                    and
                    not self.whatsapp_result.get("success")
            ):
                self.message = (
                    "Claim saved, but WhatsApp advisor message "
                    f"was not sent: "
                    f"{str(self.whatsapp_result.get('response', ''))[:180]}"
                )
