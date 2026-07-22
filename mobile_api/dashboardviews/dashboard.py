import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..utils.branch_filter import resolve_branch, filter_branch
from ..api_serializers.dashboard_serializer import DashboardSerializer
from ..services.dashboard.dashboard_service import DashboardService

logger = logging.getLogger(__name__)


class NewMobileDashboardView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.debug("Dashboard request params: %s", request.GET.dict())
        user = request.user

        branch = resolve_branch(
            user,
            request.GET.get("branch"),
        )

        data = DashboardService(
            user=user,
            branch=branch,
            period=request.GET.get("period", "today"),
            start_date=request.GET.get("start_date"),
            end_date=request.GET.get("end_date"),
        ).get_dashboard()
        serializer = DashboardSerializer(instance=data)
        return Response(serializer.data)
