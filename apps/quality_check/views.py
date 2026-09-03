import base64
import binascii
from io import BytesIO
from pathlib import Path

from PIL import Image as PillowImage, UnidentifiedImageError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.models import (
    JobCard,
    JobCardQualityCheck,
    Employee,
    QualityCheckEvidencePhoto,
    QualityCheckInspectorSignature,
    QualityCheckItem,
    WorkProgress,
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
    return (
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


def is_quality_inspector(employee):
    if not employee:
        return False
    role_text = " ".join(
        [
            employee.employee_type or "",
            employee.designation or "",
            employee.department or "",
        ]
    ).upper()
    return any(
        keyword in role_text
        for keyword in [
            "QUALITY INSPECTOR",
            "QC INSPECTOR",
            "QUALITY CHECK",
            "QUALITY CONTROL",
        ]
    )


def _qc_dashboard_row(quality_check):
    jobcard = quality_check.jobcard
    vehicle = jobcard.vehicle
    if vehicle is None and jobcard.claim_id:
        vehicle = jobcard.claim.vehicle
    registration = getattr(vehicle, "registration_no", "") or "-"
    inspector_name = "-"
    if quality_check.inspector:
        inspector_name = (
            quality_check.inspector.get_full_name().strip()
            or quality_check.inspector.username
        )
    return {
        "quality_check": quality_check,
        "jobcard": jobcard,
        "registration": registration,
        "inspector_name": inspector_name,
    }


def _pending_qc_dashboard_row(jobcard):
    quality_check = getattr(jobcard, "quality_check", None)
    vehicle = jobcard.vehicle
    if vehicle is None and jobcard.claim_id:
        vehicle = jobcard.claim.vehicle
    return {
        "quality_check": quality_check,
        "jobcard": jobcard,
        "registration": (
            getattr(vehicle, "registration_no", "") or "-"
        ),
        "completed_progress_count": jobcard.completed_progress_count,
    }


@login_required
def quality_inspector_dashboard(request):
    employee = Employee.objects.filter(user=request.user).first()
    if not is_quality_inspector(employee) and not request.user.is_superuser:
        return redirect("dashboard")

    today = timezone.localdate()
    month_start = today.replace(day=1)
    from_date = (
        parse_date(request.GET.get("from_date") or "")
        or month_start
    )
    to_date = parse_date(request.GET.get("to_date") or "") or today
    if to_date < from_date:
        from_date, to_date = to_date, from_date

    active_tab = request.GET.get("tab") or "pending"
    if active_tab not in {"pending", "completed"}:
        active_tab = "pending"
    search = (request.GET.get("search") or "").strip()

    queryset = (
        JobCardQualityCheck.objects
        .select_related(
            "jobcard",
            "jobcard__vehicle",
            "jobcard__claim",
            "jobcard__claim__vehicle",
            "inspector",
        )
        .prefetch_related("items")
    )
    if employee and employee.branch_id:
        queryset = queryset.filter(
            Q(jobcard__branch_id=employee.branch_id)
            | Q(jobcard__claim__branch_id=employee.branch_id)
        )

    eligible_jobs = (
        JobCard.objects
        .select_related(
            "vehicle",
            "claim",
            "claim__vehicle",
            "quality_check",
        )
        .filter(allocation__progress__finish_time__isnull=False)
        .filter(
            Q(quality_check__isnull=True)
            | Q(quality_check__completed=False)
        )
        .annotate(
            completed_progress_count=Count(
                "allocation__progress",
                filter=Q(
                    allocation__progress__finish_time__isnull=False
                ),
                distinct=True,
            )
        )
        .distinct()
    )
    if employee and employee.branch_id:
        eligible_jobs = eligible_jobs.filter(
            Q(branch_id=employee.branch_id)
            | Q(claim__branch_id=employee.branch_id)
        )

    pending_count = eligible_jobs.count()
    completed_month_count = queryset.filter(
        completed=True,
        completed_at__date__gte=month_start,
        completed_at__date__lte=today,
    ).count()

    if active_tab == "completed":
        queryset = queryset.filter(
            completed=True,
            completed_at__date__gte=from_date,
            completed_at__date__lte=to_date,
        ).order_by("-completed_at", "-id")
        if search:
            queryset = queryset.filter(
                Q(jobcard__job_no__icontains=search)
                | Q(jobcard__vehicle__registration_no__icontains=search)
                | Q(
                    jobcard__claim__vehicle__registration_no__icontains=search
                )
            )
        rows = [_qc_dashboard_row(qc) for qc in queryset]
    else:
        if search:
            eligible_jobs = eligible_jobs.filter(
                Q(job_no__icontains=search)
                | Q(vehicle__registration_no__icontains=search)
                | Q(claim__vehicle__registration_no__icontains=search)
            )
        eligible_jobs = eligible_jobs.order_by("job_date", "id")
        rows = [
            _pending_qc_dashboard_row(job)
            for job in eligible_jobs
        ]

    return render(
        request,
        "quality_check/inspector_dashboard.html",
        {
            "employee": employee,
            "active_tab": active_tab,
            "rows": rows,
            "pending_count": pending_count,
            "completed_month_count": completed_month_count,
            "from_date": from_date,
            "to_date": to_date,
            "search": search,
        },
    )


def _update_summary(quality_check, user):
    has_items = quality_check.items.exists()
    has_pending = quality_check.items.filter(
        status=QualityCheckItem.Status.PENDING,
    ).exists()
    quality_check.completed = has_items and not has_pending
    quality_check.inspector = user
    quality_check.completed_at = (
        quality_check.completed_at or timezone.now()
        if quality_check.completed
        else None
    )
    quality_check.save(
        update_fields=[
            "completed",
            "completed_at",
            "inspector",
        ]
    )
    from apps.jobcards.api.quality_check_view import (
        JobCardQualityCheckAPIView,
    )

    JobCardQualityCheckAPIView.update_jobcard_flags(
        quality_check.jobcard,
        quality_check,
    )


def _desktop_qc_action(request, quality_check):
    action = request.POST.get("action", "")

    if action == "update_item":
        item = get_object_or_404(
            quality_check.items,
            pk=request.POST.get("item_id"),
        )
        item_status = request.POST.get("status", "").strip().upper()
        remarks = request.POST.get("remarks", "").strip()
        if item_status not in QualityCheckItem.Status.values:
            messages.error(request, "Select a valid QC status.")
            return
        if item_status == QualityCheckItem.Status.NOT_OK and not remarks:
            messages.error(
                request,
                f"Remarks are required when {item.item_name} is Not OK.",
            )
            return
        item.status = item_status
        item.remarks = remarks
        if item_status == QualityCheckItem.Status.PENDING:
            item.checked_by = None
            item.checked_at = None
        else:
            item.checked_by = request.user
            item.checked_at = timezone.now()
        item.save()
        _update_summary(quality_check, request.user)
        messages.success(request, f"{item.item_name} updated.")

    elif action == "save_remarks":
        quality_check.remarks = request.POST.get("remarks", "").strip()
        quality_check.save(update_fields=["remarks"])
        messages.success(request, "Overall QC remarks saved.")

    elif action == "upload_photos":
        photos = request.FILES.getlist("photos")
        if not photos:
            messages.error(request, "Select at least one evidence photo.")
            return
        if len(photos) > 10:
            messages.error(request, "Upload a maximum of 10 photos at once.")
            return
        caption = request.POST.get("caption", "").strip()[:200]
        valid_photos = []
        for photo in photos:
            if photo.size > 10 * 1024 * 1024:
                messages.error(request, f"{photo.name} exceeds 10 MB.")
                return
            try:
                with PillowImage.open(photo) as image:
                    image.verify()
                    image_format = image.format
            except (UnidentifiedImageError, OSError, ValueError):
                messages.error(request, f"{photo.name} is not a valid image.")
                return
            finally:
                photo.seek(0)
            if image_format not in {"JPEG", "PNG", "WEBP"}:
                messages.error(request, f"{photo.name} is unsupported.")
                return
            valid_photos.append(photo)
        for photo in valid_photos:
            QualityCheckEvidencePhoto.objects.create(
                quality_check=quality_check,
                image=photo,
                caption=caption,
                uploaded_by=request.user,
            )
        messages.success(request, f"{len(valid_photos)} evidence photo(s) uploaded.")

    elif action == "delete_photo":
        photo = get_object_or_404(
            quality_check.evidence_photos,
            pk=request.POST.get("photo_id"),
        )
        photo.image.delete(save=False)
        photo.delete()
        messages.success(request, "Evidence photo deleted.")

    elif action == "add_signature":
        data_url = request.POST.get("signature", "")
        prefix = "data:image/png;base64,"
        if not data_url.startswith(prefix):
            messages.error(request, "Draw the inspector signature first.")
            return
        try:
            image_data = base64.b64decode(
                data_url[len(prefix):],
                validate=True,
            )
        except (ValueError, binascii.Error):
            messages.error(request, "The signature data is invalid.")
            return
        signature = QualityCheckInspectorSignature(
            quality_check=quality_check,
            inspector=request.user,
        )
        filename = (
            f"{quality_check.jobcard.job_no}_qc_"
            f"{request.user.pk}_{timezone.now():%Y%m%d%H%M%S}.png"
        ).replace("/", "_")
        signature.image.save(
            filename,
            ContentFile(image_data),
            save=True,
        )
        quality_check.inspector = request.user
        quality_check.save(update_fields=["inspector"])
        messages.success(request, "Inspector signature added.")

    elif action == "delete_signature":
        signature = get_object_or_404(
            quality_check.inspector_signatures,
            pk=request.POST.get("signature_id"),
        )
        signature.image.delete(save=False)
        signature.delete()
        messages.success(request, "Inspector signature deleted.")


@login_required
def quality_check_detail(request, jobcard_id):
    employee = Employee.objects.filter(user=request.user).first()
    if (
        is_quality_inspector(employee)
        and not JobCardQualityCheck.objects.filter(
            jobcard_id=jobcard_id,
        ).exists()
        and not WorkProgress.objects.filter(
            allocation__job_id=jobcard_id,
            finish_time__isnull=False,
        ).exists()
    ):
        messages.error(
            request,
            "QC can start after at least one work progress is completed.",
        )
        return redirect("quality_inspector_dashboard")

    quality_check = get_quality_check(jobcard_id)
    if request.method == "POST":
        _desktop_qc_action(request, quality_check)
        return redirect("quality_check_detail", jobcard_id=jobcard_id)
    return render(
        request,
        "quality_check/detail.html",
        {"quality_check": quality_check},
    )


def _safe_image(path, width, height):
    if not path or not Path(path).exists():
        return None
    source_width, source_height = ImageReader(path).getSize()
    scale = min(width / source_width, height / source_height)
    image = Image(
        path,
        width=source_width * scale,
        height=source_height * scale,
    )
    image.hAlign = "LEFT"
    return image


@login_required
def quality_check_report(request, jobcard_id):
    quality_check = get_quality_check(jobcard_id)
    jobcard = quality_check.jobcard
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=f"Quality Check Report - {jobcard.job_no}",
        author="MasterApp Bodyshop",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="QCHeading",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#17324D"),
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="QCSection",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=5 * mm,
            spaceAfter=2.5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="QCCaption",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
        )
    )

    story = [
        Paragraph("FINAL QUALITY CHECK REPORT", styles["QCHeading"]),
        Paragraph(
            "Inspection evidence and release record",
            styles["Normal"],
        ),
        Spacer(1, 5 * mm),
    ]

    vehicle = getattr(jobcard, "vehicle", None)
    registration = (
        getattr(vehicle, "registration_no", "")
        or getattr(jobcard, "registration_no", "")
        or "-"
    )
    inspector = "-"
    if quality_check.inspector:
        inspector = (
            quality_check.inspector.get_full_name().strip()
            or quality_check.inspector.username
        )
    result_color = {
        "OK": colors.HexColor("#15803D"),
        "NOT_OK": colors.HexColor("#B91C1C"),
        "PENDING": colors.HexColor("#B45309"),
    }[quality_check.result]
    summary = Table(
        [
            ["Job Card", jobcard.job_no, "Registration", registration],
            ["Inspector", inspector, "Result", quality_check.result],
            [
                "Completed",
                "Yes" if quality_check.completed else "No",
                "Completion",
                f"{quality_check.completion_percentage:.0f}%",
            ],
        ],
        colWidths=[28 * mm, 59 * mm, 28 * mm, 59 * mm],
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF5")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E8EEF5")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (3, 1), (3, 1), result_color),
                ("FONTNAME", (3, 1), (3, 1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([summary, Paragraph("Inspection Checklist", styles["QCSection"])])

    item_rows = [["#", "Inspection Item", "Category", "Status", "Remarks"]]
    for index, item in enumerate(quality_check.items.all(), start=1):
        item_rows.append(
            [
                str(index),
                Paragraph(item.item_name, styles["BodyText"]),
                Paragraph(item.category or "-", styles["BodyText"]),
                item.get_status_display(),
                Paragraph(item.remarks or "-", styles["BodyText"]),
            ]
        )
    item_table = Table(
        item_rows,
        repeatRows=1,
        colWidths=[9 * mm, 48 * mm, 38 * mm, 20 * mm, 59 * mm],
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(item_table)
    story.extend(
        [
            Paragraph("Overall Remarks", styles["QCSection"]),
            Paragraph(quality_check.remarks or "No overall remarks.", styles["BodyText"]),
        ]
    )

    photos = list(quality_check.evidence_photos.all())
    if photos:
        story.extend([PageBreak(), Paragraph("Evidence Photos", styles["QCHeading"])])
        photo_cells = []
        for photo in photos:
            image = _safe_image(photo.image.path, 78 * mm, 53 * mm)
            if image:
                photo_cells.append(
                    [
                        image,
                        Spacer(1, 1.5 * mm),
                        Paragraph(
                            photo.caption or "QC evidence",
                            styles["QCCaption"],
                        ),
                    ]
                )
        photo_rows = [
            photo_cells[index:index + 2]
            for index in range(0, len(photo_cells), 2)
        ]
        if photo_rows:
            if len(photo_rows[-1]) == 1:
                photo_rows[-1].append("")
            photo_table = Table(
                photo_rows,
                colWidths=[86 * mm, 86 * mm],
                hAlign="LEFT",
            )
            photo_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                    ]
                )
            )
            story.append(photo_table)

    story.extend([Spacer(1, 8 * mm), Paragraph("Inspector Approvals", styles["QCSection"])])
    signature_rows = []
    for approval in quality_check.inspector_signatures.all():
        approval_name = "-"
        if approval.inspector:
            approval_name = (
                approval.inspector.get_full_name().strip()
                or approval.inspector.username
            )
        signature_rows.append(
            [
                _safe_image(approval.image.path, 55 * mm, 22 * mm),
                Paragraph(
                    f"<b>{approval_name}</b><br/>"
                    f"Signed {approval.signed_at:%d %b %Y %H:%M}",
                    styles["BodyText"],
                ),
            ]
        )
    if not signature_rows:
        legacy_signature = (
            _safe_image(
                quality_check.inspector_signature.path,
                55 * mm,
                22 * mm,
            )
            if quality_check.inspector_signature
            else None
        )
        signature_rows.append(
            [
                legacy_signature
                or Paragraph("Signature not captured", styles["BodyText"]),
                Paragraph(f"<b>{inspector}</b><br/>Inspector", styles["BodyText"]),
            ]
        )
    signature_table = Table(
        signature_rows,
        colWidths=[75 * mm, 99 * mm],
    )
    signature_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (0, -1), 0.7, colors.HexColor("#64748B")),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    story.append(signature_table)

    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(16 * mm, 9 * mm, f"QC Report - {jobcard.job_no}")
        canvas.drawRightString(
            A4[0] - 16 * mm,
            9 * mm,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    disposition = (
        "attachment"
        if request.GET.get("download") == "1"
        else "inline"
    )
    response["Content-Disposition"] = (
        f'{disposition}; filename="QC_Report_{jobcard.job_no}.pdf"'
    )
    return response
