from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.services.user_context import user_payload
from apps.navigation.services.menu_service import allowed_menus_for_user, build_menu_tree
from core.models import Employee
from mobile_api.serializers import MobileLoginSerializer


class MobileLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = MobileLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_payload(user),
            }
        )


class MobileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": user_payload(request.user)})


class MobileProfilePhotoUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        employee = Employee.objects.filter(user=request.user).first()
        if not employee:
            return Response(
                {"errors": {"profilePhoto": "Employee profile not found."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image = request.FILES.get("profile_photo")
        if not image:
            return Response(
                {"errors": {"profilePhoto": "Select profile photo."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if employee.profile_photo:
            employee.profile_photo.delete(save=False)
        employee.profile_photo = image
        employee.save(update_fields=["profile_photo"])
        return Response(
            {
                "message": "Profile photo updated successfully.",
                "user": user_payload(request.user),
            }
        )


class MobileMenuView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        menus = allowed_menus_for_user(request.user)
        return Response({"menus": build_menu_tree(menus)})
