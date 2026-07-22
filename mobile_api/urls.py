from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .dashboardviews.branch import MobileBranchListView
from .dashboardviews.dashboard import NewMobileDashboardView
from apps.claims.api.views import (
    ClaimSaveView,
    MobileClaimDetailView,
    MobileClaimListView,
)
from apps.accounts.api.views import (
    MobileLoginView,
    MobileMeView,
    MobileMenuView,
    MobileProfilePhotoUploadView,
)
from apps.notifications.api.views import (
    MobileNotificationListView,
    MobileNotificationReadView,
)
from apps.customers.api.views import (
    MobileCustomerListView,
    MobileCustomerSaveView,
    MobileCustomerSearchView,
)
from apps.vehicles.api.views import (
    MobileVehicleCreateView,
    MobileVehicleDetailView,
    MobileVehicleListView,
    MobileVehicleModelCreateView,
    MobileVehicleSaveView,
    MobileVehicleVariantCreateView,
    MobileVehicleSearchView,
)
from apps.jobcards.api.views import (
    MobileJobcardActionLinksView,
    MobileJobcardDetailView,
    MobileJobcardListView,
    MobileJobcardSaveView,
    MobileJobcardSignatureSaveView,
    MobileJobcardVehiclePhotoUploadView,
    MobileNextJobNoView,
)
from apps.workshop.api.views import (
    MobileMyWorkActionView,
    MobileMyWorkDetailView,
    MobileMyWorkListView,
    MobileMyWorkUpdateView,
    MobileRepairProgressView,
    MobileWorkAllocationView,
    RepairProgressPhotoDeleteAPIView,
    RepairProgressPhotoListAPIView,
    RepairProgressPhotoUploadAPIView,
)
from .views import (
    MobileClaimEntryOptionsView,
    MobileClaimVehicleCheckView,
    MobileDashboardView,
    MobileGateInEntryView,
    MobileNextClaimNoView,
)


urlpatterns = [
    path("login/", MobileLoginView.as_view(), name="mobile_login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="mobile_token_refresh"),
    path("me/", MobileMeView.as_view(), name="mobile_me"),
    path("profile-photo/", MobileProfilePhotoUploadView.as_view(), name="mobile_profile_photo_upload"),
    path("menu/", MobileMenuView.as_view(), name="mobile_menu"),
    path("notifications/", MobileNotificationListView.as_view(), name="mobile_notifications"),
    path("notifications/<int:pk>/read/", MobileNotificationReadView.as_view(), name="mobile_notification_read"),
    path("dashboard/", MobileDashboardView.as_view(), name="mobile_dashboard"),
    path("gate-in/", MobileGateInEntryView.as_view(), name="mobile_gate_in"),
    path("gate-in/<int:pk>/", MobileGateInEntryView.as_view(), name="mobile_gate_in_update"),
    path("my-work/", MobileMyWorkListView.as_view(), name="mobile_my_work"),
    path("my-work/<int:progress_id>/action/",MobileMyWorkActionView.as_view(),name="mobile_my_work_action",),
    path("claims/", MobileClaimListView.as_view(), name="mobile_claims"),
    path("claims/<int:pk>/", MobileClaimDetailView.as_view(), name="mobile_claim_detail"),
    path("claims/next-no/", MobileNextClaimNoView.as_view(), name="mobile_claim_next_no"),
    path("claims/check-vehicle/", MobileClaimVehicleCheckView.as_view(), name="mobile_claim_check_vehicle"),
    path("claims/save/", ClaimSaveView.as_view(), name="mobile_claim_save"),
    path("claims/<int:pk>/save/", ClaimSaveView.as_view(), name="mobile_claim_update"),
    path("claim-entry-options/", MobileClaimEntryOptionsView.as_view(), name="mobile_claim_entry_options"),
    path("customers/", MobileCustomerListView.as_view(), name="mobile_customers"),
    path("customers/search/", MobileCustomerSearchView.as_view(), name="mobile_customer_search"),
    path("customers/create/", MobileCustomerSaveView.as_view(), name="mobile_customer_create"),
    path("customers/<int:pk>/save/", MobileCustomerSaveView.as_view(), name="mobile_customer_update"),
    path("vehicles/", MobileVehicleListView.as_view(), name="mobile_vehicles"),
    path("vehicles/<int:pk>/", MobileVehicleDetailView.as_view(), name="mobile_vehicle_detail"),
    path("vehicles/search/", MobileVehicleSearchView.as_view(), name="mobile_vehicle_search"),
    path("vehicles/models/create/", MobileVehicleModelCreateView.as_view(), name="mobile_vehicle_model_create"),
    path("vehicles/variants/create/", MobileVehicleVariantCreateView.as_view(), name="mobile_vehicle_variant_create"),
    path("vehicles/create/", MobileVehicleCreateView.as_view(), name="mobile_vehicle_create"),
    path("vehicles/save/", MobileVehicleSaveView.as_view(), name="mobile_vehicle_save"),
    path("vehicles/<int:pk>/save/", MobileVehicleSaveView.as_view(), name="mobile_vehicle_update"),
    path("jobcards/", MobileJobcardListView.as_view(), name="mobile_jobcards"),
    path("jobcards/next-no/", MobileNextJobNoView.as_view(), name="mobile_jobcard_next_no"),
    path("jobcards/save/", MobileJobcardSaveView.as_view(), name="mobile_jobcard_save"),
    path("jobcards/<int:pk>/", MobileJobcardDetailView.as_view(), name="mobile_jobcard_detail"),
    path("jobcards/<int:pk>/save/", MobileJobcardSaveView.as_view(), name="mobile_jobcard_update"),
    path("jobcards/<int:pk>/signatures/", MobileJobcardSignatureSaveView.as_view(), name="mobile_jobcard_signatures"),
    path("jobcards/<int:pk>/actions/", MobileJobcardActionLinksView.as_view(), name="mobile_jobcard_actions"),
    path("jobcards/<int:pk>/vehicle-condition-photos/", MobileJobcardVehiclePhotoUploadView.as_view(), name="mobile_jobcard_vehicle_condition_photo_upload"),
    path("jobcards/<int:pk>/allocation/",MobileWorkAllocationView.as_view(), name="MobileWorkAllocationView"),
    path("jobcards/<int:pk>/repair-progress/",MobileRepairProgressView.as_view(), name="MobileRepairProgressView"),
    path("jobcards/<int:job_id>/repair-progress/photos/",RepairProgressPhotoListAPIView.as_view(),name="repair-progress-photos",),
# Upload Photo
    path("jobcards/<int:job_id>/repair-progress/photos/upload/",RepairProgressPhotoUploadAPIView.as_view(),name="repair-progress-photo-upload",),
path(
    "jobcards/<int:job_id>/repair-progress/photos/<int:photo_id>/",
    RepairProgressPhotoDeleteAPIView.as_view(),
    name="repair-progress-photo-delete",
),
path(
    "my-work/<int:progress_id>/",
    MobileMyWorkDetailView.as_view(),name="mobile-my-work-detail",
),
path(
        "my-work/<int:progress_id>/update/",
        MobileMyWorkUpdateView.as_view(),
        name="mobile-my-work-update",
    ),

    path(
        "newdashboard/",
        NewMobileDashboardView.as_view(),
        name="mobile-dashboard",
    ),
path(
        "branches/",
        MobileBranchListView.as_view(),
        name="mobile-branches",
    ),

]
