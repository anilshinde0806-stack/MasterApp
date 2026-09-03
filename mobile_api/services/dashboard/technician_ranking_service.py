from django.db.models import Count, Q

from core.models import Employee, WorkProgress
from mobile_api.services.dashboard.filter_service import DashboardFilterService


class TopTechnicianService:

    def __init__(
        self,
        employee,
        branch=None,
        period="today",
        start_date=None,
        end_date=None,
    ):
        self.employee = employee
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date


    def get(self):

        # ======================================
        # GET TECHNICIANS
        # ======================================

        technicians = Employee.objects.filter(
            is_active=True
        ).filter(
            Q(employee_type__iexact="STAFF") |
            Q(employee_type__iexact="TECHNICIAN") |
            Q(employee_type__iexact="PAINTER") |
            Q(employee_type__iexact="DENTER")
        )


        # ======================================
        # FILTER EMPLOYEES BY BRANCH
        # ======================================

        if self.branch:

            technicians = technicians.filter(
                branch=self.branch
            )


        # ======================================
        # GET FILTERED WORK PROGRESS
        # ======================================

        work_queryset = WorkProgress.objects.select_related(
            "employee",
            "allocation",
            "allocation__job",
            "allocation__job__branch",
        )


        # Apply Branch + Period + Date filters
        work_queryset = DashboardFilterService(
            queryset=work_queryset,

            branch=self.branch,

            period=self.period,

            start_date=self.start_date,

            end_date=self.end_date,

            # WorkProgress -> WorkAllocation -> JobCard
            branch_field="allocation__job__branch",

            date_field="allocation__job__job_date",

        ).filter()


        # Get filtered WorkProgress IDs
        filtered_work_ids = work_queryset.values_list(
            "id",
            flat=True
        )


        # ======================================
        # CALCULATE TECHNICIAN PERFORMANCE
        # ======================================

        technicians = technicians.annotate(

            total_jobs=Count(

                "workprogress",

                filter=Q(
                    workprogress__id__in=filtered_work_ids
                ),

                distinct=True,

            ),


            completed_jobs=Count(

                "workprogress",

                filter=Q(
                    workprogress__id__in=filtered_work_ids,

                    workprogress__finish_time__isnull=False,
                ),

                distinct=True,

            ),

        )


        # ======================================
        # FORMAT RESULTS
        # ======================================

        results = []


        for technician in technicians:

            total_jobs = (
                technician.total_jobs or 0
            )

            completed_jobs = (
                technician.completed_jobs or 0
            )


            efficiency = 0


            if total_jobs > 0:

                efficiency = round(
                    (completed_jobs / total_jobs) * 100,
                    2
                )


            # Don't show technicians
            # without work in selected filter

            if total_jobs == 0:
                continue


            results.append({

                "id": technician.id,

                "name": technician.name,

                "department": (
                    technician.department
                    or technician.designation
                    or "Workshop"
                ),

                "total_jobs": total_jobs,

                "completed_jobs": completed_jobs,

                "efficiency": efficiency,

            })


        # ======================================
        # SORT BEST TECHNICIANS
        # ======================================

        results.sort(

            key=lambda x: (

                x["efficiency"],

                x["completed_jobs"],

            ),

            reverse=True

        )


        return results[:5]