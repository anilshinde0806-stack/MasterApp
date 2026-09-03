# Register your models here.
from django.contrib import admin
from .models import JobCardQualityCheck, JobCardType
from .models import QualityCheckItem
from core.models import JobCardQualityCheck
from .models import (
    ItemData,
    Employee,
    Surveyor,
    InsuranceCompany,
    CompanySetup,
    Announcement,
    Branch,
    GateInEntry,
    UserLoginActivity,
)

admin.site.register(ItemData)
admin.site.register(InsuranceCompany)
admin.site.register(Employee)
admin.site.register(Surveyor)

admin.site.register(CompanySetup)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "claim_no_alias",
        "jobcard_no_alias",
        "city",
        "is_head_office",
        "is_active",
    ]
    list_filter = ["is_active", "is_head_office", "city"]
    search_fields = [
        "code",
        "name",
        "claim_no_alias",
        "jobcard_no_alias",
        "city",
        "mobile",
        "email",
        "gst_no",
    ]


@admin.register(GateInEntry)
class GateInEntryAdmin(admin.ModelAdmin):
    list_display = [
        "registration_no",
        "current_km",
        "service_type",
        "gate_in_datetime",
        "branch",
        "status",
        "jobcard",
        "entered_by",
        "cancelled_by",
    ]
    list_filter = ["service_type", "status", "branch", "gate_in_datetime"]
    search_fields = ["registration_no", "jobcard__job_no", "remarks", "cancellation_remark"]


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "notice_type",
        "is_active",
        "show_once",
        "created_at",
    ]

    list_filter = [
        "notice_type",
        "is_active",
        "show_once",
    ]

    search_fields = [
        "title",
        "message",
    ]


@admin.register(UserLoginActivity)
class UserLoginActivityAdmin(admin.ModelAdmin):
    list_display = ["user", "login_at", "ip_address", "session_key"]
    list_filter = ["login_at"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "ip_address"]
    readonly_fields = ["user", "login_at", "ip_address", "user_agent", "session_key"]



@admin.register(JobCardQualityCheck)
class JobCardQualityCheckAdmin(admin.ModelAdmin):
    list_display = [
        "jobcard",
        "inspector",
        "completed",
        "completed_at",
        "updated_at",
    ]

    list_filter = [
        "completed",
        "paint_finish",
        "road_test",
        "washing_done",
        "final_inspection",
    ]

    search_fields = [
        "jobcard__job_no",
        "remarks",
        "inspector__username",
        "inspector__first_name",
        "inspector__last_name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]
class QualityCheckItemInline(admin.TabularInline):
    model = QualityCheckItem
    extra = 0

    fields = (
        "item_name",
        "category",
        "status",
        "remarks",
        "checked_by",
        "checked_at",
    )

    readonly_fields = (
        "checked_by",
        "checked_at",
    )

    @admin.register(JobCardType)
    class JobCardTypeAdmin(admin.ModelAdmin):
        list_display = (
            "name",
            "display_order",
            "is_active",
        )

        list_filter = (
            "is_active",
        )

        search_fields = (
            "name",
        )

        ordering = (
            "display_order",
            "name",
        )