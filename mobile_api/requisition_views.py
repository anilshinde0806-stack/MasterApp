from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import (
    Employee,
    ItemData,
    JobCard,
    PartRequisition,
    PartRequisitionLine,
    PartRequisitionFulfillment,
    PartStockTransaction,
    PartOrderHeader,
    PartOrder,
    Vehicle,
)
from core.views import (
    create_user_notification,
    is_advisor_employee,
    is_parts_manager,
    sync_part_requisition_status,
)


def _notify_parts_team(title, message, url=""):
    for employee in Employee.objects.select_related("user").filter(user__is_active=True):
        if is_parts_manager(employee):
            create_user_notification(employee.user, title, message, url)


def _notify_requisition_owner(requisition, title, message, url=""):
    create_user_notification(requisition.requested_by, title, message, url)


def _role_context(user):
    employee = Employee.objects.filter(user=user).first()
    advisor = is_advisor_employee(employee)
    parts_manager = is_parts_manager(employee)
    return employee, advisor, parts_manager


def _line_payload(line):
    return {
        "id": line.id,
        "estimated_part_id": line.estimated_part_id,
        "part_id": line.part_id,
        "part_no": line.part.item_code,
        "description": line.part.item_name,
        "unit": line.part.unit,
        "rate": str(line.part.rate),
        "stock_qty": str(line.part.current_stock),
        "requested_qty": str(line.requested_qty),
        "fulfilled_qty": str(line.fulfilled_qty),
        "pending_qty": str(line.pending_qty),
        "remarks": line.remarks,
    }


def _requisition_payload(requisition, *, detail=False, advisor=False):
    vehicle = getattr(getattr(requisition.job, "claim", None), "vehicle", None)
    data = {
        "id": requisition.id,
        "requisition_no": requisition.requisition_no,
        "job_id": requisition.job_id,
        "job_no": requisition.job.job_no,
        "vehicle_no": getattr(vehicle, "registration_no", "") or "",
        "priority": requisition.priority,
        "status": requisition.status,
        "remarks": requisition.remarks,
        "needed_by": requisition.needed_by.isoformat()
        if requisition.needed_by
        else None,
        "requested_at": requisition.requested_at.isoformat(),
        "requested_by": requisition.requested_by.get_full_name()
        or requisition.requested_by.username
        if requisition.requested_by
        else "",
        "line_count": len(requisition.lines.all()),
        "back_target": {
            "type": "jobcard" if advisor else "requisition_list",
            "job_id": requisition.job_id if advisor else None,
        },
    }
    if detail:
        data["lines"] = [_line_payload(line) for line in requisition.lines.all()]
    return data


class MobilePartRequisitionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _, advisor, _ = _role_context(request.user)
        queryset = PartRequisition.objects.select_related(
            "job",
            "job__claim",
            "job__claim__vehicle",
            "requested_by",
        ).prefetch_related("lines")
        if advisor and not request.user.is_superuser:
            queryset = queryset.filter(requested_by=request.user)

        query = (request.query_params.get("q") or "").strip()
        selected_status = (request.query_params.get("status") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(requisition_no__icontains=query)
                | Q(job__job_no__icontains=query)
                | Q(job__claim__vehicle__registration_no__icontains=query)
            ).distinct()
        if selected_status:
            queryset = queryset.filter(status=selected_status)

        return Response(
            {
                "results": [
                    _requisition_payload(item, advisor=advisor)
                    for item in queryset[:200]
                ],
                "is_advisor": advisor,
            }
        )


class MobilePartRequisitionJobsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        jobs = (
            JobCard.objects.select_related("claim", "claim__vehicle")
            .prefetch_related("parts")
            .order_by("-id")[:200]
        )
        return Response({
            "jobs": [
                {
                    "id": job.id,
                    "job_no": job.job_no,
                    "vehicle_no": (
                        job.claim.vehicle.registration_no
                        if job.claim_id and job.claim.vehicle_id else ""
                    ),
                    "estimated_part_count": job.parts.count(),
                    "has_open_requisition": job.part_requisitions.filter(
                        status__in=["Submitted", "Partially Fulfilled"]
                    ).exists(),
                }
                for job in jobs
                if job.parts.exists()
            ]
        })


class MobilePartMasterSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = str(request.query_params.get("q") or "").strip()
        if len(query) < 3:
            return Response({"results": []})
        items = ItemData.objects.filter(status="Active").filter(
            Q(item_code__icontains=query) | Q(item_name__icontains=query)
        ).order_by("item_code")[:15]
        return Response({
            "results": [
                {
                    "id": item.id,
                    "part_no": item.item_code,
                    "description": item.item_name,
                    "unit": item.unit,
                    "rate": str(item.rate),
                    "current_stock": str(item.current_stock),
                }
                for item in items
            ]
        })


class MobilePartRequisitionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, requisition_id):
        _, advisor, parts_manager = _role_context(request.user)
        requisition = get_object_or_404(
            PartRequisition.objects.select_related(
                "job",
                "job__claim",
                "job__claim__vehicle",
                "requested_by",
            ).prefetch_related("lines__part"),
            id=requisition_id,
        )
        if (
            advisor
            and not request.user.is_superuser
            and requisition.requested_by_id != request.user.id
        ):
            return Response(
                {"detail": "You cannot view another Advisor's requisition."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "requisition": _requisition_payload(
                    requisition,
                    detail=True,
                    advisor=advisor,
                ),
                "permissions": {
                    "can_fulfill": request.user.is_superuser or parts_manager,
                    "is_advisor": advisor,
                },
            }
        )


class MobilePartRequisitionFulfillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, requisition_id):
        employee = Employee.objects.filter(user=request.user).first()
        if not request.user.is_superuser and not is_parts_manager(employee):
            return Response({"detail": "Only Parts Managers can fulfil requisitions."}, status=403)
        requisition = get_object_or_404(PartRequisition.objects.select_related("job"), id=requisition_id)
        if requisition.status in {"Cancelled", "Fulfilled"}:
            return Response({"detail": f"Requisition is already {requisition.status.lower()}."}, status=400)
        raw_issues = request.data.get("issues") or {}
        if not isinstance(raw_issues, dict):
            return Response({"detail": "issues must be an object keyed by requisition line id."}, status=400)
        issue_values = {}
        for raw_line_id, raw_qty in raw_issues.items():
            try:
                line_id = int(raw_line_id)
                issue_qty = Decimal(str(raw_qty))
            except (TypeError, ValueError, InvalidOperation):
                return Response({"detail": "Issue quantities must be valid numbers."}, status=400)
            if issue_qty < 0:
                return Response({"detail": "Issue quantities cannot be negative."}, status=400)
            if issue_qty > 0:
                issue_values[line_id] = issue_qty
        if not issue_values:
            return Response({"detail": "Enter at least one quantity to issue."}, status=400)
        remarks = str(request.data.get("remarks") or "").strip()
        try:
            with transaction.atomic():
                lines = list(PartRequisitionLine.objects.select_for_update().filter(
                    id__in=issue_values, requisition=requisition).select_related("part"))
                if len(lines) != len(issue_values):
                    raise ValueError("One or more requisition lines are invalid.")
                for line in lines:
                    issue_qty = issue_values[line.id]
                    pending_qty = line.requested_qty - line.fulfilled_qty
                    if issue_qty > pending_qty:
                        raise ValueError(f"{line.part.item_code}: issue quantity exceeds pending quantity.")
                    part = ItemData.objects.select_for_update().get(id=line.part_id)
                    if issue_qty > part.current_stock:
                        raise ValueError(f"{part.item_code}: only {part.current_stock} {part.unit} available.")
                    new_balance = part.current_stock - issue_qty
                    part.current_stock = new_balance
                    part.save(update_fields=["current_stock", "updated_at"])
                    stock_tx = PartStockTransaction.objects.create(
                        part=part, transaction_type="Issue", quantity_change=-issue_qty,
                        balance_after=new_balance, reference=requisition.requisition_no,
                        remarks=remarks or f"Issued against job {requisition.job.job_no}",
                        created_by=request.user,
                    )
                    line.fulfilled_qty += issue_qty
                    line.save(update_fields=["fulfilled_qty"])
                    PartRequisitionFulfillment.objects.create(
                        line=line, quantity=issue_qty, stock_transaction=stock_tx,
                        issued_by=request.user, remarks=remarks,
                    )
                sync_part_requisition_status(requisition)
        except ValueError as error:
            return Response({"detail": str(error)}, status=400)
        _notify_requisition_owner(
            requisition,
            "Requisition Fulfilled",
            f"{requisition.requisition_no} was issued by Parts. Status: {requisition.status}.",
            f"/parts/requisitions/{requisition.id}/",
        )
        return Response({"message": "Parts issued successfully.", "status": requisition.status,
                         "requisition_id": requisition.id})


