# Register your models here.

from .models import (
    ItemData,
    Employee,
    Surveyor,
    InsuranceCompany,
    CompanySetup,
    Announcement,
    Branch,
    GateInEntry,
)
from django.contrib import admin
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
