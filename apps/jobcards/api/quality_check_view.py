from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from mobile_api.api_serializers.quality_check_serializer import (
    JobCardQualityCheckResponseSerializer, JobCardQualityCheckSerializer,
)
from django.db import transaction
from core.models import (
    JobCard,
    JobCardQualityCheck,
    QualityCheckItem,
)

from apps.quality_check.services.quality_check_items import (
    QUALITY_CHECK_ITEMS,
    ensure_quality_check_items,
)


class JobCardQualityCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_jobcard(self, jobcard_id):
        return get_object_or_404(
            JobCard,
            pk=jobcard_id,
        )

    def get_quality_check(self, jobcard):
        quality_check, _ = JobCardQualityCheck.objects.get_or_create(
            jobcard=jobcard,
        )

        ensure_quality_check_items(quality_check)

        return (
            JobCardQualityCheck.objects
            .select_related(
                "jobcard",
                "inspector",
            )
            .prefetch_related(
                "items",
                "items__checked_by",
                "evidence_photos",
                "inspector_signatures__inspector",
            )
            .get(pk=quality_check.pk)
        )

    def get(self, request, jobcard_id):
        jobcard = self.get_jobcard(jobcard_id)
        quality_check = self.get_quality_check(jobcard)

        serializer = JobCardQualityCheckResponseSerializer(
            quality_check,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def patch(self, request, jobcard_id):
        jobcard = self.get_jobcard(jobcard_id)
        quality_check = self.get_quality_check(jobcard)

        item_id = request.data.get("item_id")

        legacy_item_keys = {
            item["item_key"]
            for item in QUALITY_CHECK_ITEMS
        }
        supplied_legacy_keys = (
            legacy_item_keys.intersection(request.data.keys())
        )

        if not item_id and supplied_legacy_keys:
            return self.patch_legacy_payload(
                request=request,
                jobcard=jobcard,
                quality_check=quality_check,
                supplied_item_keys=supplied_legacy_keys,
            )

        item_status = str(
            request.data.get("status", "")
        ).strip().upper()
        remarks = str(
            request.data.get("remarks", "")
        ).strip()

        if not item_id:
            return Response(
                {
                    "item_id": [
                        "Quality-check item ID is required."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_statuses = {
            QualityCheckItem.Status.PENDING,
            QualityCheckItem.Status.OK,
            QualityCheckItem.Status.NOT_OK,
        }

        if item_status not in allowed_statuses:
            return Response(
                {
                    "status": [
                        "Status must be PENDING, OK, or NOT_OK."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
                item_status == QualityCheckItem.Status.NOT_OK
                and not remarks
        ):
            return Response(
                {
                    "remarks": [
                        "Remarks are required when status is NOT_OK."
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = get_object_or_404(
            QualityCheckItem.objects.select_for_update(),
            pk=item_id,
            quality_check=quality_check,
        )

        item.status = item_status
        item.remarks = remarks

        if item_status == QualityCheckItem.Status.PENDING:
            item.checked_by = None
            item.checked_at = None
        else:
            item.checked_by = request.user
            item.checked_at = timezone.now()

        item.save(
            update_fields=[
                "status",
                "remarks",
                "checked_by",
                "checked_at",
            ]
        )

        self.update_quality_check_summary(
            request=request,
            jobcard=jobcard,
            quality_check=quality_check,
        )

        quality_check = self.get_serializable_quality_check(
            quality_check.pk,
        )

        serializer = JobCardQualityCheckResponseSerializer(
            quality_check,
            context={"request": request},
        )

        return Response(
            {
                "message": (
                    f"{item.item_name} updated successfully."
                ),
                **serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def patch_legacy_payload(
            self,
            request,
            jobcard,
            quality_check,
            supplied_item_keys,
    ):
        invalid_fields = {
            key: ["This field must be a boolean."]
            for key in supplied_item_keys
            if not isinstance(request.data.get(key), bool)
        }

        if invalid_fields:
            return Response(
                invalid_fields,
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        items = quality_check.items.select_for_update().filter(
            item_key__in=supplied_item_keys,
        )

        for item in items:
            is_checked = request.data[item.item_key]
            if is_checked:
                item.status = QualityCheckItem.Status.OK
                item.remarks = ""
                item.checked_by = request.user
                item.checked_at = now
            elif item.status != QualityCheckItem.Status.NOT_OK:
                item.status = QualityCheckItem.Status.PENDING
                item.remarks = ""
                item.checked_by = None
                item.checked_at = None

        QualityCheckItem.objects.bulk_update(
            items,
            [
                "status",
                "remarks",
                "checked_by",
                "checked_at",
            ],
        )

        quality_check.remarks = str(
            request.data.get("remarks", quality_check.remarks)
        ).strip()
        quality_check.save(update_fields=["remarks"])

        self.update_quality_check_summary(
            request=request,
            jobcard=jobcard,
            quality_check=quality_check,
        )

        quality_check = self.get_serializable_quality_check(
            quality_check.pk,
        )
        serializer = JobCardQualityCheckResponseSerializer(
            quality_check,
            context={"request": request},
        )

        return Response(
            {
                "message": "Quality check updated successfully.",
                **serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def get_serializable_quality_check(quality_check_id):
        return (
            JobCardQualityCheck.objects
            .select_related(
                "jobcard",
                "inspector",
            )
            .prefetch_related(
                "items",
                "items__checked_by",
                "evidence_photos",
                "inspector_signatures__inspector",
            )
            .get(pk=quality_check_id)
        )

    def update_quality_check_summary(
            self,
            request,
            jobcard,
            quality_check,
    ):
        has_items = quality_check.items.exists()

        has_pending_items = quality_check.items.filter(
            status=QualityCheckItem.Status.PENDING,
        ).exists()

        quality_check.completed = (
                has_items and not has_pending_items
        )

        quality_check.inspector = request.user

        if quality_check.completed:
            quality_check.completed_at = (
                    quality_check.completed_at or timezone.now()
            )
        else:
            quality_check.completed_at = None

        quality_check.save(
            update_fields=[
                "completed",
                "completed_at",
                "inspector",
            ]
        )

        self.update_jobcard_flags(
            jobcard=jobcard,
            quality_check=quality_check,
        )

    def put(self, request, jobcard_id):
        return self.patch(request, jobcard_id)

    @staticmethod
    def get_registration_no(jobcard):
        if hasattr(jobcard, "registration_no"):
            return jobcard.registration_no or ""

        vehicle = getattr(jobcard, "vehicle", None)

        if vehicle:
            return getattr(vehicle, "registration_no", "") or ""

        return ""

    @staticmethod
    def get_repair_status(jobcard):
        if hasattr(jobcard, "get_repair_status_display"):
            return jobcard.get_repair_status_display()

        return str(getattr(jobcard, "repair_status", "") or "")

    @staticmethod
    def update_jobcard_flags(jobcard, quality_check):
        update_fields = []

        if hasattr(jobcard, "qc_done"):
            jobcard.qc_done = quality_check.completed
            update_fields.append("qc_done")

        washing_item = quality_check.items.filter(
            item_key="washing_done",
        ).first()

        if (
                washing_item is not None
                and hasattr(jobcard, "washing_done")
        ):
            jobcard.washing_done = (
                    washing_item.status
                    == QualityCheckItem.Status.OK
            )
            update_fields.append("washing_done")

        road_test_item = quality_check.items.filter(
            item_key="road_test",
        ).first()

        if (
                road_test_item is not None
                and hasattr(jobcard, "road_test_done")
        ):
            jobcard.road_test_done = (
                    road_test_item.status
                    == QualityCheckItem.Status.OK
            )
            update_fields.append("road_test_done")

        if update_fields:
            jobcard.save(
                update_fields=list(set(update_fields))
            )
