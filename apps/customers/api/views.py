from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils.parser_utils import clean_text
from core.models import Customer


class MobileCustomerSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        if len(query) < 2:
            return Response({"customers": []})

        customers = (
            Customer.objects.filter(
                Q(name__icontains=query)
                | Q(mobile_no__icontains=query)
                | Q(email__icontains=query)
                | Q(customer_code__icontains=query)
                | Q(whatsapp_no__icontains=query)
                | Q(company_name__icontains=query)
            )
            .order_by("name")[:15]
        )

        return Response(
            {
                "customers": [
                    {
                        "id": customer.id,
                        "name": customer.name,
                        "mobile_no": customer.mobile_no or "",
                        "email": customer.email or "",
                        "city": customer.city or "",
                        "customer_code": customer.customer_code or "",
                        "customer_type": customer.customer_type or "",
                        "label": f"{customer.name} | {customer.mobile_no or '-'}",
                    }
                    for customer in customers
                ]
            }
        )

def mobile_customer_payload(customer):
    return {
        "id": customer.id,
        "customer_code": customer.customer_code or "",
        "customer_type": customer.customer_type or "Individual",
        "salutation": customer.salutation or "",
        "name": customer.name,
        "gender": customer.gender or "",
        "date_of_birth": customer.date_of_birth.isoformat() if customer.date_of_birth else "",
        "anniversary_date": customer.anniversary_date.isoformat() if customer.anniversary_date else "",
        "gst_registered": customer.gst_registered,
        "pan_no": customer.pan_no or "",
        "aadhaar_no": customer.aadhaar_no or "",
        "mobile_no": customer.mobile_no or "",
        "alternate_mobile_no": customer.alternate_mobile_no or "",
        "whatsapp_no": customer.whatsapp_no or "",
        "email": customer.email or "",
        "preferred_contact_method": customer.preferred_contact_method or "Mobile",
        "address_line_1": customer.address_line_1 or "",
        "address_line_2": customer.address_line_2 or "",
        "city": customer.city or "",
        "state": customer.state or "",
        "address": customer.address or "",
        "gst_no": customer.gst_no or "",
        "pin_code": customer.pin_code or "",
        "country": customer.country or "India",
        "company_name": customer.company_name or "",
        "contact_person": customer.contact_person or "",
        "designation": customer.designation or "",
        "company_gst_no": customer.company_gst_no or "",
        "is_active": customer.is_active,
    }

class MobileCustomerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = clean_text(request.GET.get("q"))
        customers = Customer.objects.all()
        if query:
            customers = customers.filter(
                Q(name__icontains=query)
                | Q(mobile_no__icontains=query)
                | Q(email__icontains=query)
                | Q(city__icontains=query)
                | Q(customer_code__icontains=query)
                | Q(whatsapp_no__icontains=query)
                | Q(company_name__icontains=query)
            )

        return Response(
            {
                "customers": [
                    mobile_customer_payload(customer)
                    for customer in customers.order_by("name")[:100]
                ]
            }
        )

class MobileCustomerSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        data = request.data or {}
        name = clean_text(data.get("name"))
        mobile_no = clean_text(data.get("mobileNo"))
        customer_type = clean_text(data.get("customerType")) or "Individual"
        gst_registered = bool(data.get("gstRegistered"))
        customer = Customer.objects.filter(pk=pk).first() if pk else None
        errors = {}

        if pk and not customer:
            return Response({"detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        if not name:
            errors["name"] = "Customer Name required."
        if customer_type not in dict(Customer.CUSTOMER_TYPE_CHOICES):
            errors["customerType"] = "Invalid Customer Type."
        if gst_registered and not clean_text(data.get("gstNo")):
            errors["gstNo"] = "GST No required when GST Registered is Yes."
        mobile_qs = Customer.objects.filter(mobile_no=mobile_no) if mobile_no else Customer.objects.none()
        if customer:
            mobile_qs = mobile_qs.exclude(pk=customer.pk)
        if mobile_no and mobile_qs.exists():
            errors["mobileNo"] = "Customer Mobile already exists."

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        if not customer:
            customer = Customer()

        customer.customer_type = customer_type
        customer.salutation = clean_text(data.get("salutation"))
        customer.name = name
        customer.gender = clean_text(data.get("gender"))
        customer.date_of_birth = parse_date(clean_text(data.get("dateOfBirth"))) if clean_text(data.get("dateOfBirth")) else None
        customer.anniversary_date = parse_date(clean_text(data.get("anniversaryDate"))) if clean_text(data.get("anniversaryDate")) else None
        customer.gst_registered = gst_registered
        customer.pan_no = clean_text(data.get("panNo")) or None
        customer.aadhaar_no = clean_text(data.get("aadhaarNo")) or None
        customer.mobile_no = mobile_no or None
        customer.alternate_mobile_no = clean_text(data.get("alternateMobileNo")) or None
        customer.whatsapp_no = clean_text(data.get("whatsappNo")) or None
        customer.email = clean_text(data.get("email")) or None
        customer.preferred_contact_method = clean_text(data.get("preferredContactMethod")) or "Mobile"
        customer.address_line_1 = clean_text(data.get("addressLine1")) or None
        customer.address_line_2 = clean_text(data.get("addressLine2")) or None
        customer.city = clean_text(data.get("city")) or None
        customer.state = clean_text(data.get("state")) or None
        customer.address = clean_text(data.get("address")) or None
        customer.gst_no = clean_text(data.get("gstNo")) or None
        customer.pin_code = clean_text(data.get("pinCode")) or None
        customer.country = clean_text(data.get("country")) or "India"
        customer.company_name = clean_text(data.get("companyName")) or None
        customer.contact_person = clean_text(data.get("contactPerson")) or None
        customer.designation = clean_text(data.get("designation")) or None
        customer.company_gst_no = clean_text(data.get("companyGstNo")) or None
        customer.save()

        return Response(
            {
                "message": "Customer saved successfully.",
                "customer": mobile_customer_payload(customer),
            },
            status=status.HTTP_201_CREATED if not pk else status.HTTP_200_OK,
        )
