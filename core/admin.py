# Register your models here.

from .models import ItemData, Employee, Surveyor, InsuranceCompany, CompanySetup, Announcement
from django.contrib import admin
admin.site.register(ItemData)
admin.site.register(InsuranceCompany)
admin.site.register(Employee)
admin.site.register(Surveyor)

admin.site.register(CompanySetup)
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