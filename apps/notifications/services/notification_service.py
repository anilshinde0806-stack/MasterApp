from core.models import Employee, UserNotification


def notification_payload(notification):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "url": notification.url or "",
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(
            sep=" ", timespec="minutes"
        ),
    }


def create_user_notification(user, title, message, url=""):
    if not user:
        return None
    return UserNotification.objects.create(
        user=user,
        title=title,
        message=message,
        url=url or "",
    )


def create_unread_notification_once(user, title, message, url=""):
    if not user:
        return None
    notification, _ = UserNotification.objects.get_or_create(
        user=user,
        title=title,
        message=message,
        is_read=False,
        defaults={"url": url or ""},
    )
    return notification


def notify_work_start_blocked(progress, reason):
    job = progress.allocation.job if progress and progress.allocation_id else None
    if not job:
        return []

    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else job.vehicle
    registration_no = vehicle.registration_no if vehicle else "-"
    technician = progress.employee.name if progress.employee_id else "Technician"
    title = "Repair Start Requires Approval"
    message = (
        f"{technician} cannot start {progress.get_stage_display()} for "
        f"Jobcard {job.job_no} ({registration_no}). {reason}"
    )

    recipients = []
    if job.advisor_id and job.advisor.user_id:
        recipients.append(job.advisor.user)
    elif claim and claim.employee_id and claim.employee.user_id:
        recipients.append(claim.employee.user)

    floor_employees = list(Employee.objects.filter(
        is_active=True,
        user__isnull=False,
    ).select_related("user", "branch"))
    floor_supervisors = []
    for employee in floor_employees:
        role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
        if any(role in role_text for role in ("FLOOR SUPERVISOR", "FLOOR INCHARGE", "FLOOR IN-CHARGE")):
            floor_supervisors.append(employee)

    branch_supervisors = [
        employee
        for employee in floor_supervisors
        if not job.branch_id or employee.branch_id in (None, job.branch_id)
    ]
    recipients.extend(
        employee.user for employee in (branch_supervisors or floor_supervisors)
    )

    created = []
    seen = set()
    for user in recipients:
        if not user or user.id in seen:
            continue
        seen.add(user.id)
        created.append(
            create_unread_notification_once(
                user,
                title,
                message,
                f"/claim/{claim.id}/edit/" if claim else f"/jobCard/{job.id}/edit/",
            )
        )
    return created


def notify_jobcard_advisor(job, title, message):
    if not job:
        return None
    advisor_user = None
    if job.advisor_id and job.advisor and job.advisor.user_id:
        advisor_user = job.advisor.user
    elif (
        job.claim_id
        and job.claim
        and job.claim.employee_id
        and job.claim.employee.user_id
    ):
        advisor_user = job.claim.employee.user
    return create_user_notification(
        advisor_user,
        title,
        message,
        f"/jobCard/{job.id}/edit/",
    )


def notify_work_progress_change(progress, action_label):
    job = progress.allocation.job if progress and progress.allocation_id else None
    if not job:
        return None
    claim = job.claim if job.claim_id else None
    vehicle = claim.vehicle if claim and claim.vehicle_id else None
    registration_no = vehicle.registration_no if vehicle else "-"
    return notify_jobcard_advisor(
        job,
        "Repair Work Progress Updated",
        f"Jobcard {job.job_no} {progress.get_stage_display()} "
        f"{action_label} for {registration_no}",
    )
