from decimal import Decimal

from rest_framework import serializers

from core.models import PartOrder, PartOrderHeader


class SparePartSerializer(serializers.ModelSerializer):
    part_no = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    ordered_qty = serializers.SerializerMethodField()
    received_qty = serializers.SerializerMethodField()
    pending_qty = serializers.SerializerMethodField()
    receipt_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PartOrder
        fields = [
            "id",
            "part_no",
            "description",
            "order_no",
            "supplier",
            "order_date",
            "expected_date",
            "received_date",
            "ordered_qty",
            "received_qty",
            "pending_qty",
            "receipt_percentage",
            "status",
            "tracking_ref",
            "remarks",
            "updated_at",
        ]

    def get_part_no(self, obj):
        if obj.part:
            return obj.part.part_no or ""

        return obj.manual_part_no or ""

    def get_description(self, obj):
        if obj.part:
            return obj.part.description or ""

        return obj.manual_description or ""

    def get_ordered_qty(self, obj):
        return float(obj.ordered_qty or 0)

    def get_received_qty(self, obj):
        return float(obj.received_qty or 0)

    def get_pending_qty(self, obj):
        ordered = Decimal(obj.ordered_qty or 0)
        received = Decimal(obj.received_qty or 0)

        pending = ordered - received

        return float(max(pending, Decimal("0")))

    def get_receipt_percentage(self, obj):
        ordered = Decimal(obj.ordered_qty or 0)
        received = Decimal(obj.received_qty or 0)

        if ordered <= 0:
            return 0.0

        percentage = (received / ordered) * Decimal("100")

        return round(
            float(min(percentage, Decimal("100"))),
            2,
        )


class PartOrderHeaderSerializer(serializers.ModelSerializer):
    parts = SparePartSerializer(
        source="lines",
        many=True,
        read_only=True,
    )

    total_parts = serializers.SerializerMethodField()
    received_parts = serializers.SerializerMethodField()
    pending_parts = serializers.SerializerMethodField()

    class Meta:
        model = PartOrderHeader
        fields = [
            "id",
            "order_no",
            "order_date",
            "expected_date",
            "supplier",
            "status",
            "remarks",
            "total_parts",
            "received_parts",
            "pending_parts",
            "parts",
            "updated_at",
        ]

    def get_total_parts(self, obj):
        return obj.lines.count()

    def get_received_parts(self, obj):
        return obj.lines.filter(status="Received").count()

    def get_pending_parts(self, obj):
        return obj.lines.exclude(
            status__in=["Received", "Cancelled"],
        ).count()