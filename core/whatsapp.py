import requests

from config import settings
from .models import CompanySetup


def normalize_india_mobile(mobile):
    mobile = "".join(ch for ch in str(mobile or "") if ch.isdigit())
    if len(mobile) == 10:
        return "91" + mobile
    return mobile


def send_whatsapp_template_message(mobile, template_name, language_code="en_US", parameters=None):
    token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "") or getattr(settings, "WHATSAPP_TOKEN", "")
    phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    graph_version = getattr(settings, "WHATSAPP_GRAPH_VERSION", "v23.0")

    if not token or not phone_number_id:
        return {
            "success": False,
            "status_code": 400,
            "response": "WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID are required in .env.",
        }

    mobile = normalize_india_mobile(mobile)
    if len(mobile) < 11:
        return {
            "success": False,
            "status_code": 400,
            "response": "Enter valid WhatsApp mobile number with country code.",
        }

    payload = {
        "messaging_product": "whatsapp",
        "to": mobile,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if parameters:
        payload["template"]["components"] = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(value or "-")}
                    for value in parameters
                ],
            }
        ]

    try:
        response = requests.post(
            f"https://graph.facebook.com/{graph_version}/{phone_number_id}/messages",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        return {
            "success": response.status_code in [200, 201],
            "status_code": response.status_code,
            "response": response.text,
        }
    except requests.RequestException as error:
        return {
            "success": False,
            "status_code": 500,
            "response": str(error),
        }


def send_advisor_assigned_whatsapp(claim):
    if not claim or not claim.employee_id or not claim.vehicle_id:
        return {"success": False, "response": "Claim, advisor, and vehicle are required."}

    vehicle = claim.vehicle
    customer = vehicle.customer if vehicle and vehicle.customer_id else None
    advisor = claim.employee
    if not customer or not customer.mobile_no:
        return {"success": False, "response": "Customer mobile number is required."}

    branch_name = claim.branch.name if claim.branch_id else ""
    company = CompanySetup.objects.first()
    company_name = branch_name or (company.company_name if company else "Shreeji Automart, Surat")

    template_name = getattr(settings, "WHATSAPP_ADVISOR_ASSIGN_TEMPLATE", "service_advisor_intro")
    parameters = [
        advisor.name or "-",
        advisor.mobile_no or "-",
        getattr(settings, "WHATSAPP_BODYSHOP_MANAGER_NAME", "Mr. Kaushal"),
        getattr(settings, "WHATSAPP_BODYSHOP_MANAGER_PHONE", "8980007687"),
        getattr(settings, "WHATSAPP_BODYSHOP_HEAD_NAME", "Mr. Yatin"),
        getattr(settings, "WHATSAPP_BODYSHOP_HEAD_PHONE", "8980007630"),
        getattr(settings, "WHATSAPP_AREA_MANAGER_NAME", "Mr. Gunjan Patel"),
        getattr(settings, "WHATSAPP_AREA_MANAGER_EMAIL", "patel.gunjan@tatamotors.com"),
        getattr(settings, "WHATSAPP_CUSTOMER_CARE_EMAIL", "customercare.support@tatamotors.com"),
        company_name,
    ]
    if template_name == "hello_world":
        parameters = []

    return send_whatsapp_template_message(
        customer.mobile_no,
        template_name,
        getattr(settings, "WHATSAPP_ADVISOR_ASSIGN_LANGUAGE", "en_US"),
        parameters,
    )
