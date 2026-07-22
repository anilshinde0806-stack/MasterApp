import base64
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse

from apps.common.utils.parser_utils import clean_text
from apps.jobcards.constants import VEHICLE_CONDITION_PHOTO_CAPTIONS
from core.models import (
    Claim,
    ClaimStageCode,
    Employee,
    JobCardTyreInventory,
    WorkProgress,
    WorkProgressPhoto,
)


def save_mobile_signature_data(job, field_name, data_url):
    data_url = clean_text(data_url)
    if not data_url:
        return False

    field = getattr(job, field_name)
    if data_url == "__clear__":
        if field:
            field.delete(save=False)
        setattr(job, field_name, None)
        return True

    if not data_url.startswith("data:image/png;base64,"):
        return False

    try:
        image_data = base64.b64decode(data_url.split(",", 1)[1])
    except (ValueError, IndexError):
        return False

    if field:
        field.delete(save=False)

    filename = f"{job.job_no}_{field_name}.png".replace("/", "_")
    setattr(job, field_name, ContentFile(image_data, name=filename))
    return True

def mobile_jobcard_payload(job, request=None):
    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    stage_lookup = dict(Claim.CLAIM_STAGES)
    inventory = getattr(job, "inventory", None)
    allocation = getattr(job, "allocation", None)
    progress_list = (
        list(allocation.progress.order_by("id"))
        if allocation
        else []
    )

    current_progress = (
        progress_list[-1]
        if progress_list
        else None
    )
    assigned_employee_names = list(dict.fromkeys(
        item.employee.name
        for item in progress_list
        if item.employee_id
    ))
    job_branch = job.branch if job.branch_id else (claim.branch if claim and claim.branch_id else None)
    work_completed = (
        job.repair_status in ["Completed", "Closed"]
        or (claim and int(claim.claim_stage or 0) >= ClaimStageCode.WORK_COMPLETED)
    )
    ri_done = bool(job.reinspection_done) or (
        claim and int(claim.claim_stage or 0) >= ClaimStageCode.LIABILITY
    )
    close_ready = {
        "work_completed": bool(work_completed),
        "qc_done": bool(job.qc_done),
        "ri_done": bool(ri_done),
        "part_entry_complete": bool(allocation and allocation.part_entry_complete),
    }

    progress_photos = []

    photos = (
        WorkProgressPhoto.objects
        .filter(progress__allocation__job=job)
        .select_related(
            "progress",
            "progress__employee",
        )
        .order_by(
            "progress__stage",
            "-uploaded_at",
        )
    )

    for photo in photos:

        image_url = ""

        if photo.image:
            if request:
                image_url = request.build_absolute_uri(
                    photo.image.url
                )
            else:
                image_url = photo.image.url

        progress_photos.append({

            "id": photo.id,

            "image": image_url,

            "stage": photo.progress.stage,

            "stage_label": photo.progress.get_stage_display(),

            "employee": (
                photo.progress.employee.name
                if photo.progress.employee
                else ""
            ),

            "employee_id": photo.progress.employee_id,

            "remarks": photo.progress.remarks or "",

            "status": (
                "Completed"
                if photo.progress.finish_time
                else "Started"
                if photo.progress.start_time
                else "Pending"
            ),

            "started_at": (
                photo.progress.start_time.strftime("%d-%m-%Y %I:%M %p")
                if photo.progress.start_time
                else ""
            ),

            "completed_at": (
                photo.progress.finish_time.strftime("%d-%m-%Y %I:%M %p")
                if photo.progress.finish_time
                else ""
            ),

            "uploaded_at": photo.uploaded_at.strftime(
                "%d-%m-%Y %I:%M %p"
            ),
            "job_no": job.job_no,

            "registration_no": (
                job.claim.vehicle.registration_no
                if job.claim and job.claim.vehicle
                else ""
            ),
        })
    return {
        "id": job.id,
        "claim": claim.id if claim else "",
        "claim_no": claim.claim_no if claim else "",
        "ic_claim_no": claim.ic_claim_no if claim else "",
        "claim_stage": claim.claim_stage if claim else "",
        "claim_stage_label": stage_lookup.get(claim.claim_stage, "") if claim else "",
        "job_no": job.job_no,
        "job_date": job.job_date.isoformat(sep=" ", timespec="minutes") if job.job_date else "",
        "registration_no": vehicle.registration_no if vehicle else "",
        "customer": customer.name if customer else "",
        "model": str(vehicle.model) if vehicle and vehicle.model_id else "",
        "variant": vehicle.variant.name if vehicle and vehicle.variant_id else "",
        "advisor": job.advisor_id or "",
        "advisor_name": job.advisor.name if job.advisor_id else "",
        "branch": job_branch.id if job_branch else "",
        "branch_name": job_branch.name if job_branch else "",
        "technician_name": ", ".join(assigned_employee_names),
        "vehicle_inward_type": job.vehicle_inward_type or "",
        "vehicle_inward_by": job.vehicle_inward_by or "",
        "gate_in_datetime": job.gate_in_datetime.isoformat(sep=" ", timespec="minutes") if job.gate_in_datetime else "",
        "expected_delivery_datetime": job.expected_delivery_datetime.isoformat(sep=" ", timespec="minutes") if job.expected_delivery_datetime else "",
        "km": job.km or "",
        "fuel_level": job.fuel_level or "",
        "part_order_date": job.part_order_date.isoformat() if job.part_order_date else "",
        "part_order_no": job.part_order_no or "",
        "repair_status": job.repair_status or "",
        # -----------------------------
        # Workshop Workflow
        # -----------------------------

        "has_allocation": allocation is not None,

        "work_started": len(progress_list) > 0,
        "progress_photos": progress_photos,
        "progress_count": len(progress_list),
        "allocations": [
            {
                "id": item.id,
                "stage": item.stage,
                "stage_label": item.get_stage_display(),
                "employee_id": item.employee_id or "",
                "employee_name": item.employee.name if item.employee_id else "",
                "status": (
                    "Completed"
                    if item.finish_time
                    else "Started"
                    if item.start_time
                    else "Pending"
                ),
                "remarks": item.remarks or "",
                "started_at": item.start_time.isoformat(timespec="minutes") if item.start_time else "",
                "completed_at": item.finish_time.isoformat(timespec="minutes") if item.finish_time else "",
            }
            for item in progress_list
        ],
        "priority": job.priority if hasattr(job, "priority") else "Normal",
        "estimated_time": getattr(job, "estimated_time", "") or "",
        "current_stage": (
            current_progress.stage
            if current_progress
            else "Pending Allocation"
            if allocation is None
            else "Work Not Started"
        ),

        "current_stage_label": (
            current_progress.get_stage_display()
            if current_progress
            else "Pending Allocation"
            if allocation is None
            else "Work Not Started"
        ),
        "estimated_delivery": job.estimated_delivery.isoformat(sep=" ", timespec="minutes") if job.estimated_delivery else "",
        "actual_delivery": job.actual_delivery.isoformat(sep=" ", timespec="minutes") if job.actual_delivery else "",
        "repair_instructions": job.repair_instructions or "",
        "road_test_done": job.road_test_done,
        "washing_done": job.washing_done,
        "ready_for_delivery": job.ready_for_delivery,
        "additional_approval_required": job.additional_approval_required,
        "second_approval_status": job.second_approval_status or "",
        "additional_approval_reason": job.additional_approval_reason or "",
        "advisor_signature_url": job.advisor_signature.url if job.advisor_signature else "",
        "customer_signature_url": job.customer_signature.url if job.customer_signature else "",
        "qc_done": job.qc_done,
        "reinspection_done": job.reinspection_done,
        "reinspection_date": job.reinspection_date.isoformat(sep=" ", timespec="minutes") if job.reinspection_date else "",
        "reinspection_done_by": job.reinspection_done_by or "",
        "parts_total": float(job.parts_total or 0),
        "labour_total": float(job.labour_total or 0),
        "grand_total": float(job.grand_total or 0),
        "close_ready": close_ready,
        "close_pending": [
            label
            for key, label in {
                "work_completed": "Work Completed",
                "qc_done": "QC Done",
                "ri_done": "RI Done",
                "part_entry_complete": "Part Entry Complete",
            }.items()
            if not close_ready[key]
        ],
        "inventory": {
            "mud_flap_count": inventory.mud_flap_count if inventory else 0,
            "floor_mat_count": inventory.floor_mat_count if inventory else 0,
            "lh_mirror": bool(inventory and inventory.lh_mirror),
            "rh_mirror": bool(inventory and inventory.rh_mirror),
            "center_mirror": bool(inventory and inventory.center_mirror),
            "frt_wiper": bool(inventory and inventory.frt_wiper),
            "rr_wiper": bool(inventory and inventory.rr_wiper),
            "accessories": bool(inventory and inventory.accessories),
            "spare_wheel": bool(inventory and inventory.spare_wheel),
            "jack": bool(inventory and inventory.jack),
            "tool_kit": bool(inventory and inventory.tool_kit),
            "stereo": bool(inventory and inventory.stereo),
            "battery": bool(inventory and inventory.battery),
            "number_plate": bool(inventory and inventory.number_plate),
            "fuel_percent": inventory.fuel_percent if inventory else 0,
            "cng_percent": inventory.cng_percent if inventory else 0,
            "damage_marks": inventory.damage_marks if inventory else [],
            "remarks": inventory.remarks if inventory else "",
        },
        "tyres": [
            {
                "position": tyre.position,
                "label": dict(JobCardTyreInventory.POSITION_CHOICES).get(tyre.position, tyre.position),
                "make": tyre.make,
                "size": tyre.size,
                "depth": float(tyre.depth or 0),
                "wheel_cap": tyre.wheel_cap,
            }
            for tyre in job.tyres.all().order_by("id")
        ],
        "vehicle_condition_photos": [
            {
                "index": index,
                "caption": caption,
                "id": photo.id if photo else "",
                "url": photo.image.url if photo and photo.image else "",
                "uploaded_at": photo.uploaded_at.isoformat(sep=" ", timespec="minutes") if photo else "",
            }
            for index, caption in enumerate(VEHICLE_CONDITION_PHOTO_CAPTIONS, start=1)
            for photo in [
                next(
                    (
                        item
                        for item in job.vehicle_condition_photos.all()
                        if item.caption == caption
                    ),
                    None,
                )
            ]
        ],
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "actions": mobile_jobcard_action_payload(None, job),
        "parts": [
            {
                "id": part.id,
                "part_no": part.part_no,
                "description": part.description,
                "qty": part.qty,
                "rate": float(part.rate or 0),
                "amount": float(part.amount or 0),
            }
            for part in job.parts.all().order_by("id")
        ],
        "labours": [
            {
                "id": labour.id,
                "job_code": labour.job_code,
                "description": labour.description,
                "labour_hrs": float(labour.labour_hrs or 0),
                "rate": float(labour.rate or 0),
                "amount": float(labour.amount or 0),
                "paint_panel_type": labour.paint_panel_type or "",
            }
            for labour in job.labours.all().order_by("id")
        ],
    }

