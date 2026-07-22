class AdvisorPerformanceService:

    def __init__(self, work):

        self.work = work

    def get(self):

        total = self.work.count()

        completed = self.work.filter(
            finish_time__isnull=False
        ).count()

        running = self.work.filter(
            start_time__isnull=False,
            finish_time__isnull=True,
        ).count()

        pending = total - completed - running

        completion = (
            round(completed * 100 / total, 1)
            if total
            else 0
        )

        return {

            "total_jobs": total,

            "completed_jobs": completed,

            "pending_jobs": pending,

            "running_jobs": running,

            "completion_percentage": completion,

            "average_tat": "2.5 Days",

        }