class MobilePartRequisitionReturnView(APIView):
    """Return previously issued parts to inventory."""
    permission_classes = [IsAuthenticated]

    def post(self, request, requisition_id):
        employee = Employee.objects.filter(user=request.user).first()
        if not request.user.is_superuser and not is_parts_manager(employee):
            return Response({"detail": "Only Parts Managers can return requisition parts."}, status=403)
        requisition = get_object_or_404(PartRequisition.objects.select_related("job"), id=requisition_id)
        if requisition.status == "Cancelled":
            return Response({"detail": "Cancelled requisitions cannot be returned."}, status=400)
        raw_returns = request.data.get("returns") or {}
        if not isinstance(raw_returns, dict):
            return Response({"detail": "returns must be an object keyed by requisition line id."}, status=400)
        return_values = {}
        for raw_line_id, raw_qty in raw_returns.items():
            try:
                line_id = int(raw_line_id)
                qty = Decimal(str(raw_qty))
            except (TypeError, ValueError, InvalidOperation):
                return Response({"detail": "Return quantities must be valid numbers."}, status=400)
            if qty < 0:
                return Response({"detail": "Return quantities cannot be negative."}, status=400)
            if qty > 0:
                return_values[line_id] = qty
        if not return_values:
            return Response({"detail": "Enter at least one quantity to return."}, status=400)
        remarks = str(request.data.get("remarks") or "").strip()
        try:
            with transaction.atomic():
                lines = list(PartRequisitionLine.objects.select_for_update().filter(
                    id__in=return_values, requisition=requisition).select_related("part"))
                if len(lines) != len(return_values):
                    raise ValueError("One or more requisition lines are invalid.")
                for line in lines:
                    qty = return_values[line.id]
                    if qty > line.fulfilled_qty:
                        raise ValueError(f"{line.part.item_code}: return exceeds fulfilled quantity.")
                    part = ItemData.objects.select_for_update().get(id=line.part_id)
                    new_balance = part.current_stock + qty
                    part.current_stock = new_balance
                    part.save(update_fields=["current_stock", "updated_at"])
                    PartStockTransaction.objects.create(
                        part=part, transaction_type="Return", quantity_change=qty,
                        balance_after=new_balance, reference=requisition.requisition_no,
                        remarks=remarks or f"Returned against job {requisition.job.job_no}",
                        created_by=request.user,
                    )
                    line.fulfilled_qty -= qty
                    line.save(update_fields=["fulfilled_qty"])
                sync_part_requisition_status(requisition)
        except ValueError as error:
            return Response({"detail": str(error)}, status=400)
        _notify_requisition_owner(
            requisition,
            "Parts Returned to Stock",
            f"Parts were returned for {requisition.requisition_no}. Status: {requisition.status}.",
            f"/parts/requisitions/{requisition.id}/",
        )
        return Response({"message": "Parts returned to stock successfully.", "status": requisition.status,
                         "requisition_id": requisition.id})


class MobileJobPartRequisitionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        _, advisor, parts_manager = _role_context(request.user)
        if not request.user.is_superuser and not advisor and not parts_manager:
            return Response(
                {"detail": "Only an Advisor can create a job estimate requisition."},
                status=status.HTTP_403_FORBIDDEN,
            )

        job = get_object_or_404(
            JobCard.objects.select_related("advisor").prefetch_related("parts"),
            id=job_id,
        )
        if (
            advisor
            and
            not request.user.is_superuser
            and job.advisor_id
            and job.advisor.user_id
            and job.advisor.user_id != request.user.id
        ):
            return Response(
                {"detail": "This job card is assigned to another Advisor."},
                status=status.HTTP_403_FORBIDDEN,
            )

        existing = job.part_requisitions.filter(
            status__in=["Submitted", "Partially Fulfilled"]
        ).first()
        if existing:
            return Response(
                {
                    "message": (
                        f"Open requisition {existing.requisition_no} already exists."
                    ),
                    "requisition_id": existing.id,
                    "created": False,
                }
            )

        estimated_parts = list(job.parts.all().order_by("id"))
        if not estimated_parts:
            return Response(
                {"detail": "Add estimated part lines before creating a requisition."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code_query = Q()
        for estimated_part in estimated_parts:
            code_query |= Q(item_code__iexact=estimated_part.part_no)
        master_by_code = {
            item.item_code.upper(): item
            for item in ItemData.objects.filter(status="Active").filter(code_query)
        }
        missing = [
            part.part_no
            for part in estimated_parts
            if part.part_no.upper() not in master_by_code
        ]
        if missing:
            return Response(
                {
                    "detail": (
                        "These estimated parts are missing or inactive in Part Master: "
                        + ", ".join(missing[:8])
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        needed_by = request.data.get("needed_by")
        priority = request.data.get("priority") or "Normal"
        if priority not in dict(PartRequisition.PRIORITY_CHOICES):
            priority = "Normal"

        with transaction.atomic():
            requisition = PartRequisition.objects.create(
                job=job,
                requested_by=request.user,
                needed_by=needed_by or None,
                priority=priority,
                remarks=(
                    request.data.get("remarks")
                    or "Created from approved job-card estimate."
                ),
            )
            requisition.requisition_no = (
                f"PR-{timezone.localdate():%Y%m%d}-{requisition.id:04d}"
            )
            requisition.save(update_fields=["requisition_no", "updated_at"])
            PartRequisitionLine.objects.bulk_create(
                [
                    PartRequisitionLine(
                        requisition=requisition,
                        part=master_by_code[estimated_part.part_no.upper()],
                        estimated_part=estimated_part,
                        requested_qty=Decimal(estimated_part.qty),
                        remarks="Estimate line",
                    )
                    for estimated_part in estimated_parts
                ]
            )

        _notify_parts_team(
            "New Part Requisition",
            f"Advisor {request.user.get_full_name() or request.user.username} created {requisition.requisition_no} for job {job.job_no}.",
            f"/parts/requisitions/{requisition.id}/",
        )

        return Response(
            {
                "message": f"Requisition {requisition.requisition_no} created.",
                "requisition_id": requisition.id,
                "created": True,
            },
            status=status.HTTP_201_CREATED,
        )


class MobilePartOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _, _, parts_manager = _role_context(request.user)
        if not request.user.is_superuser and not parts_manager:
            return Response(
                {"detail": "Parts Manager access is required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lines = request.data.get("lines") or []
        if not isinstance(lines, list):
            return Response({"detail": "Lines must be a list."}, status=400)
        valid_lines = []
        for line in lines:
            part_no = str(line.get("part_no") or "").strip()
            description = str(line.get("description") or "").strip()
            try:
                quantity = Decimal(str(line.get("qty") or "0"))
            except Exception:
                quantity = Decimal("0")
            if (part_no or description) and quantity > 0:
                valid_lines.append((part_no, description, quantity))
        if not valid_lines:
            return Response({"detail": "Add at least one part line."}, status=400)

        job = JobCard.objects.filter(id=request.data.get("job_id")).first()
        vehicle = Vehicle.objects.filter(id=request.data.get("vehicle_id")).first()
        if job and not vehicle and job.claim_id and job.claim.vehicle_id:
            vehicle = job.claim.vehicle
        if not job and not vehicle:
            return Response(
                {"detail": "Select a Job Card or Vehicle."}, status=400
            )

        with transaction.atomic():
            header = PartOrderHeader.objects.create(
                job=job,
                vehicle=vehicle,
                order_no=str(request.data.get("order_no") or "").strip(),
                order_date=request.data.get("order_date") or None,
                expected_date=request.data.get("expected_date") or None,
                supplier=str(request.data.get("supplier") or "").strip(),
                remarks=str(request.data.get("remarks") or "").strip(),
                status="Pending",
            )
            if not header.order_no:
                header.order_no = f"PO-{timezone.localdate():%Y%m%d}-{header.id:04d}"
                header.save(update_fields=["order_no", "updated_at"])
            for part_no, description, quantity in valid_lines:
                PartOrder.objects.create(
                    order=header,
                    job=job,
                    manual_part_no=part_no,
                    manual_description=description,
                    order_no=header.order_no,
                    supplier=header.supplier,
                    order_date=header.order_date,
                    expected_date=header.expected_date,
                    ordered_qty=quantity,
                    status="Pending",
                )

        if job and getattr(job, "advisor_id", None) and getattr(job.advisor, "user_id", None):
            create_user_notification(
                job.advisor.user,
                "Part Order Updated",
                f"Part order {header.order_no} was created/updated by Parts for job {job.job_no}.",
                f"/parts/orders/{header.id}/",
            )
        return Response(
            {
                "message": f"Part order {header.order_no} created.",
                "order_id": header.id,
                "order_no": header.order_no,
            },
            status=status.HTTP_201_CREATED,
        )
