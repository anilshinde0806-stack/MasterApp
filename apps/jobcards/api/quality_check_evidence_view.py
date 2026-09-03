import base64
import binascii
from PIL import Image, UnidentifiedImageError

from django.core.files.base import ContentFile
from django.core import signing
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    JobCard,
    JobCardQualityCheck,
    QualityCheckEvidencePhoto,
    QualityCheckInspectorSignature,
)
from mobile_api.api_serializers.quality_check_serializer import (
    JobCardQualityCheckResponseSerializer,
)
from apps.quality_check.services.quality_check_items import (
    ensure_quality_check_items,
)


def get_quality_check(jobcard_id):
    jobcard = get_object_or_404(JobCard, pk=jobcard_id)
    quality_check, _ = JobCardQualityCheck.objects.get_or_create(
        jobcard=jobcard,
    )
    ensure_quality_check_items(quality_check)
    return quality_check


def response_payload(request, quality_check, message):
    quality_check = (
        JobCardQualityCheck.objects
        .select_related("jobcard", "inspector")
        .prefetch_related(
            "items",
            "items__checked_by",
            "evidence_photos",
            "inspector_signatures__inspector",
        )
        .get(pk=quality_check.pk)
    )
    serializer = JobCardQualityCheckResponseSerializer(
        quality_check,
        context={"request": request},
    )
    return {"message": message, **serializer.data}


class QualityCheckEvidenceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, jobcard_id):
        quality_check = get_quality_check(jobcard_id)
        images = request.FILES.getlist("photos")

        if not images:
            return Response(
                {"photos": ["Select at least one evidence photo."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(images) > 10:
            return Response(
                {"photos": ["A maximum of 10 photos can be uploaded at once."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for image in images:
            if image.size > 10 * 1024 * 1024:
                return Response(
                    {"photos": [f"{image.name} exceeds the 10 MB limit."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                with Image.open(image) as uploaded_image:
                    uploaded_image.verify()
                    image_format = uploaded_image.format
            except (UnidentifiedImageError, OSError, ValueError):
                return Response(
                    {"photos": [f"{image.name} is not a supported image."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            finally:
                image.seek(0)

            if image_format not in {"JPEG", "PNG", "WEBP"}:
                return Response(
                    {"photos": [f"{image.name} is not a supported image."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        caption = str(request.data.get("caption", "")).strip()[:200]
        QualityCheckEvidencePhoto.objects.bulk_create(
            [
                QualityCheckEvidencePhoto(
                    quality_check=quality_check,
                    image=image,
                    caption=caption,
                    uploaded_by=request.user,
                )
                for image in images
            ]
        )
        return Response(
            response_payload(
                request,
                quality_check,
                "Evidence photos uploaded successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


class QualityCheckEvidenceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, jobcard_id, photo_id):
        quality_check = get_quality_check(jobcard_id)
        photo = get_object_or_404(
            QualityCheckEvidencePhoto,
            pk=photo_id,
            quality_check=quality_check,
        )
        photo.image.delete(save=False)
        photo.delete()
        return Response(
            response_payload(
                request,
                quality_check,
                "Evidence photo deleted successfully.",
            )
        )


class QualityCheckSignatureAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, jobcard_id):
        quality_check = get_quality_check(jobcard_id)
        data_url = str(request.data.get("signature", "")).strip()

        if data_url == "__clear__":
            for signature in quality_check.inspector_signatures.all():
                signature.image.delete(save=False)
            quality_check.inspector_signatures.all().delete()
            if quality_check.inspector_signature:
                quality_check.inspector_signature.delete(save=False)
            quality_check.inspector_signature = None
            quality_check.save(update_fields=["inspector_signature"])
        else:
            prefix = "data:image/png;base64,"
            if not data_url.startswith(prefix):
                return Response(
                    {"signature": ["A PNG signature is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                image_data = base64.b64decode(
                    data_url[len(prefix):],
                    validate=True,
                )
            except (ValueError, binascii.Error):
                return Response(
                    {"signature": ["The signature data is invalid."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(image_data) > 2 * 1024 * 1024:
                return Response(
                    {"signature": ["The signature exceeds the 2 MB limit."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            filename = (
                f"{quality_check.jobcard.job_no}_qc_"
                f"{request.user.pk}.png"
            ).replace("/", "_")
            signature = QualityCheckInspectorSignature(
                quality_check=quality_check,
                inspector=request.user,
            )
            signature.image.save(
                filename,
                ContentFile(image_data),
                save=True,
            )
            quality_check.inspector = request.user
            quality_check.save(update_fields=["inspector"])

        return Response(
            response_payload(
                request,
                quality_check,
                "Inspector signature saved successfully.",
            )
        )

    def delete(self, request, jobcard_id):
        quality_check = get_quality_check(jobcard_id)
        signature_id = request.data.get("signature_id")
        signature = get_object_or_404(
            QualityCheckInspectorSignature,
            pk=signature_id,
            quality_check=quality_check,
        )
        signature.image.delete(save=False)
        signature.delete()
        return Response(
            response_payload(
                request,
                quality_check,
                "Inspector signature deleted successfully.",
            )
        )


class MobileQualityCheckReportAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, jobcard_id):
        from apps.quality_check.views import quality_check_report

        token = request.query_params.get("token", "")
        try:
            signed_jobcard_id = signing.loads(
                token,
                salt="mobile-quality-check-report",
                max_age=24 * 60 * 60,
            )
        except signing.BadSignature:
            return Response(
                {"detail": "The report link is invalid or expired."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if signed_jobcard_id != jobcard_id:
            return Response(
                {"detail": "The report link is invalid."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return quality_check_report.__wrapped__(
            request._request,
            jobcard_id,
        )
