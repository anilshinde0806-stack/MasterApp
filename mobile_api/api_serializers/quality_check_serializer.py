from rest_framework import serializers

from core.models import JobCardQualityCheck
from rest_framework import serializers

from core.models import QualityCheckItem
from apps.quality_check.services.quality_check_items import (
    ensure_quality_check_items,
)
class JobCardQualityCheckSerializer(serializers.ModelSerializer):
    inspector_name = serializers.SerializerMethodField()
    checked_items = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()

    class Meta:
        model = JobCardQualityCheck
        fields = [
            "id",
            "jobcard",
            "paint_finish",
            "color_match",
            "panel_alignment",
            "electrical_check",
            "ac_check",
            "road_test",
            "washing_done",
            "interior_cleaning",
            "exterior_cleaning",
            "tool_kit_available",
            "spare_wheel_available",
            "fuel_level_checked",
            "customer_belongings_checked",
            "documents_checked",
            "final_inspection",
            "remarks",
            "inspector",
            "inspector_name",
            "completed",
            "completed_at",
            "checked_items",
            "total_items",
            "completion_percentage",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "jobcard",
            "inspector",
            "inspector_name",
            "completed_at",
            "checked_items",
            "total_items",
            "completion_percentage",
            "created_at",
            "updated_at",
        ]

    def get_inspector_name(self, obj):
        if not obj.inspector:
            return ""

        full_name = obj.inspector.get_full_name()

        return full_name or obj.inspector.username

    def get_check_fields(self):
        return [
            "paint_finish",
            "color_match",
            "panel_alignment",
            "electrical_check",
            "ac_check",
            "road_test",
            "washing_done",
            "interior_cleaning",
            "exterior_cleaning",
            "tool_kit_available",
            "spare_wheel_available",
            "fuel_level_checked",
            "customer_belongings_checked",
            "documents_checked",
            "final_inspection",
        ]

    def get_checked_items(self, obj):
        return sum(
            1
            for field in self.get_check_fields()
            if getattr(obj, field, False)
        )

    def get_total_items(self, obj):
        return len(self.get_check_fields())

    def get_completion_percentage(self, obj):
        total = self.get_total_items(obj)

        if total == 0:
            return 0.0

        checked = self.get_checked_items(obj)

        return round((checked / total) * 100, 2)
class QualityCheckItemSerializer(serializers.ModelSerializer):
    checked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = QualityCheckItem
        fields = (
            "id",
            "item_key",
            "item_name",
            "category",
            "status",
            "remarks",
            "checked_by",
            "checked_by_name",
            "checked_at",
        )

        read_only_fields = (
            "id",
            "item_key",
            "item_name",
            "category",
            "checked_by",
            "checked_by_name",
            "checked_at",
        )

    def get_checked_by_name(self, obj):
        if not obj.checked_by:
            return ""

        full_name = obj.checked_by.get_full_name().strip()

        return full_name or obj.checked_by.username

    def validate(self, attrs):
        status = attrs.get(
            "status",
            getattr(self.instance, "status", "PENDING"),
        )

        remarks = attrs.get(
            "remarks",
            getattr(self.instance, "remarks", ""),
        )

        if status == QualityCheckItem.Status.NOT_OK:
            if not str(remarks).strip():
                raise serializers.ValidationError(
                    {
                        "remarks": (
                            "Remarks are required when "
                            "the result is Not OK."
                        )
                    }
                )

        return attrs
