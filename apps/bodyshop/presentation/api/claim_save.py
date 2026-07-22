"""Compatibility adapter from the mobile Claim payload to MOS."""

from apps.bodyshop.application.commands.create_claim import (
    CreateClaimCommand,
    CreateClaimHandler,
)
from apps.bodyshop.infrastructure.persistence.django_claim_repository import (
    DjangoClaimRepository,
)
from apps.claims.services.claim_helpers import mobile_claim_payload
from apps.common.utils.parser_utils import clean_text, parse_mobile_date
from apps.core.foundation.exceptions import ValidationException
from apps.core.infrastructure.persistence.django_unit_of_work import DjangoUnitOfWork
from core.models import Branch, Claim as ClaimModel, Employee, InsuranceCompany, Vehicle
from core.numbering import next_claim_no
from core.whatsapp import send_advisor_assigned_whatsapp
from rest_framework import status


class MosClaimCreateEndpoint:
    """Preserves the legacy mobile response while invoking the MOS handler."""

    TRANSITION_FIELDS = (
        "policyNo",
        "icClaimNo",
        "intimationDate",
        "surveyDate",
        "surveyor",
        "insuranceApprovalDate",
        "preInvoiceSentAt",
        "preInvoicePart",
        "preInvoiceLabour",
        "liabilityReceivedAt",
        "liabilityDoAmount",
        "invoiceDateTime",
        "invoiceAmount",
        "invoicePartsAmount",
        "invoiceLabourAmount",
        "paymentMode",
        "paymentDetails",
        "deliveryDateTime",
        "deliveredBy",
        "deliveredTo",
        "driverName",
        "deliveryRemarks",
    )

    @classmethod
    def supports(cls, data, pk=None) -> bool:
        posted_id = clean_text(data.get("id") or data.get("claimId") or data.get("claim_id"))
        if pk or posted_id:
            return False
        return not any(clean_text(data.get(field)) for field in cls.TRANSITION_FIELDS)

    def execute(self, user, data) -> dict:
        registration_no = clean_text(data.get("registrationNo")).upper()
        if not registration_no:
            return self._validation_error("registrationNo", "Vehicle Registration No required.")

        vehicle = Vehicle.objects.filter(registration_no__iexact=registration_no).first()
        if not vehicle:
            return self._validation_error(
                "registrationNo",
                "Vehicle not found in Master data. Create vehicle first.",
            )

        advisor = self._optional(Employee, data.get("advisor"))
        insurance_company = self._optional(
            InsuranceCompany, data.get("insuranceCompany")
        )
        branch = self._claim_branch(user, advisor)
        if not branch:
            return self._validation_error("branch", "Branch is required.")

        requested_claim_no = clean_text(data.get("claimNo"))
        claim_no = (
            requested_claim_no
            if requested_claim_no and requested_claim_no.lower() != "auto"
            else next_claim_no(branch)
        )
        repository = DjangoClaimRepository()
        handler = CreateClaimHandler(repository, DjangoUnitOfWork())

        try:
            aggregate = handler.handle(
                CreateClaimCommand(
                    claim_no=claim_no,
                    vehicle_id=vehicle.id,
                    branch_id=branch.id,
                    advisor_id=advisor.id if advisor else None,
                    insurance_company_id=(
                        insurance_company.id if insurance_company else None
                    ),
                    claim_type=clean_text(data.get("claimType")) or "Cashless",
                    accident_date=parse_mobile_date(data.get("accidentDate")),
                    requested_by=str(user.id),
                )
            )
        except ValidationException as exc:
            return self._handler_validation_error(exc.message)

        claim = (
            ClaimModel.objects.select_related(
                "branch", "vehicle", "vehicle__customer", "vehicle__variant",
                "employee", "insurance_company"
            )
            .get(pk=aggregate.id)
        )
        payload = mobile_claim_payload(claim)
        message, whatsapp = self._run_legacy_effects(user, claim, payload)
        return {
            "data": {
                "success": True,
                "message": message,
                "data": {
                    "claim": payload,
                    "whatsapp": whatsapp,
                },
            },
            "status": status.HTTP_200_OK,
        }

    @staticmethod
    def _optional(model, pk):
        return model.objects.filter(pk=pk).first() if pk else None

    @staticmethod
    def _claim_branch(user, advisor):
        if advisor and advisor.branch_id:
            return advisor.branch
        employee = Employee.objects.filter(user=user).select_related("branch").first()
        if employee and employee.branch_id:
            return employee.branch
        return Branch.objects.filter(is_head_office=True).first()

    @staticmethod
    def _run_legacy_effects(user, claim, payload):
        message = "Claim saved successfully."
        whatsapp = {}
        if claim.employee_id:
            try:
                whatsapp = send_advisor_assigned_whatsapp(claim) or {}
                if whatsapp and not whatsapp.get("success"):
                    message = (
                        "Claim saved, but WhatsApp advisor message was not sent: "
                        + str(whatsapp.get("response", ""))[:180]
                    )
            except Exception as exc:
                message = f"Claim saved, but advisor notification failed: {str(exc)[:180]}"
        try:
            from erp.erp.database.services.audit_service import AuditService

            AuditService.write(
                module_code="CLAIM",
                document_type="CLAIM",
                document_id=claim.id,
                action="SAVE",
                new_data=payload,
                user_id=user.id,
                branch_id=claim.branch_id,
                remarks="Claim saved from Mobile through MOS",
            )
        except Exception as exc:
            if message == "Claim saved successfully.":
                message = f"Claim saved, but audit entry was not written: {str(exc)[:180]}"
        return message, whatsapp

    @staticmethod
    def _validation_error(field, message):
        return {
            "data": {"errors": {field: message}},
            "status": status.HTTP_400_BAD_REQUEST,
        }

    def _handler_validation_error(self, message):
        mappings = (
            ("Claim number", "claimNo"),
            ("open claim", "registrationNo"),
            ("open jobcard", "registrationNo"),
            ("Claim type", "claimType"),
            ("Vehicle", "registrationNo"),
            ("Branch", "branch"),
        )
        field = next((name for text, name in mappings if text.lower() in message.lower()), "claim")
        return self._validation_error(field, message)
