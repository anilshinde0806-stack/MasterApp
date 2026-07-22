from django.test import SimpleTestCase
from django.urls import resolve, reverse

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


class MobileAccountRoutingTests(SimpleTestCase):
    def assert_view_class(self, route_name, expected_view, *, kwargs=None):
        match = resolve(reverse(route_name, kwargs=kwargs))
        self.assertIs(match.func.view_class, expected_view)

    def test_account_routes_use_module_adapters(self):
        self.assert_view_class("mobile_login", MobileLoginView)
        self.assert_view_class("mobile_me", MobileMeView)
        self.assert_view_class("mobile_menu", MobileMenuView)
        self.assert_view_class(
            "mobile_profile_photo_upload",
            MobileProfilePhotoUploadView,
        )

    def test_notification_routes_use_module_adapters(self):
        self.assert_view_class("mobile_notifications", MobileNotificationListView)
        self.assert_view_class(
            "mobile_notification_read",
            MobileNotificationReadView,
            kwargs={"pk": 1},
        )

    def test_customer_routes_use_module_adapters(self):
        self.assert_view_class("mobile_customers", MobileCustomerListView)
        self.assert_view_class("mobile_customer_search", MobileCustomerSearchView)
        self.assert_view_class("mobile_customer_create", MobileCustomerSaveView)
        self.assert_view_class(
            "mobile_customer_update",
            MobileCustomerSaveView,
            kwargs={"pk": 1},
        )

    def test_vehicle_routes_use_module_adapters(self):
        routes = [
            ("mobile_vehicles", MobileVehicleListView, None),
            ("mobile_vehicle_detail", MobileVehicleDetailView, {"pk": 1}),
            ("mobile_vehicle_search", MobileVehicleSearchView, None),
            ("mobile_vehicle_model_create", MobileVehicleModelCreateView, None),
            ("mobile_vehicle_variant_create", MobileVehicleVariantCreateView, None),
            ("mobile_vehicle_create", MobileVehicleCreateView, None),
            ("mobile_vehicle_save", MobileVehicleSaveView, None),
            ("mobile_vehicle_update", MobileVehicleSaveView, {"pk": 1}),
        ]
        for route_name, view_class, kwargs in routes:
            with self.subTest(route_name=route_name):
                self.assert_view_class(route_name, view_class, kwargs=kwargs)

    def test_jobcard_routes_use_module_adapters(self):
        routes = [
            ("mobile_jobcards", MobileJobcardListView, None),
            ("mobile_jobcard_next_no", MobileNextJobNoView, None),
            ("mobile_jobcard_save", MobileJobcardSaveView, None),
            ("mobile_jobcard_detail", MobileJobcardDetailView, {"pk": 1}),
            ("mobile_jobcard_update", MobileJobcardSaveView, {"pk": 1}),
            ("mobile_jobcard_signatures", MobileJobcardSignatureSaveView, {"pk": 1}),
            ("mobile_jobcard_actions", MobileJobcardActionLinksView, {"pk": 1}),
            (
                "mobile_jobcard_vehicle_condition_photo_upload",
                MobileJobcardVehiclePhotoUploadView,
                {"pk": 1},
            ),
        ]
        for route_name, view_class, kwargs in routes:
            with self.subTest(route_name=route_name):
                self.assert_view_class(route_name, view_class, kwargs=kwargs)

    def test_workshop_routes_use_module_adapters(self):
        routes = [
            ("mobile_my_work", MobileMyWorkListView, None),
            ("mobile_my_work_action", MobileMyWorkActionView, {"progress_id": 1}),
            ("MobileWorkAllocationView", MobileWorkAllocationView, {"pk": 1}),
            ("MobileRepairProgressView", MobileRepairProgressView, {"pk": 1}),
            ("repair-progress-photos", RepairProgressPhotoListAPIView, {"job_id": 1}),
            ("repair-progress-photo-upload", RepairProgressPhotoUploadAPIView, {"job_id": 1}),
            (
                "repair-progress-photo-delete",
                RepairProgressPhotoDeleteAPIView,
                {"job_id": 1, "photo_id": 1},
            ),
            ("mobile-my-work-detail", MobileMyWorkDetailView, {"progress_id": 1}),
            ("mobile-my-work-update", MobileMyWorkUpdateView, {"progress_id": 1}),
        ]
        for route_name, view_class, kwargs in routes:
            with self.subTest(route_name=route_name):
                self.assert_view_class(route_name, view_class, kwargs=kwargs)
