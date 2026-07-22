from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils.parser_utils import clean_text, parse_mobile_date
from core.models import Customer, Vehicle, VehicleModel, VehicleVariant
from core.validators import (
    VEHICLE_NUMBER_ERROR,
    is_valid_vehicle_number,
    normalize_vehicle_number,
)


def get_optional(model, pk):
    if not pk:
        return None
    return model.objects.filter(pk=pk).first()


class MobileVehicleSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        if len(query) < 2:
            return Response({"vehicles": []})

        vehicles = (
            Vehicle.objects.select_related("customer", "model", "variant")
            .filter(
                Q(registration_no__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(customer__mobile_no__icontains=query)
            )
            .order_by("registration_no")[:15]
        )

        return Response(
            {
                "vehicles": [
                    {
                        "id": vehicle.id,
                        "registration_no": vehicle.registration_no,
                        "customer": vehicle.customer.name if vehicle.customer_id else "",
                        "mobile_no": vehicle.customer.mobile_no if vehicle.customer_id else "",
                        "model": vehicle.model.name if vehicle.model_id else "",
                        "variant": vehicle.variant.name if vehicle.variant_id else "",
                        "label": (
                            f"{vehicle.registration_no} | "
                            f"{vehicle.customer.name if vehicle.customer_id else ''} | "
                            f"{vehicle.model.name if vehicle.model_id else ''}"
                        ),
                    }
                    for vehicle in vehicles
                ]
            }
        )

def mobile_vehicle_payload(vehicle):
    return {
        "id": vehicle.id,
        "registration_no": vehicle.registration_no,
        "customer_id": vehicle.customer_id,
        "customer": vehicle.customer.name if vehicle.customer_id else "",
        "customer_mobile": vehicle.customer.mobile_no if vehicle.customer_id else "",
        "model_id": vehicle.model_id,
        "model": vehicle.model.name if vehicle.model_id else "",
        "variant_id": vehicle.variant_id,
        "variant": vehicle.variant.name if vehicle.variant_id else "",
        "chassis_no": vehicle.chassis_no or "",
        "engine_no": vehicle.engine_no or "",
        "color": vehicle.color or "",
        "sale_date": vehicle.sale_date.isoformat() if vehicle.sale_date else "",
        "vehicle_type": vehicle.vehicle_type or "",
    }

class MobileVehicleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        vehicles = Vehicle.objects.select_related("customer", "model", "variant")
        if query:
            vehicles = vehicles.filter(
                Q(registration_no__icontains=query)
                | Q(customer__name__icontains=query)
                | Q(customer__mobile_no__icontains=query)
                | Q(model__name__icontains=query)
                | Q(variant__name__icontains=query)
            )

        return Response(
            {
                "vehicles": [
                    mobile_vehicle_payload(vehicle)
                    for vehicle in vehicles.order_by("registration_no")[:100]
                ]
            }
        )

class MobileVehicleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        vehicle = (
            Vehicle.objects.select_related("customer", "model", "variant")
            .filter(pk=pk)
            .first()
        )
        if not vehicle:
            return Response({"detail": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"vehicle": mobile_vehicle_payload(vehicle)})

class MobileVehicleModelCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = clean_text((request.data or {}).get("name"))
        if not name:
            return Response(
                {"errors": {"name": "Model Name required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = VehicleModel.objects.filter(name__iexact=name).first()
        created = False
        if not model:
            model = VehicleModel.objects.create(name=name)
            created = True
        return Response(
            {
                "message": "Vehicle model created successfully." if created else "Vehicle model already exists.",
                "model": {"id": model.id, "label": model.name},
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

class MobileVehicleVariantCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        name = clean_text(data.get("name"))
        model = get_optional(VehicleModel, data.get("model"))
        errors = {}

        if not model:
            errors["model"] = "Select Vehicle Model first."
        if not name:
            errors["name"] = "Variant Name required."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        variant = VehicleVariant.objects.filter(
            model=model,
            name__iexact=name,
        ).first()
        created = False
        if not variant:
            variant = VehicleVariant.objects.create(model=model, name=name)
            created = True
        return Response(
            {
                "message": "Vehicle variant created successfully." if created else "Vehicle variant already exists.",
                "variant": {
                    "id": variant.id,
                    "label": variant.name,
                    "model_id": variant.model_id,
                },
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

class MobileVehicleCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        errors = {}

        registration_no = clean_text(data.get("registrationNo")).upper()
        customer_name = clean_text(data.get("customerName"))
        customer_mobile = clean_text(data.get("customerMobile"))
        customer_id = data.get("customerId")
        chassis_no = clean_text(data.get("chassisNo")).upper()
        engine_no = clean_text(data.get("engineNo")).upper()
        color = clean_text(data.get("color"))
        sale_date = parse_mobile_date(data.get("saleDate"))
        vehicle_type = clean_text(data.get("vehicleType")) or "PV"
        model = get_optional(VehicleModel, data.get("model"))
        variant = get_optional(VehicleVariant, data.get("variant"))

        if not registration_no:
            errors["registrationNo"] = "Vehicle Registration No required."
        elif not is_valid_vehicle_number(registration_no):
            errors["registrationNo"] = VEHICLE_NUMBER_ERROR
        elif Vehicle.objects.filter(registration_no__iexact=registration_no).exists():
            errors["registrationNo"] = "Vehicle Registration No already exists."

        selected_customer = get_optional(Customer, customer_id)

        if not selected_customer and not customer_name:
            errors["customerName"] = "Customer Name required."
        if not chassis_no:
            errors["chassisNo"] = "Chassis No required."
        elif Vehicle.objects.filter(chassis_no__iexact=chassis_no).exists():
            errors["chassisNo"] = "Chassis No already exists."

        if not engine_no:
            errors["engineNo"] = "Engine No required."
        elif Vehicle.objects.filter(engine_no__iexact=engine_no).exists():
            errors["engineNo"] = "Engine No already exists."

        if not model:
            errors["model"] = "Vehicle Model required."
        if not variant:
            errors["variant"] = "Vehicle Variant required."
        if not color:
            errors["color"] = "Color required."
        if not sale_date:
            errors["saleDate"] = "Sale Date required."
        if vehicle_type not in dict(Vehicle.VEHICLE_TYPE_CHOICES):
            errors["vehicleType"] = "Select valid Vehicle Type."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            customer = selected_customer
            if not customer and customer_mobile:
                customer = Customer.objects.filter(mobile_no=customer_mobile).first()
            if not customer:
                customer = Customer.objects.create(
                    name=customer_name,
                    mobile_no=customer_mobile or None,
                )

            vehicle = Vehicle.objects.create(
                registration_no=registration_no,
                chassis_no=chassis_no,
                engine_no=engine_no,
                model=model,
                variant=variant,
                color=color,
                sale_date=sale_date,
                vehicle_type=vehicle_type,
                customer=customer,
            )

        return Response(
            {
                "message": "Vehicle created successfully.",
                "vehicle": {
                    "id": vehicle.id,
                    "registration_no": vehicle.registration_no,
                    "customer": customer.name,
                    "mobile_no": customer.mobile_no or "",
                    "model": model.name,
                    "variant": variant.name,
                },
            },
            status=status.HTTP_201_CREATED,
        )

class MobileVehicleSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        data = request.data or {}
        errors = {}

        vehicle = Vehicle.objects.filter(pk=pk).first() if pk else None
        if pk and not vehicle:
            return Response({"detail": "Vehicle not found."}, status=status.HTTP_404_NOT_FOUND)

        registration_no = normalize_vehicle_number(data.get("registrationNo"))
        customer_name = clean_text(data.get("customerName"))
        customer_mobile = clean_text(data.get("customerMobile"))
        customer_id = data.get("customerId")
        chassis_no = clean_text(data.get("chassisNo")).upper()
        engine_no = clean_text(data.get("engineNo")).upper()
        color = clean_text(data.get("color"))
        sale_date = parse_mobile_date(data.get("saleDate"))
        vehicle_type = clean_text(data.get("vehicleType")) or "PV"
        model = get_optional(VehicleModel, data.get("model"))
        variant = get_optional(VehicleVariant, data.get("variant"))
        selected_customer = get_optional(Customer, customer_id)

        registration_qs = Vehicle.objects.filter(registration_no__iexact=registration_no) if registration_no else Vehicle.objects.none()
        chassis_qs = Vehicle.objects.filter(chassis_no__iexact=chassis_no) if chassis_no else Vehicle.objects.none()
        engine_qs = Vehicle.objects.filter(engine_no__iexact=engine_no) if engine_no else Vehicle.objects.none()
        if vehicle:
            registration_qs = registration_qs.exclude(pk=vehicle.pk)
            chassis_qs = chassis_qs.exclude(pk=vehicle.pk)
            engine_qs = engine_qs.exclude(pk=vehicle.pk)

        if not registration_no:
            errors["registrationNo"] = "Vehicle Registration No required."
        elif not is_valid_vehicle_number(registration_no):
            errors["registrationNo"] = VEHICLE_NUMBER_ERROR
        elif registration_qs.exists():
            errors["registrationNo"] = "Vehicle Registration No already exists."

        if not selected_customer and not customer_name:
            errors["customerName"] = "Customer Name required."
        if not chassis_no:
            errors["chassisNo"] = "Chassis No required."
        elif chassis_qs.exists():
            errors["chassisNo"] = "Chassis No already exists."

        if not engine_no:
            errors["engineNo"] = "Engine No required."
        elif engine_qs.exists():
            errors["engineNo"] = "Engine No already exists."

        if not model:
            errors["model"] = "Vehicle Model required."
        if not variant:
            errors["variant"] = "Vehicle Variant required."
        elif model and variant.model_id != model.id:
            errors["variant"] = "Select variant for selected model."
        if not color:
            errors["color"] = "Color required."
        if not sale_date:
            errors["saleDate"] = "Sale Date required."
        if vehicle_type not in dict(Vehicle.VEHICLE_TYPE_CHOICES):
            errors["vehicleType"] = "Select valid Vehicle Type."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            customer = selected_customer
            if not customer and customer_mobile:
                customer = Customer.objects.filter(mobile_no=customer_mobile).first()
            if not customer:
                customer = Customer.objects.create(
                    name=customer_name,
                    mobile_no=customer_mobile or None,
                )

            if not vehicle:
                vehicle = Vehicle()
            vehicle.registration_no = registration_no
            vehicle.chassis_no = chassis_no
            vehicle.engine_no = engine_no
            vehicle.model = model
            vehicle.variant = variant
            vehicle.color = color
            vehicle.sale_date = sale_date
            vehicle.vehicle_type = vehicle_type
            vehicle.customer = customer
            vehicle.save()

        return Response(
            {
                "message": "Vehicle saved successfully.",
                "vehicle": mobile_vehicle_payload(vehicle),
            },
            status=status.HTTP_201_CREATED if not pk else status.HTTP_200_OK,
        )
