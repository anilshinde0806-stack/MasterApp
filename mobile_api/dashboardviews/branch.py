from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..api_serializers.branch_serializer import BranchSerializer
from core.models import Branch

class MobileBranchListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        employee = request.user.employee
        employee_type = (employee.employee_type or "").upper()

        if request.user.is_superuser or employee_type == "ADMIN":

            serializer = BranchSerializer(
                Branch.objects.filter(is_active=True),
                many=True,
            )

            return Response({
                "selected": "all",
                "can_change_branch": True,
                "branches": [
                    {
                        "id": "all",
                        "name": "All Branches",
                        "code": "ALL",
                        "is_head_office": False,
                    },
                    *serializer.data,
                ],
            })

        serializer = BranchSerializer(employee.branch)

        return Response({
            "selected": employee.branch.id,
            "can_change_branch": False,
            "branches": [serializer.data],
        })