class JobCardQualityCheckResponseSerializer(
    serializers.Serializer
):
    jobcard = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    evidence_photos = serializers.SerializerMethodField()
    inspector_signature_url = serializers.SerializerMethodField()
    inspector_signatures = serializers.SerializerMethodField()
    report_url = serializers.SerializerMethodField()
    items = QualityCheckItemSerializer(
        many=True,
        read_only=True,
    )

    def get_jobcard(self, obj):
        jobcard = obj.jobcard

        advisor_name = ""

        advisor = getattr(jobcard, "advisor", None)

        if advisor:
            advisor_name = (
                advisor.get_full_name().strip()
                if hasattr(advisor, "get_full_name")
                else str(advisor)
            )

            if not advisor_name:
                advisor_name = getattr(
                    advisor,
                    "username",
                    "",
                )

        floor_supervisor_name = ""

        floor_supervisor = getattr(
            jobcard,
            "floor_supervisor",
            None,
        )

        if floor_supervisor:
            floor_supervisor_name = (
                floor_supervisor.get_full_name().strip()
                if hasattr(
                    floor_supervisor,
                    "get_full_name",
                )
                else str(floor_supervisor)
            )

            if not floor_supervisor_name:
                floor_supervisor_name = getattr(
                    floor_supervisor,
                    "username",
                    "",
                )

        return {
            "id": jobcard.id,
            "job_no": getattr(
                jobcard,
                "job_no",
                "",
            ),
            "registration_no": getattr(
                jobcard,
                "registration_no",
                "",
            ),
            "repair_status": getattr(
                jobcard,
                "repair_status",
                "",
            ),
            "advisor_name": advisor_name,
            "floor_supervisor_name":
                floor_supervisor_name,
        }

    def get_summary(self, obj):
        return {
            "remarks": obj.remarks,
            "total_items": obj.total_items,
            "ok_items": obj.ok_items,
            "not_ok_items": obj.not_ok_items,
            "pending_items": obj.pending_items,
            "checked_items": obj.checked_items,
            "completion_percentage":
                obj.completion_percentage,
            "result": obj.result,
            "completed": obj.completed,
            "completed_at": obj.completed_at,
            "inspector_name":
                self._get_inspector_name(obj),
        }

    def _absolute_url(self, path):
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path

    def get_evidence_photos(self, obj):
        return [
            {
                "id": photo.id,
                "url": self._absolute_url(photo.image.url),
                "caption": photo.caption,
                "created_at": photo.created_at,
            }
            for photo in obj.evidence_photos.all()
            if photo.image
        ]

    def get_inspector_signature_url(self, obj):
        signatures = list(obj.inspector_signatures.all())
        if signatures:
            return self._absolute_url(signatures[-1].image.url)
        if not obj.inspector_signature:
            return ""
        return self._absolute_url(obj.inspector_signature.url)

    def get_inspector_signatures(self, obj):
        signatures = []
        for signature in obj.inspector_signatures.all():
            inspector_name = ""
            if signature.inspector:
                inspector_name = (
                    signature.inspector.get_full_name().strip()
                    or signature.inspector.username
                )
            signatures.append(
                {
                    "id": signature.id,
                    "url": self._absolute_url(signature.image.url),
                    "inspector_name": inspector_name,
                    "signed_at": signature.signed_at,
                }
            )
        if not signatures and obj.inspector_signature:
            signatures.append(
                {
                    "id": 0,
                    "url": self._absolute_url(
                        obj.inspector_signature.url
                    ),
                    "inspector_name": self._get_inspector_name(obj),
                    "signed_at": obj.completed_at,
                }
            )
        return signatures

    def get_report_url(self, obj):
        from django.core import signing
        from django.urls import reverse

        path = self._absolute_url(
            reverse(
                "mobile-jobcard-quality-check-report",
                args=[obj.jobcard_id],
            )
        )
        token = signing.dumps(
            obj.jobcard_id,
            salt="mobile-quality-check-report",
        )
        return f"{path}?token={token}"

    def _get_inspector_name(self, obj):
        inspector = getattr(
            obj,
            "inspector",
            None,
        )

        if not inspector:
            return ""

        if hasattr(inspector, "get_full_name"):
            full_name = (
                inspector.get_full_name().strip()
            )

            if full_name:
                return full_name

        return getattr(
            inspector,
            "username",
            str(inspector),
        )
