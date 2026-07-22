"""Mobile Claim presentation endpoints.

URLs remain registered by ``mobile_api.urls`` for backward compatibility.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.claims.repositories.claim_queries import ClaimQueryService
from apps.claims.services.claim_delete_service import (
    ClaimDeleteForbidden,
    ClaimDeleteService,
    ClaimHasJobCard,
    ClaimNotFound,
)
from apps.claims.services.claim_helpers import mobile_claim_payload
from apps.claims.services.claim_service import ClaimService
from apps.bodyshop.module import BodyShopModule
from apps.bodyshop.presentation.api import MosClaimCreateEndpoint
from apps.core.platform.feature_flags import FeatureFlags


class MobileClaimListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = ClaimQueryService.filtered(
            request.user,
            branch_id=request.GET.get("branch"),
            from_date=request.GET.get("from_date"),
            to_date=request.GET.get("to_date"),
            status=request.GET.get("status") or "open",
        )

        rows = []
        for claim in claims.order_by("-id")[:100]:
            row = mobile_claim_payload(claim)
            row.update({
                "created_at": (
                    claim.created_at.isoformat() if claim.created_at else ""
                ),
                "pending_days": (
                    timezone.localdate() - claim.created_at.date()
                ).days if claim.created_at else 0,
            })
            rows.append(row)

        return Response({"claims": rows})


class MobileClaimDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        claim = (
            ClaimQueryService.filtered(request.user, status="all")
            .select_related("delivered_by")
            .filter(pk=pk)
            .first()
        )
        if not claim:
            return Response(
                {"detail": "Claim not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"claim": mobile_claim_payload(claim)})

    def delete(self, request, pk):
        try:
            claim_no = ClaimDeleteService.delete(claim_id=pk, user=request.user)
        except ClaimNotFound as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ClaimDeleteForbidden as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ClaimHasJobCard as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({
            "message": f"Claim {claim_no} deleted successfully."
        })


class ClaimSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        if (
            FeatureFlags.is_enabled(BodyShopModule.CLAIMS_V2_FEATURE)
            and MosClaimCreateEndpoint.supports(request.data, pk)
        ):
            result = MosClaimCreateEndpoint().execute(request.user, request.data)
        else:
            result = ClaimService(request.user).save(request.data, pk)

        return Response(result["data"], status=result["status"])
