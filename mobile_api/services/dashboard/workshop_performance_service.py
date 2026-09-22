from django.db.models import Count, Q

from core.models import JobCard, Employee
from mobile_api.services.dashboard.filter_service import DashboardFilterService




class WorkshopPerformanceService:

    def __init__(
        self,
        jobcards
    ):
        self.jobcards = jobcards

    def get(self):

        from django.db import connection
        import json

        jobcard_ids = list(
            self.jobcards.values_list(
                "id",
                flat=True
            )
        )

        print("\n========== WORKSHOP SERVICE DEBUG ==========")

        print("JOBCARD IDS:", jobcard_ids)

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT fn_workshop_performance(%s)
                """,
                [jobcard_ids]
            )

            row = cursor.fetchone()

        result = row[0] if row else {}

        # PostgreSQL JSONB may already be a dict,
        # but this keeps it safe.
        if isinstance(result, str):
            result = json.loads(result)

        print("WORKSHOP RESULT:", result)

        print("============================================\n")

        return result
    # =====================================================
    # BASE JOBCARD QUERYSET
    # =====================================================

    def get_jobcards(self):

        queryset = JobCard.objects.select_related(
            "branch"
        )

        queryset = DashboardFilterService(

            queryset=queryset,

            branch=self.branch,

            period=self.period,

            start_date=self.start_date,

            end_date=self.end_date,

        ).filter()

        return queryset


    # =====================================================
    # WORKSHOP PERFORMANCE
    # =====================================================

    def get_performance(self):

        jobcards = self.get_jobcards()

        total_jobs = jobcards.count()


        # -------------------------------------------------
        # COMPLETED
        # -------------------------------------------------

        completed_jobs = jobcards.filter(
            repair_status__iexact="Completed"
        ).count()


        # -------------------------------------------------
        # RUNNING
        # -------------------------------------------------

        running_jobs = jobcards.filter(
            repair_status__iexact="Open"
        ).count()


        # -------------------------------------------------
        # PENDING
        # -------------------------------------------------

        pending_jobs = jobcards.filter(
             repair_status__iexact="Allocated"
        ).count()


        # -------------------------------------------------
        # READY FOR DELIVERY
        # -------------------------------------------------

        ready_for_delivery = jobcards.filter(
            ready_for_delivery=True
        ).count()


        # -------------------------------------------------
        # COMPLETION %
        # -------------------------------------------------

        completion_percentage = (

            round(
                (completed_jobs / total_jobs) * 100,
                2
            )

            if total_jobs > 0

            else 0

        )


        return {

            "total_jobs": total_jobs,

            "completed_jobs": completed_jobs,

            "running_jobs": running_jobs,

            "pending_jobs": pending_jobs,

            "ready_for_delivery": ready_for_delivery,

            "completion_percentage": completion_percentage,

            "average_tat": 0,

            "overdue_jobs": 0,

            "on_time_delivery": 0,

        }


    # =====================================================
    # JOB PROGRESS
    # =====================================================

    def get_job_progress(self):

        jobcards = self.get_jobcards()


        stages = [

            {
                "key": "received",
                "title": "Vehicle Received",
                "count": jobcards.count(),
                "color": "#2563eb",
            },

            {
                "key": "inspection",
                "title": "Inspection",
                "count": 0,
                "color": "#0891b2",
            },

            {
                "key": "insurance",
                "title": "Insurance Approval",
                "count": 0,
                "color": "#f97316",
            },

            {
                "key": "parts",
                "title": "Parts Pending",
                "count": 0,
                "color": "#9333ea",
            },

            {
                "key": "denting",
                "title": "Denting",
                "count": 0,
                "color": "#0f766e",
            },

            {
                "key": "painting",
                "title": "Painting",
                "count": 0,
                "color": "#ec4899",
            },

            {
                "key": "quality_check",
                "title": "Quality Check",
                "count": 0,
                "color": "#4f46e5",
            },

            {
                "key": "ready",
                "title": "Ready for Delivery",
                "count": jobcards.filter(
                    ready_for_delivery=True
                ).count(),
                "color": "#16a34a",
            },

        ]


        total = jobcards.count()


        for stage in stages:

            stage["percentage"] = (

                round(
                    (stage["count"] / total) * 100,
                    1
                )

                if total > 0

                else 0

            )


        return stages


    # =====================================================
    # TECHNICIAN PERFORMANCE
    # =====================================================

    def get_technician_performance(self):

        technicians = Employee.objects.filter(

            is_active=True

        ).filter(

           
            Q(designation__iexact="Technician") 

        )


        # -----------------------------------------------
        # BRANCH
        # -----------------------------------------------

        if self.branch:

            technicians = technicians.filter(
                branch=self.branch
            )


        technicians = technicians.annotate(

            total_jobs=Count(
                "workprogress",
                distinct=True
            ),

            completed_jobs=Count(

                "workprogress",

                filter=Q(
                    workprogress__finish_time__isnull=False
                ),

                distinct=True

            ),

            running_jobs=Count(

                "workprogress",

                filter=Q(

                    workprogress__start_time__isnull=False,

                    workprogress__finish_time__isnull=True

                ),

                distinct=True

            ),

        )


        results = []


        for technician in technicians:

            total = technician.total_jobs or 0

            completed = technician.completed_jobs or 0

            running = technician.running_jobs or 0


            utilization = (

                round(
                    (completed / total) * 100,
                    2
                )

                if total > 0

                else 0

            )


            if total == 0:

                continue


            results.append({

                "id": technician.id,

                "name": technician.name,

                "assigned": total,

                "in_progress": running,

                "completed": completed,

                "utilization": utilization,

            })


        results.sort(

            key=lambda item: (

                item["utilization"],

                item["completed"]

            ),

            reverse=True

        )


        return results[:5]


    # =====================================================
    # MANPOWER
    # =====================================================

    def get_manpower(self):

        employees = Employee.objects.filter(
            is_active=True
        )


        if self.branch:

            employees = employees.filter(
                branch=self.branch
            )


        technicians = employees.filter(
            employee_type__iexact="TECHNICIAN"
        ).count()


        denters = employees.filter(
            designation__icontains="DENTER"
        ).count()


        painters = employees.filter(
            designation__icontains="PAINTER"
        ).count()


        mechanics = employees.filter(
            designation__icontains="MECHANIC"
        ).count()


        total_manpower = employees.count()


        return {

            "technicians": {

                "current": technicians,

                "total": technicians,

                "percentage": 100 if technicians else 0,

            },


            "denters": {

                "current": denters,

                "total": denters,

                "percentage": 100 if denters else 0,

            },


            "painters": {

                "current": painters,

                "total": painters,

                "percentage": 100 if painters else 0,

            },


            "mechanics": {

                "current": mechanics,

                "total": mechanics,

                "percentage": 100 if mechanics else 0,

            },


            "total_manpower": total_manpower,

        }


    # =====================================================
    # BOTTLENECKS
    # =====================================================

    def get_bottlenecks(self):

        jobcards = self.get_jobcards()


        pending_jobs = jobcards.filter(
            repair_status__iexact="Open"
        ).count()


        ready_jobs = jobcards.filter(
            ready_for_delivery=True
        ).count()


        return [

            {

                "key": "pending",

                "title": "Jobs Pending",

                "count": pending_jobs,

                "type": "warning",

                "target_tab": "workshop",

            },


            {

                "key": "ready",

                "title": "Ready For Delivery",

                "count": ready_jobs,

                "type": "success",

                "target_tab": "overview",

            },

        ]


    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    