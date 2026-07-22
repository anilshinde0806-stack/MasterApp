from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.common.utils.parser_utils import clean_text
from core.models import Claim, ClaimStageCode, JobCard


class ClaimValidator:

    def __init__(self, service):
        self.service = service
        self.data = service.data or {}
        self.errors = service.errors

    def validate(self):
        self.validate_vehicle()
        self.validate_claim()
        self.validate_open_claim()
        self.validate_open_jobcard()
        self.validate_claim_type()
        self.validate_survey_status()
        self.validate_payment_mode()
        self.validate_delivery()
        self.validate_invoice_jobcard()
        self.validate_intimation()

        return self.errors

    def validate_vehicle(self):
        if not self.service.registration_no:
            self.errors["registrationNo"] = (
                "Vehicle Registration No required."
            )

            return

        if not self.service.vehicle:
            self.errors["registrationNo"] = (
                "Vehicle not found in Master data. Create vehicle first."
            )

    def validate_claim(self):
        claim_id = (
            self.service.pk
            or clean_text(
                self.data.get("id")
                or self.data.get("claimId")
                or self.data.get("claim_id")
            )
        )

        if claim_id and not self.service.claim:
            self.errors["claim"] = "Claim not found."

    def validate_open_claim(self):
        if not self.service.vehicle:
            return

        open_claims = (
            Claim.objects
            .filter(vehicle=self.service.vehicle)
            .exclude(claim_stage=ClaimStageCode.CLOSED)
            .exclude(status="Closed")
        )

        if self.service.claim:
            open_claims = open_claims.exclude(
                pk=self.service.claim.pk
            )

        open_claim = open_claims.order_by("-id").first()

        if open_claim:
            self.errors["registrationNo"] = (
                "Open claim already exists for this vehicle: "
                f"{open_claim.claim_no}."
            )

    def validate_open_jobcard(self):
        if not self.service.vehicle:
            return

        open_jobcard = (
            JobCard.objects
            .filter(
                Q(claim__vehicle=self.service.vehicle)
                | Q(vehicle=self.service.vehicle)
            )
            .exclude(repair_status__iexact="Closed")
            .order_by("-id")
            .first()
        )

        if not open_jobcard:
            return

        if (
                self.service.claim
                and open_jobcard.claim_id == self.service.claim.id
        ):
            return

        self.errors["registrationNo"] = (
            "Open jobcard already exists for this vehicle: "
            f"{open_jobcard.job_no}."
        )

    def validate_claim_type(self):
        if (
                self.service.claim_type
                not in dict(Claim.CLAIM_TYPE_CHOICES)
        ):
            self.errors["claimType"] = "Select valid Claim Type."

    def validate_survey_status(self):
        if (
                self.service.survey_status
                and self.service.survey_status
                not in dict(Claim.SURVEY_STATUS_CHOICES)
        ):
            self.errors["surveyStatus"] = (
                "Select valid Survey Status."
            )

    def validate_payment_mode(self):
        if (
                self.service.payment_mode
                and self.service.payment_mode
                not in dict(Claim.PAYMENT_MODE_CHOICES)
        ):
            self.errors["paymentMode"] = "Select valid Payment Mode."

    def validate_delivery(self):
        if (
                self.service.delivered_to
                and self.service.delivered_to
                not in dict(Claim.DELIVERY_TO_CHOICES)
        ):
            self.errors["deliveredTo"] = (
                "Select valid Delivered To option."
            )

        if (
            self.service.delivered_to == "Drop By Driver"
            and not clean_text(self.data.get("driverName"))
        ):
            self.errors["driverName"] = "Driver Name is required."

    def validate_invoice_jobcard(self):
        has_invoice_data = any(
            clean_text(self.data.get(key))
            for key in (
                "invoiceDateTime",
                "invoiceAmount",
                "invoicePartsAmount",
                "invoiceLabourAmount",
                "paymentMode",
                "paymentDetails",
            )
        )
        if not has_invoice_data:
            return
        jobcard = (
            JobCard.objects.filter(claim=self.service.claim).first()
            if self.service.claim
            else None
        )
        if not jobcard or (jobcard.repair_status or "").lower() != "closed":
            self.errors["invoice"] = (
                "First close the linked jobcard for this claim before "
                "saving invoice details."
            )

    def validate_intimation(self):
        has_intimation_data = any(
            [
                clean_text(self.data.get("intimationDate")),
                clean_text(self.data.get("policyNo")),
                clean_text(self.data.get("icClaimNo")),
            ]
        )

        if not has_intimation_data:
            return

        if not self.service.claim:
            self.errors["jobcard"] = (
                "Save claim and create Jobcard before "
                "Claim Intimation stage."
            )

            return

        if not self.jobcard_exists():
            self.errors["jobcard"] = (
                "Create Jobcard before moving to "
                "Claim Intimation stage."
            )

    def jobcard_exists(self):
        return JobCard.objects.filter(
            claim=self.service.claim
        ).exists()

    def raise_if_invalid(self):
        if self.errors:
            raise ValidationError(
                {
                    "errors": self.errors
                }
            )
