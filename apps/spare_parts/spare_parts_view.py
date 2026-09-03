from decimal import Decimal
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import JobCard, PartOrder, PartOrderHeader
from mobile_api.api_serializers.spare_part_serializer import (
    PartOrderHeaderSerializer,
    SparePartSerializer,
)


class JobCardSparePartsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, jobcard_id):
        jobcard = get_object_or_404(
            JobCard.objects.select_related(
                "claim",
                "claim__vehicle",
                "vehicle",
            ),
            pk=jobcard_id,
        )

        part_lines_queryset = (
            PartOrder.objects
            .select_related("part")
            .order_by("-updated_at", "-id")
        )

        headers = (
            PartOrderHeader.objects
            .filter(job=jobcard)
            .prefetch_related(
                Prefetch(
                    "lines",
                    queryset=part_lines_queryset,
                ),
            )
            .order_by("-updated_at", "-id")
        )

        # Older part orders may exist without a header.
        ungrouped_parts = (
            PartOrder.objects
            .filter(
                job=jobcard,
                order__isnull=True,
            )
            .select_related("part")
            .order_by("-updated_at", "-id")
        )

        header_data = PartOrderHeaderSerializer(
            headers,
            many=True,
            context={"request": request},
        ).data

        ungrouped_data = SparePartSerializer(
            ungrouped_parts,
            many=True,
            context={"request": request},
        ).data

        from django.db.models import Q

        all_parts = list(
            PartOrder.objects
            .filter(
                Q(job=jobcard) |
                Q(order__job=jobcard)
            )
            .select_related(
                "part",
                "order",
            )
            .distinct()
        )

        total_parts = len(all_parts)

        received_parts = sum(
            1
            for part in all_parts
            if part.status == "Received"
            or (
                part.ordered_qty > 0
                and part.received_qty >= part.ordered_qty
            )
        )

        delayed_parts = sum(
            1
            for part in all_parts
            if part.status == "Back Order"
        )

        in_transit_parts = sum(
            1
            for part in all_parts
            if part.status == "In Transit"
        )

        pending_parts = sum(
            1
            for part in all_parts
            if part.status in {
                "Pending",
                "Order Placed",
                "Partially Received",
            }
        )

        cancelled_parts = sum(
            1
            for part in all_parts
            if part.status == "Cancelled"
        )

        ordered_qty = sum(
            (
                part.ordered_qty or Decimal("0")
                for part in all_parts
            ),
            Decimal("0"),
        )

        received_qty = sum(
            (
                part.received_qty or Decimal("0")
                for part in all_parts
            ),
            Decimal("0"),
        )

        pending_qty = max(
            ordered_qty - received_qty,
            Decimal("0"),
        )

        vehicle = jobcard.vehicle

        if vehicle is None and jobcard.claim_id:
            vehicle = jobcard.claim.vehicle

        registration_no = (
            vehicle.registration_no
            if vehicle
            else ""
        )

        return Response(
            {
                "jobcard": {
                    "id": jobcard.id,
                    "job_no": jobcard.job_no,
                    "registration_no": registration_no,
                    "repair_status": jobcard.repair_status,
                },
                "summary": {
                    "total_parts": total_parts,
                    "received_parts": received_parts,
                    "in_transit_parts": in_transit_parts,
                    "pending_parts": pending_parts,
                    "delayed_parts": delayed_parts,
                    "cancelled_parts": cancelled_parts,
                    "ordered_qty": float(ordered_qty),
                    "received_qty": float(received_qty),
                    "pending_qty": float(pending_qty),
                },
                "orders": header_data,
                "ungrouped_parts": ungrouped_data,
            }
        )