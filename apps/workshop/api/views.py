from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.claims.services.repair_workflow_service import (
    RepairWorkflowBlocked,
    RepairWorkflowService,
)
from apps.common.utils.parser_utils import clean_text, parse_mobile_date
from apps.jobcards.api.payloads import (
    mobile_employee_list,
    mobile_jobcard_payload,
    mobile_stage_list,
)
from apps.jobcards.services.access import dashboard_querysets_for_user
from apps.notifications.services.notification_service import (
    notify_work_progress_change as mobile_notify_work_progress_change,
    notify_work_start_blocked,
)
from core.models import (
    Employee,
    JobCard,
    WorkAllocation,
    WorkProgress,
    WorkProgressPhoto,
)

def is_mobile_repair_resource(employee):
    if not employee:
        return False

    role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
    return any(
        keyword in role_text
        for keyword in ["TECHNICIAN", "DENTER", "PAINTER"]
    )


def mobile_work_progress_payload(progress, request=None):
    job = progress.allocation.job if progress.allocation_id else None
    claim = job.claim if job and job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    customer = vehicle.customer if vehicle and vehicle.customer_id else None

    photo_urls = []
    for photo in progress.photos.all():
        if not photo.image:
            continue
        url = photo.image.url
        photo_urls.append(request.build_absolute_uri(url) if request else url)

    return {
        "id": progress.id,
        "stage": progress.stage,
        "stage_label": progress.get_stage_display(),
        "start_time": progress.start_time.isoformat() if progress.start_time else "",
        "finish_time": progress.finish_time.isoformat() if progress.finish_time else "",
        "remarks": progress.remarks or "",
        "assigned_at": (
            progress.allocation.allotment_date.isoformat()
            if progress.allocation_id and progress.allocation.allotment_date
            else ""
        ),
        "photo_count": len(photo_urls),
        "before_photos": [],
        "after_photos": photo_urls,
        "job_id": job.id if job else "",
        "job_no": job.job_no if job else "",
        "claim_no": claim.claim_no if claim else "",
        "registration_no": vehicle.registration_no if vehicle else "",
        "model": vehicle.model.name if vehicle and vehicle.model_id else "",
        "customer": customer.name if customer else "",
    }


def mobile_my_work_queryset(employee, from_date=None, to_date=None):
    progress = (
        WorkProgress.objects
        .select_related(
            "allocation",
            "allocation__job",
            "allocation__job__claim",
            "allocation__job__claim__vehicle",
            "allocation__job__claim__vehicle__customer",
            "allocation__job__claim__vehicle__model",
            "employee",
        )
        .prefetch_related("photos")
        .filter(employee=employee)
    )

    if from_date:
        progress = progress.filter(allocation__job__created_at__date__gte=from_date)
    if to_date:
        progress = progress.filter(allocation__job__created_at__date__lte=to_date)

    return progress


def mobile_apply_my_work_status(progress, status_filter):
    if status_filter == "wip":
        return progress.filter(start_time__isnull=False, finish_time__isnull=True)
    if status_filter == "completed":
        return progress.filter(finish_time__isnull=False)
    return progress.filter(start_time__isnull=True)


class MobileMyWorkListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = Employee.objects.filter(user=request.user).first()
        if not is_mobile_repair_resource(employee):
            return Response(
                {"detail": "Only Technician, Denter or Painter can access My Work."},
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.localdate()
        month_start = today.replace(day=1)

        status_filter = clean_text(request.GET.get("status")) or "new"

        from_date = None
        to_date = None

        if status_filter == "completed":
            from_date = (
                    parse_mobile_date(request.GET.get("from_date"))
                    or month_start
            )

            to_date = (
                    parse_mobile_date(request.GET.get("to_date"))
                    or today
            )

        base_progress = mobile_my_work_queryset(
            employee,
            from_date,
            to_date,
        )
        rows = mobile_apply_my_work_status(
            base_progress,
            status_filter,
        ).order_by(
            "start_time",
            "allocation__job__job_no",
            "id",
        )

        


        jobs = [
            mobile_work_progress_payload(progress, request)
            for progress in rows
        ]



        return Response({
            "filters": {
            "from_date": from_date.isoformat() if from_date else None,
            "to_date": to_date.isoformat() if to_date else None,
            "status": status_filter,
                       },
            "counts": {
                "new": base_progress.filter(start_time__isnull=True).count(),
                "wip": base_progress.filter(start_time__isnull=False, finish_time__isnull=True).count(),
                "completed": base_progress.filter(finish_time__isnull=False).count(),
            },
            "jobs": jobs,
        })


class MobileMyWorkActionView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    def post(self, request, progress_id):
        employee = Employee.objects.filter(user=request.user).first()
        if not is_mobile_repair_resource(employee):
            return Response(
                {"detail": "Only Technician, Denter or Painter can update My Work."},
                status=status.HTTP_403_FORBIDDEN,
            )

        progress = (
            WorkProgress.objects
            .select_related(
                "allocation",
                "allocation__job",
                "allocation__job__advisor",
                "allocation__job__advisor__user",
                "allocation__job__claim",
                "allocation__job__claim__employee",
                "allocation__job__claim__employee__user",
                "allocation__job__claim__vehicle",
            )
            .filter(id=progress_id, employee=employee)
            .first()
        )

        if not progress:
            return Response({"detail": "Work progress not found."}, status=status.HTTP_404_NOT_FOUND)

        uploaded_images = request.FILES.getlist("progress_photos")
        if uploaded_images and (not progress.start_time or progress.finish_time):
            return Response(
                {"detail": "Photos can only be uploaded while work is in progress."},
                status=status.HTTP_409_CONFLICT,
            )

        action = clean_text(request.data.get("action"))
        old_start_time = progress.start_time
        old_finish_time = progress.finish_time

        if action in {"start", "finish"}:
            try:
                RepairWorkflowService.ensure_start_allowed(
                    progress.allocation.job
                )
            except RepairWorkflowBlocked as exc:
                notify_work_start_blocked(progress, str(exc))
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_409_CONFLICT,
                )

        if action == "start" and not progress.start_time:
            progress.start_time = timezone.now()
            progress.save(update_fields=["start_time"])
        elif action == "finish":
            if not progress.start_time:
                progress.start_time = timezone.now()
            if not progress.finish_time:
                progress.finish_time = timezone.now()
            progress.save(update_fields=["start_time", "finish_time"])

        if action in {"start", "finish"} and progress.start_time:
            RepairWorkflowService.mark_repair_started(progress.allocation.job)

        for image in uploaded_images:
            WorkProgressPhoto.objects.create(
                progress=progress,
                image=image,
            )

        if action == "start" and not old_start_time and progress.start_time:
            mobile_notify_work_progress_change(progress, "started")
        elif action == "finish" and not old_finish_time and progress.finish_time:
            mobile_notify_work_progress_change(progress, "finished")

        return Response({
            "message": "My Work updated successfully.",
            "job": mobile_work_progress_payload(progress, request),
        })


class MobileWorkAllocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        _, jobcards = dashboard_querysets_for_user(request.user)

        job = (
            jobcards
            .select_related(
                "claim",
                "claim__vehicle",
                "claim__vehicle__customer",
                "advisor",
            )
            .prefetch_related(
                "allocation__progress",
                "allocation__progress__employee",
            )
            .filter(pk=pk)
            .first()
        )
        if not job:
            return Response(
                {"detail": "Job Card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        employees = [
            {
                "id": emp.id,
                "name": emp.name,
            }
            for emp in Employee.objects.filter(is_active=True).order_by("name")
        ]
        stages = [
            {
                "value": value,
                "label": label,
            }
            for value, label in WorkProgress.STAGES
        ]
        progress = []
        allocation = getattr(job, "allocation", None)
        if allocation:

            for item in allocation.progress.select_related("employee").order_by("id"):

                if item.finish_time:
                    status = "Completed"
                elif item.start_time:
                    status = "Started"
                else:
                    status = "Pending"

                progress.append({
                    "id": item.id,
                    "stage": item.stage,
                    "stage_label": item.get_stage_display(),
                    "employee": item.employee.name if item.employee else "",
                    "employee_id": item.employee_id,
                    "remarks": item.remarks,
                    "status": status,
                    "started_at": (
                        item.start_time.strftime("%d-%m-%Y %H:%M")
                        if item.start_time else ""
                    ),
                    "completed_at": (
                        item.finish_time.strftime("%d-%m-%Y %H:%M")
                        if item.finish_time else ""
                    ),
                })
        return Response(
            {
                "jobcard": mobile_jobcard_payload(job,request),
                "employees": mobile_employee_list(),
                "stages": mobile_stage_list(),
                "progress": progress,
            }
        )

    def post(self, request, pk):

        job = JobCard.objects.select_related("claim").filter(pk=pk).first()

        if not job:
            return Response(
                {"detail": "Job Card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            RepairWorkflowService.ensure_allocation_allowed(job)
        except RepairWorkflowBlocked as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        stage = (request.data.get("stage") or "").strip()
        employee_id = request.data.get("employee")
        remarks = (request.data.get("remarks") or "").strip()

        if not stage:
            return Response(
                {"detail": "Select Progress Stage."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if stage not in dict(WorkProgress.STAGES):
            return Response(
                {"detail": "Invalid Progress Stage."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not employee_id:
            return Response(
                {"detail": "Select Technician."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee = Employee.objects.filter(
            pk=employee_id,
            is_active=True,
        ).first()

        if not employee:
            return Response(
                {"detail": "Technician not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allocation, created = WorkAllocation.objects.get_or_create(
            job=job,
        )

        # Prevent duplicate stage allocation only
        if allocation.progress.filter(stage=stage).exists():
            return Response(
                {
                    "detail": "This repair stage is already allocated."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        progress = WorkProgress.objects.create(
            allocation=allocation,
            stage=stage,
            employee=employee,
            remarks=remarks,
        )
        # Update job status after first allocation
        if getattr(job, "repair_status", None) != "Allocated":
            job.repair_status = "Allocated"
            job.save(update_fields=["repair_status"])

        return Response(
            {
                "message": "Repair stage allocated successfully.",
                "progress": {
                    "id": progress.id,
                    "stage": progress.stage,
                    "stage_label": progress.get_stage_display(),
                    "employee": employee.name,
                    "employee_id": employee.id,
                    "remarks": progress.remarks,
                    "status": "Pending",
                },
            },
            status=status.HTTP_201_CREATED,
        )


class MobileRepairProgressView(APIView):
    permission_classes = [IsAuthenticated]

    STAGE_ORDER = [
        "Dismantling",
        "Mechanical",
        "Body Repair/Denting",
        "Paint Preperation",
        "Painting",
        "Assembly",
        "Fitting",
        "Polishing",
    ]

    def get(self, request, pk):

        _, jobcards = dashboard_querysets_for_user(request.user)

        job = (
            jobcards
            .select_related(
                "claim",
                "claim__vehicle",
                "claim__vehicle__customer",
                "advisor",
            )
            .prefetch_related(
                "allocation__progress__employee",
            )
            .filter(pk=pk)
            .first()
        )

        if not job:
            return Response(
                {"detail": "Job Card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        allocation = getattr(job, "allocation", None)

        progress = []

        if allocation:

            for item in allocation.progress.all().order_by("id"):

                if item.finish_time:
                    status_name = "Completed"
                elif item.start_time:
                    status_name = "Started"
                else:
                    status_name = "Pending"

                progress.append(
                    {
                        "id": item.id,
                        "stage": item.stage,
                        "stage_label": item.get_stage_display(),
                        "employee": item.employee.name if item.employee else "",
                        "employee_id": item.employee_id,
                        "remarks": item.remarks,
                        "status": status_name,
                        "started_at": (
                            item.start_time.strftime("%d-%m-%Y %H:%M")
                            if item.start_time else ""
                        ),
                        "completed_at": (
                            item.finish_time.strftime("%d-%m-%Y %H:%M")
                            if item.finish_time else ""
                        ),
                    }
                )

        response_data = {
            "jobcard": mobile_jobcard_payload(job,request),
            "employees": mobile_employee_list(),
            "stages": mobile_stage_list(),
            "progress": progress,
        }


        return Response(response_data)
    def post(self, request, pk):

        action = (request.data.get("action") or "").strip().lower()
        progress_id = request.data.get("progress_id")
        remarks = (request.data.get("remarks") or "").strip()

        if not progress_id:
            return Response(
                {"detail": "Progress ID required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        progress = (
            WorkProgress.objects
            .select_related(
                "allocation",
                "allocation__job",
                "allocation__job__claim",
            )
            .filter(pk=progress_id)
            .first()
        )

        if not progress:
            return Response(
                {"detail": "Repair stage not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        job = progress.allocation.job

        if action == "start":

            try:
                RepairWorkflowService.ensure_start_allowed(job)
            except RepairWorkflowBlocked as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_409_CONFLICT,
                )

            if progress.start_time:
                return Response(
                    {
                        "detail": "Stage already started."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            progress.start_time = timezone.now()

            if remarks:
                progress.remarks = remarks

            progress.save()
            RepairWorkflowService.mark_repair_started(job)

            if job.repair_status != "In Progress":
                job.repair_status = "In Progress"
                job.save(update_fields=["repair_status"])

            return Response(
                {
                    "message": "Repair stage started successfully.",
                    "progress_id": progress.id,
                }
            )

        elif action == "complete":

            try:
                RepairWorkflowService.ensure_start_allowed(job)
            except RepairWorkflowBlocked as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_409_CONFLICT,
                )

            if not progress.start_time:
                return Response(
                    {
                        "detail": "Start the stage first."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if progress.finish_time:
                return Response(
                    {
                        "detail": "Stage already completed."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            progress.finish_time = timezone.now()

            if remarks:
                progress.remarks = remarks

            progress.save()

            remaining = progress.allocation.progress.filter(
                finish_time__isnull=True,
            ).exists()

            if not remaining:
                job.repair_status = "Repair Completed"
                job.save(update_fields=["repair_status"])

            return Response(
                {
                    "message": "Repair stage completed successfully.",
                    "progress_id": progress.id,
                }
            )

        return Response(
            {
                "detail": "Invalid action."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class RepairProgressPhotoListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):

        job = get_object_or_404(JobCard, id=job_id)

        photos = WorkProgressPhoto.objects.filter(
            progress__allocation__job=job
        ).select_related("progress")

        data = []

        for photo in photos:
            data.append({
                "id": photo.id,
                "image": request.build_absolute_uri(photo.image.url),
                "stage": photo.progress.stage,
                "uploaded_at": photo.uploaded_at.strftime("%d-%m-%Y %H:%M"),
            })

        return Response({
            "photos": data,
        })


class RepairProgressPhotoUploadAPIView(APIView):
        permission_classes = [IsAuthenticated]

        def post(self, request, job_id):
            job = JobCard.objects.filter(id=job_id).first()

            if not job:
                return Response(
                    {"detail": "Job not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            photos = request.FILES.getlist("progress_photos")

            if not photos:
                return Response(
                    {"detail": "No photo selected."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            progress = (
                WorkProgress.objects
                .filter(allocation__job=job)
                .order_by("-id")
                .first()
            )

            if not progress:
                return Response(
                    {"detail": "Repair stage not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            for photo in photos:
                WorkProgressPhoto.objects.create(
                    progress=progress,
                    image=photo,
                )

            return Response({
                "success": True,
                "message": "Photo uploaded successfully.",
            })


class RepairProgressPhotoDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, job_id, photo_id):

        photo = WorkProgressPhoto.objects.filter(
            id=photo_id,
            progress__allocation__job_id=job_id,
        ).first()

        if not photo:
            return Response(
                {"detail": "Photo not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Delete image file
        if photo.image:
            photo.image.delete(save=False)

        photo.delete()

        return Response(
            {
                "success": True,
                "message": "Photo deleted successfully.",
            }
        )


class MyWorkAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        employee = Employee.objects.get(
            user=request.user
        )

        queryset = WorkAllocation.objects.filter(
            employee=employee,
            is_completed=False,
        )

        jobs = []

        for allocation in queryset:

            progress = allocation.progress

            job = allocation.jobcard

            jobs.append({

                "id": allocation.id,

                "job_no": job.job_card_no,

                "claim_no": job.claim.claim_no,

                "ic_claim_no": job.claim.ic_claim_no,

                "vehicle_no": job.vehicle.registration_no,

                "vehicle_model": str(job.vehicle.model),

                "customer_name":
                    job.vehicle.customer.name,

                "advisor":
                    job.advisor.name,

                "technician":
                    employee.name,

                "work_type":
                    progress.work_type.name,

                "status":
                    progress.status,

                "priority":
                    progress.priority,

                "progress":
                    progress.progress_percentage,

                "assigned_at":
                    allocation.created_at,

                "started_at":
                    progress.started_at,

                "completed_at":
                    progress.completed_at,

                "remarks":
                    progress.remarks,

                "before_photos": [],

                "after_photos": [],

            })

        return Response({

            "summary": {

                "assigned":
                    queryset.filter(
                        progress__status="Assigned"
                    ).count(),

                "started":
                    queryset.filter(
                        progress__status="Started"
                    ).count(),

                "paused":
                    queryset.filter(
                        progress__status="Paused"
                    ).count(),

                "completed":
                    queryset.filter(
                        progress__status="Completed"
                    ).count(),
            },

            "jobs": jobs

        })


class MobileMyWorkDetailView(APIView):
        permission_classes = [IsAuthenticated]

        def get(self, request, progress_id):
            employee = Employee.objects.filter(
                user=request.user
            ).first()

            progress = (
                WorkProgress.objects
                .select_related(
                    "allocation",
                    "allocation__job",
                    "allocation__job__claim",
                    "allocation__job__claim__vehicle",
                )
                .filter(
                    id=progress_id,
                    employee=employee,
                )
                .first()
            )

            if not progress:
                return Response(
                    {"detail": "Not found"},
                    status=404,
                )

            return Response(
                mobile_work_progress_payload(progress, request)
            )


class MobileMyWorkUpdateView(APIView):

    permission_classes = [IsAuthenticated]

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    def post(self, request, progress_id):

        employee = Employee.objects.filter(
            user=request.user
        ).first()

        if not is_mobile_repair_resource(employee):
            return Response(
                {"detail": "Permission denied"},
                status=403,
            )

        progress = (
            WorkProgress.objects
            .select_related("allocation__job__claim")
            .filter(
                id=progress_id,
                employee=employee,
            )
            .first()
        )

        if not progress:
            return Response(
                {"detail": "Work not found"},
                status=404,
            )

        uploaded_images = request.FILES.getlist("progress_photos")
        if uploaded_images and (not progress.start_time or progress.finish_time):
            return Response(
                {"detail": "Photos can only be uploaded while work is in progress."},
                status=409,
            )

        action = clean_text(
            request.data.get("action") or ""
        )

        remarks = clean_text(
            request.data.get("remarks") or ""
        )

        if remarks:
            progress.remarks = remarks

        if action == "start":
            try:
                RepairWorkflowService.ensure_start_allowed(
                    progress.allocation.job
                )
            except RepairWorkflowBlocked as exc:
                notify_work_start_blocked(progress, str(exc))
                return Response({"detail": str(exc)}, status=409)
            if not progress.start_time:
                progress.start_time = timezone.now()

        elif action == "finish":

            try:
                RepairWorkflowService.ensure_start_allowed(
                    progress.allocation.job
                )
            except RepairWorkflowBlocked as exc:
                notify_work_start_blocked(progress, str(exc))
                return Response({"detail": str(exc)}, status=409)

            if not progress.start_time:
                progress.start_time = timezone.now()

            if not progress.finish_time:
                progress.finish_time = timezone.now()

        progress.save()
        if action in {"start", "finish"} and progress.start_time:
            RepairWorkflowService.mark_repair_started(progress.allocation.job)

        for image in uploaded_images:

            WorkProgressPhoto.objects.create(
                progress=progress,
                image=image,
            )

        return Response({

            "message": "Updated successfully.",

            "job": mobile_work_progress_payload(
                progress,
                request,
            ),

        })