def mobile_stage_list():
    return [
        {
            "value": value,
            "label": label,
        }
        for value, label in WorkProgress.STAGES
    ]

def mobile_employee_list():
    return [
        {
            "id": emp.id,
            "name": emp.name,
        }
        for emp in Employee.objects.filter(
            is_active=True
        ).order_by("name")
    ]

def mobile_jobcard_action_payload(request, job):
    pdf_path = reverse("jobcard_print", args=[job.id, settings.PDF_SECRET_TOKEN])
    preview_path = reverse("jobcard_print_preview", args=[job.id, settings.PDF_SECRET_TOKEN])

    if request is not None:
        pdf_url = request.build_absolute_uri(pdf_path)
        preview_url = request.build_absolute_uri(preview_path)
    else:
        site_url = getattr(settings, "SITE_URL", "").rstrip("/")
        pdf_url = f"{site_url}{pdf_path}" if site_url else pdf_path
        preview_url = f"{site_url}{preview_path}" if site_url else preview_path

    whatsapp_url = ""
    whatsapp_message = ""
    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    mobile_no = (customer.mobile_no if customer else "") or ""
    if mobile_no:
        mobile = "91" + mobile_no[-10:]
        whatsapp_message = (
            f"Dear {customer.name},\n"
            f"Your Job Card {job.job_no} has been created.\n"
            f"Vehicle: {vehicle.registration_no if vehicle else ''}\n\n"
            f"JobCard PDF:\n{pdf_url}"
        )
        whatsapp_url = f"https://wa.me/{mobile}?text={quote(whatsapp_message)}"

    return {
        "print_preview_url": preview_url,
        "print_pdf_url": pdf_url,
        "whatsapp_url": whatsapp_url,
        "whatsapp_message": whatsapp_message,
    }
