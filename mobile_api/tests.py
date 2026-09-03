from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import signing
from django.test import override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
import base64
import tempfile

from django.test import TestCase

from apps.jobcards.api.quality_check_view import (
    JobCardQualityCheckAPIView,
)
from apps.jobcards.api.quality_check_evidence_view import (
    QualityCheckEvidenceAPIView,
    QualityCheckSignatureAPIView,
    MobileQualityCheckReportAPIView,
)
from core.models import (
    JobCard,
    QualityCheckEvidencePhoto,
    QualityCheckItem,
)


class JobCardQualityCheckAPIViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="qc-inspector",
            password="test-password",
        )
        self.jobcard = JobCard.objects.create(
            job_no="TEST-QC-001",
        )
        self.factory = APIRequestFactory()
        self.view = JobCardQualityCheckAPIView.as_view()

    def patch(self, payload):
        request = self.factory.patch(
            "/api/mobile/jobcards/"
            f"{self.jobcard.pk}/quality-check/",
            payload,
            format="json",
        )
        force_authenticate(request, user=self.user)
        return self.view(
            request,
            jobcard_id=self.jobcard.pk,
        )

    def test_accepts_legacy_bulk_boolean_payload(self):
        response = self.patch(
            {
                "paint_finish": True,
                "color_match": False,
                "remarks": "Legacy mobile save",
                "completed": False,
            }
        )

        self.assertEqual(response.status_code, 200)

        quality_check = self.jobcard.quality_check
        paint_finish = quality_check.items.get(
            item_key="paint_finish",
        )
        color_match = quality_check.items.get(
            item_key="color_match",
        )

        self.assertEqual(
            paint_finish.status,
            QualityCheckItem.Status.OK,
        )
        self.assertEqual(paint_finish.checked_by, self.user)
        self.assertEqual(
            color_match.status,
            QualityCheckItem.Status.PENDING,
        )
        self.assertEqual(
            quality_check.remarks,
            "Legacy mobile save",
        )

    def test_item_payload_still_requires_item_id(self):
        response = self.patch(
            {
                "status": "OK",
                "remarks": "",
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {
                "item_id": [
                    "Quality-check item ID is required."
                ]
            },
        )

    def test_rejects_non_boolean_legacy_values(self):
        response = self.patch(
            {
                "paint_finish": "true",
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {
                "paint_finish": [
                    "This field must be a boolean."
                ]
            },
        )

    def test_bulk_save_preserves_not_ok_item_and_remarks(self):
        initial_response = self.patch(
            {
                "paint_finish": False,
            }
        )
        self.assertEqual(initial_response.status_code, 200)

        quality_check = self.jobcard.quality_check
        failed_item = quality_check.items.get(
            item_key="paint_finish",
        )
        failed_item.status = QualityCheckItem.Status.NOT_OK
        failed_item.remarks = "Paint defect remains"
        failed_item.checked_by = self.user
        failed_item.save()

        response = self.patch(
            {
                "paint_finish": False,
                "remarks": "Recheck after polishing",
            }
        )

        self.assertEqual(response.status_code, 200)

        failed_item.refresh_from_db()
        quality_check.refresh_from_db()

        self.assertEqual(
            failed_item.status,
            QualityCheckItem.Status.NOT_OK,
        )
        self.assertEqual(
            failed_item.remarks,
            "Paint defect remains",
        )
        self.assertEqual(
            quality_check.remarks,
            "Recheck after polishing",
        )
        self.assertEqual(
            response.data["summary"]["remarks"],
            "Recheck after polishing",
        )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class QualityCheckEvidenceAPIViewTests(TestCase):
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
        "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="qc-photo-inspector",
            password="test-password",
        )
        self.jobcard = JobCard.objects.create(job_no="TEST-QC-PHOTO")
        self.factory = APIRequestFactory()

    def test_uploads_evidence_and_returns_thumbnail_url(self):
        photo = SimpleUploadedFile(
            "evidence.png",
            self.png_bytes,
            content_type="image/png",
        )
        request = self.factory.post(
            "/evidence/",
            {"photos": photo, "caption": "Paint finish"},
            format="multipart",
        )
        force_authenticate(request, user=self.user)
        response = QualityCheckEvidenceAPIView.as_view()(
            request,
            jobcard_id=self.jobcard.pk,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(QualityCheckEvidencePhoto.objects.count(), 1)
        self.assertEqual(
            response.data["evidence_photos"][0]["caption"],
            "Paint finish",
        )

    def test_accepts_camera_photo_with_generic_content_type(self):
        photo = SimpleUploadedFile(
            "camera_capture.png",
            self.png_bytes,
            content_type="application/octet-stream",
        )
        request = self.factory.post(
            "/evidence/",
            {"photos": photo},
            format="multipart",
        )
        force_authenticate(request, user=self.user)
        response = QualityCheckEvidenceAPIView.as_view()(
            request,
            jobcard_id=self.jobcard.pk,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(QualityCheckEvidencePhoto.objects.count(), 1)

    def test_saves_inspector_signature(self):
        request = self.factory.post(
            "/signature/",
            {
                "signature": (
                    "data:image/png;base64,"
                    + base64.b64encode(self.png_bytes).decode("ascii")
                )
            },
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = QualityCheckSignatureAPIView.as_view()(
            request,
            jobcard_id=self.jobcard.pk,
        )

        self.assertEqual(response.status_code, 200)
        quality_check = self.jobcard.quality_check
        self.assertEqual(quality_check.inspector_signatures.count(), 1)
        self.assertTrue(response.data["inspector_signature_url"])
        self.assertEqual(len(response.data["inspector_signatures"]), 1)

        second_request = self.factory.post(
            "/signature/",
            {
                "signature": (
                    "data:image/png;base64,"
                    + base64.b64encode(self.png_bytes).decode("ascii")
                )
            },
            format="json",
        )
        force_authenticate(second_request, user=self.user)
        second_response = QualityCheckSignatureAPIView.as_view()(
            second_request,
            jobcard_id=self.jobcard.pk,
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(quality_check.inspector_signatures.count(), 2)
        self.assertEqual(
            len(second_response.data["inspector_signatures"]),
            2,
        )

    def test_signed_mobile_report_opens_without_browser_session(self):
        initial_request = self.factory.post(
            "/evidence/",
            {
                "photos": SimpleUploadedFile(
                    "evidence.png",
                    self.png_bytes,
                    content_type="image/png",
                )
            },
            format="multipart",
        )
        force_authenticate(initial_request, user=self.user)
        QualityCheckEvidenceAPIView.as_view()(
            initial_request,
            jobcard_id=self.jobcard.pk,
        )
        token = signing.dumps(
            self.jobcard.pk,
            salt="mobile-quality-check-report",
        )
        request = self.factory.get(
            f"/report/?token={token}",
        )
        response = MobileQualityCheckReportAPIView.as_view()(
            request,
            jobcard_id=self.jobcard.pk,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/pdf",
        )
