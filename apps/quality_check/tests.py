import base64
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import (
    JobCard,
    Employee,
    JobCardQualityCheck,
    QualityCheckEvidencePhoto,
    QualityCheckInspectorSignature,
    QualityCheckItem,
    WorkAllocation,
    WorkProgress,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DesktopQualityCheckTests(TestCase):
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
        "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="desktop-qc",
            password="test-password",
        )
        self.jobcard = JobCard.objects.create(job_no="DESKTOP-QC-001")
        self.client.force_login(self.user)
        self.url = reverse(
            "quality_check_detail",
            args=[self.jobcard.pk],
        )

    def test_desktop_page_creates_and_displays_checklist(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Desktop Quality Check")
        self.assertEqual(
            self.jobcard.quality_check.items.count(),
            15,
        )

    def test_desktop_updates_item_and_overall_remarks(self):
        self.client.get(self.url)
        item = self.jobcard.quality_check.items.first()

        response = self.client.post(
            self.url,
            {
                "action": "update_item",
                "item_id": item.pk,
                "status": "NOT_OK",
                "remarks": "Requires correction",
            },
        )
        self.assertRedirects(response, self.url)
        item.refresh_from_db()
        self.assertEqual(item.status, QualityCheckItem.Status.NOT_OK)
        self.assertEqual(item.checked_by, self.user)

        self.client.post(
            self.url,
            {
                "action": "save_remarks",
                "remarks": "Desktop final remarks",
            },
        )
        self.jobcard.quality_check.refresh_from_db()
        self.assertEqual(
            self.jobcard.quality_check.remarks,
            "Desktop final remarks",
        )

    def test_desktop_uploads_photo_and_adds_signature(self):
        response = self.client.post(
            self.url,
            {
                "action": "upload_photos",
                "photos": SimpleUploadedFile(
                    "desktop.png",
                    self.png_bytes,
                    content_type="application/octet-stream",
                ),
                "caption": "Desktop evidence",
            },
        )
        self.assertRedirects(response, self.url)
        self.assertEqual(QualityCheckEvidencePhoto.objects.count(), 1)

        signature = (
            "data:image/png;base64,"
            + base64.b64encode(self.png_bytes).decode("ascii")
        )
        response = self.client.post(
            self.url,
            {
                "action": "add_signature",
                "signature": signature,
            },
        )
        self.assertRedirects(response, self.url)
        self.assertEqual(
            QualityCheckInspectorSignature.objects.count(),
            1,
        )


class QualityInspectorDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="quality-inspector",
            password="test-password",
        )
        self.employee = Employee.objects.create(
            user=self.user,
            name="Quality Inspector",
            employee_code="QC-INS-001",
            employee_type="Quality Inspector",
        )
        self.pending_job = JobCard.objects.create(
            job_no="QC-PENDING-001",
        )
        self.completed_job = JobCard.objects.create(
            job_no="QC-COMPLETE-001",
        )
        self.unstarted_qc_job = JobCard.objects.create(
            job_no="QC-READY-TO-START",
        )
        self.ineligible_job = JobCard.objects.create(
            job_no="QC-NO-COMPLETED-PROGRESS",
        )
        self.pending_qc = JobCardQualityCheck.objects.create(
            jobcard=self.pending_job,
            completed=False,
        )
        self.completed_qc = JobCardQualityCheck.objects.create(
            jobcard=self.completed_job,
            completed=True,
            completed_at=timezone.now(),
            inspector=self.user,
        )
        for job in [self.pending_job, self.unstarted_qc_job]:
            allocation = WorkAllocation.objects.create(job=job)
            WorkProgress.objects.create(
                allocation=allocation,
                stage="Repair",
                start_time=timezone.now(),
                finish_time=timezone.now(),
            )
        ineligible_allocation = WorkAllocation.objects.create(
            job=self.ineligible_job,
        )
        WorkProgress.objects.create(
            allocation=ineligible_allocation,
            stage="Repair",
            start_time=timezone.now(),
            finish_time=None,
        )
        self.client.force_login(self.user)
        self.url = reverse("quality_inspector_dashboard")

    def test_dashboard_is_quality_inspector_homepage(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, self.url)

    def test_pending_and_current_month_completed_tabs(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QC-PENDING-001")
        self.assertContains(response, "QC-READY-TO-START")
        self.assertContains(response, "Start QC")
        self.assertContains(response, "Continue QC")
        self.assertNotContains(
            response,
            "QC-NO-COMPLETED-PROGRESS",
        )
        self.assertNotContains(response, "QC-COMPLETE-001")

        response = self.client.get(
            self.url,
            {"tab": "completed"},
        )
        self.assertContains(response, "QC-COMPLETE-001")
        self.assertNotContains(response, "QC-PENDING-001")
        self.assertContains(response, "Download Report")

    def test_start_qc_creates_checklist_for_eligible_job(self):
        self.assertFalse(
            JobCardQualityCheck.objects.filter(
                jobcard=self.unstarted_qc_job,
            ).exists()
        )

        response = self.client.get(
            reverse(
                "quality_check_detail",
                args=[self.unstarted_qc_job.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        quality_check = JobCardQualityCheck.objects.get(
            jobcard=self.unstarted_qc_job,
        )
        self.assertEqual(quality_check.items.count(), 15)

    def test_start_qc_rejects_job_without_completed_progress(self):
        response = self.client.get(
            reverse(
                "quality_check_detail",
                args=[self.ineligible_job.pk],
            )
        )

        self.assertRedirects(response, self.url)
        self.assertFalse(
            JobCardQualityCheck.objects.filter(
                jobcard=self.ineligible_job,
            ).exists()
        )

    def test_report_download_uses_attachment_disposition(self):
        response = self.client.get(
            reverse(
                "quality_check_report",
                args=[self.completed_job.pk],
            ),
            {"download": "1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response["Content-Disposition"].startswith("attachment;")
        )
