from mobile_api.utils.branch_filter import filter_branch


class AdvisorRecentWorkService:

    def __init__(self, work_queryset):
        self.work = work_queryset

    def get(self):

        works = (
            self.work
            .select_related(
                "allocation",
                "allocation__job",
                "allocation__job__vehicle",
                "allocation__job__vehicle__customer",
            )
            .prefetch_related("allocation__progress__photos")
            .order_by("-id")[:50]
        )

        data = []
        seen_allocations = set()

        for item in works:

            if item.allocation_id in seen_allocations:
                continue
            seen_allocations.add(item.allocation_id)

            job = item.allocation.job
            progress_rows = list(item.allocation.progress.all())
            total_stages = len(progress_rows)
            completed_stages = sum(1 for row in progress_rows if row.finish_time)
            running_stages = sum(
                1 for row in progress_rows
                if row.start_time and not row.finish_time
            )
            progress_value = (
                (completed_stages + (running_stages * 0.5)) / total_stages
                if total_stages else 0
            )
            if job.repair_status in ["Completed", "Closed"]:
                progress_value = 1
            latest_activity = max(
                (
                    row.finish_time or row.start_time
                    for row in progress_rows
                    if row.finish_time or row.start_time
                ),
                default=None,
            )

            data.append({
                "id": job.id,
                "job_no": job.job_no,
                "claim_no": job.claim.claim_no if job.claim else "",

                "vehicle_no": (
                    job.vehicle.registration_no
                    if job.vehicle
                    else ""
                ),

                "customer_name": (
                    job.vehicle.customer.name
                    if job.vehicle and job.vehicle.customer
                    else ""
                ),

                "advisor": job.advisor.name if job.advisor else "",

                "technician": (
    str(item.employee)
    if item.employee
    else ""
),

                "insurance_company": (
                    str(job.claim.insurance_company)
                    if job.claim and job.claim.insurance_company
                    else ""
                ),

                "status": job.repair_status,

                "progress": round(progress_value, 3),

                "photo_count": sum(
                    len(row.photos.all()) for row in progress_rows
                ),

                "remarks_added": any(
                    bool((row.remarks or "").strip()) for row in progress_rows
                ),

                "updated_at": (
                    latest_activity.isoformat() if latest_activity else ""
                ),

                "priority": getattr(job, "priority", ""),
            })

            if len(data) >= 10:
                break

        return data
