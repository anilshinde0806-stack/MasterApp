from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Branch,
    Claim,
    ClaimStageCode,
    CompanySetup,
    Customer,
    Employee,
    InsuranceCompany,
    ItemData,
    JobCard,
    JobCardInventory,
    JobCardLabour,
    JobCardPart,
    JobCardTyreInventory,
    Surveyor,
    Vehicle,
    VehicleModel,
    VehicleVariant,
)


class Command(BaseCommand):
    help = "Seed a clean client-demo dataset after migrations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Demo@123",
            help="Password for all demo users.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        today = timezone.localdate()
        now = timezone.now()

        company, _ = CompanySetup.objects.update_or_create(
            company_name="Shreeji Automart",
            defaults={
                "address": "Ring Road",
                "city": "Surat",
                "state": "Gujarat",
                "pincode": "395002",
                "mobile": "8980007687",
                "email": "demo@shreejiautomart.example",
                "website": "https://demo-bodyshop.example",
                "gst_no": "24ABCDE1234F1Z5",
                "invoice_footer": "Thank you for choosing our bodyshop service.",
            },
        )

        head_office, _ = Branch.objects.update_or_create(
            code="HO",
            defaults={
                "parent": company,
                "name": "Head Office",
                "city": "Surat",
                "state": "Gujarat",
                "mobile": "8980007687",
                "email": "ho@shreejiautomart.example",
                "is_head_office": True,
                "is_active": True,
            },
        )
        bodyshop_branch, _ = Branch.objects.update_or_create(
            code="BS-SURAT",
            defaults={
                "parent": company,
                "name": "Surat Bodyshop",
                "city": "Surat",
                "state": "Gujarat",
                "mobile": "8980007630",
                "email": "bodyshop@shreejiautomart.example",
                "is_active": True,
            },
        )

        def demo_user(username, first_name, is_superuser=False):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "email": f"{username}@demo.example",
                    "is_staff": is_superuser,
                    "is_superuser": is_superuser,
                },
            )
            if created or not user.check_password(password):
                user.set_password(password)
            user.first_name = first_name
            user.email = f"{username}@demo.example"
            user.is_active = True
            if is_superuser:
                user.is_staff = True
                user.is_superuser = True
            user.save()
            return user

        users = {
            "admin": demo_user("demo_admin", "Demo Admin", True),
            "manager": demo_user("demo_manager", "Demo Manager"),
            "advisor": demo_user("demo_advisor", "Anil Shinde"),
            "denter": demo_user("demo_denter", "Demo Denter"),
            "painter": demo_user("demo_painter", "Demo Painter"),
            "technician": demo_user("demo_technician", "Demo Technician"),
            "reception": demo_user("demo_reception", "Demo Reception"),
        }

        employees = {}
        employee_specs = [
            ("manager", "EMP001", "Demo Manager", "MANAGER", "Bodyshop Manager", "Back Office", head_office, "8980007687"),
            ("advisor", "EMP002", "Anil Shinde", "Advisor", "Service Advisor", "Front Office", bodyshop_branch, "7984801358"),
            ("denter", "EMP003", "Demo Denter", "STAFF", "Denter", "Floor", bodyshop_branch, "9000000001"),
            ("painter", "EMP004", "Demo Painter", "STAFF", "Painter", "Floor", bodyshop_branch, "9000000002"),
            ("technician", "EMP005", "Demo Technician", "STAFF", "Technician", "Floor", bodyshop_branch, "9000000003"),
            ("reception", "EMP006", "Demo Reception", "STAFF", "Reception", "Front Office", bodyshop_branch, "9000000004"),
        ]
        for key, code, name, employee_type, designation, department, branch, mobile in employee_specs:
            employee, _ = Employee.objects.update_or_create(
                employee_code=code,
                defaults={
                    "user": users[key],
                    "name": name,
                    "mobile_no": mobile[-10:],
                    "email": f"{key}@demo.example",
                    "employee_type": employee_type,
                    "designation": designation,
                    "department": department,
                    "branch": branch,
                    "joining_date": today - timedelta(days=365),
                    "is_active": True,
                },
            )
            employees[key] = employee

        insurer, _ = InsuranceCompany.objects.update_or_create(
            ins_co_name="TATA AIG General Insurance",
            branch="Surat",
            defaults={
                "city": "Surat",
                "state": "Gujarat",
                "pin_code": "395002",
                "cashless": True,
                "claim_manager_name": "Demo Claim Manager",
                "mobile_no": "9000012345",
                "email": "claims@demo-insurer.example",
            },
        )
        surveyor, _ = Surveyor.objects.update_or_create(
            name="Demo Surveyor",
            defaults={
                "mobile_no": "9000090000",
                "email": "surveyor@demo.example",
                "license_no": "SURV-DEMO-001",
                "company": "Demo Survey Services",
            },
        )

        nexon, _ = VehicleModel.objects.get_or_create(name="Nexon")
        punch, _ = VehicleModel.objects.get_or_create(name="Punch")
        nexon_xz, _ = VehicleVariant.objects.get_or_create(model=nexon, name="XZ Plus")
        punch_cng, _ = VehicleVariant.objects.get_or_create(model=punch, name="Adventure CNG")

        customers = []
        customer_specs = [
            ("Ramesh Patel", "9876500001", "Surat", "Gujarat", "Adajan, Surat", "395009"),
            ("Mehul Shah", "9876500002", "Surat", "Gujarat", "Vesu, Surat", "395007"),
            ("Priya Desai", "9876500003", "Surat", "Gujarat", "City Light, Surat", "395007"),
        ]
        for name, mobile, city, state, address, pin in customer_specs:
            customer, _ = Customer.objects.update_or_create(
                mobile_no=mobile,
                defaults={
                    "name": name,
                    "email": f"{name.lower().split()[0]}@demo.example",
                    "city": city,
                    "state": state,
                    "address": address,
                    "pin_code": pin,
                    "is_active": True,
                },
            )
            customers.append(customer)

        vehicle_specs = [
            ("GJ05AB1234", "DEMOCHASSIS001", "DEMOENGINE001", nexon, nexon_xz, "White", customers[0], "PV"),
            ("GJ05CD5678", "DEMOCHASSIS002", "DEMOENGINE002", punch, punch_cng, "Blue", customers[1], "PV"),
            ("GJ05EF9012", "DEMOCHASSIS003", "DEMOENGINE003", nexon, nexon_xz, "Grey", customers[2], "PV"),
        ]
        vehicles = []
        for reg_no, chassis, engine, model, variant, color, customer, vehicle_type in vehicle_specs:
            vehicle, _ = Vehicle.objects.update_or_create(
                registration_no=reg_no,
                defaults={
                    "chassis_no": chassis,
                    "engine_no": engine,
                    "model": model,
                    "variant": variant,
                    "color": color,
                    "sale_date": today - timedelta(days=700),
                    "vehicle_type": vehicle_type,
                    "customer": customer,
                },
            )
            vehicles.append(vehicle)

        for code, name, category, rate in [
            ("PANEL-001", "Front Bumper", "Body Parts", "8500"),
            ("PAINT-001", "Paint Material", "Consumable", "4200"),
            ("CLIP-001", "Bumper Clip Set", "Fastener", "650"),
        ]:
            ItemData.objects.update_or_create(
                item_code=code,
                defaults={
                    "item_name": name,
                    "category": category,
                    "rate": Decimal(rate),
                    "status": "Active",
                },
            )

        claim_specs = [
            ("CLM-DEMO-0001", vehicles[0], ClaimStageCode.ADVISOR_ASSIGNED, "Open"),
            ("CLM-DEMO-0002", vehicles[1], ClaimStageCode.ESTIMATE_CREATED, "Open"),
            ("CLM-DEMO-0003", vehicles[2], ClaimStageCode.CLAIM_CREATED, "Open"),
        ]
        claims = []
        for claim_no, vehicle, stage, status in claim_specs:
            claim, _ = Claim.objects.update_or_create(
                claim_no=claim_no,
                defaults={
                    "branch": bodyshop_branch,
                    "vehicle": vehicle,
                    "employee": employees["advisor"] if stage >= ClaimStageCode.ADVISOR_ASSIGNED else None,
                    "insurance_company": insurer,
                    "policy_no": f"POL-{claim_no[-4:]}",
                    "ic_claim_no": f"IC-{claim_no[-4:]}",
                    "claim_type": "Cashless",
                    "accident_date": today - timedelta(days=2),
                    "intimation_date": now - timedelta(days=1) if stage >= ClaimStageCode.INTIMATION else None,
                    "survey_date": now if stage >= ClaimStageCode.SURVEY else None,
                    "surveyor": surveyor if stage >= ClaimStageCode.SURVEY else None,
                    "survey_status": "Pending",
                    "claim_stage": stage,
                    "status": status,
                    "estimated_amount": Decimal("18500.00"),
                    "approved_amount": Decimal("0.00"),
                },
            )
            claims.append(claim)

        job_specs = [
            ("JOB-DEMO-0001", claims[0], "Open", Decimal("9150"), Decimal("4500")),
            ("JOB-DEMO-0002", claims[1], "Open", Decimal("13350"), Decimal("7200")),
        ]
        for job_no, claim, repair_status, parts_total, labour_total in job_specs:
            job, _ = JobCard.objects.update_or_create(
                claim=claim,
                defaults={
                    "job_no": job_no,
                    "advisor": employees["advisor"],
                    "vehicle_inward_type": "Walk-in",
                    "vehicle_inward_by": "Customer Self",
                    "gate_in_datetime": now - timedelta(hours=4),
                    "expected_delivery_datetime": now + timedelta(days=3),
                    "km": 24500,
                    "part_order_date": today,
                    "part_order_no": f"PO-{job_no[-4:]}",
                    "repair_status": repair_status,
                    "parts_total": parts_total,
                    "labour_total": labour_total,
                    "grand_total": parts_total + labour_total,
                    "repair_instructions": "Demo repair advice: inspect front bumper, paint panel, and perform QC.",
                },
            )
            JobCardInventory.objects.update_or_create(
                job=job,
                defaults={
                    "mud_flap_count": 4,
                    "floor_mat_count": 4,
                    "lh_mirror": True,
                    "rh_mirror": True,
                    "center_mirror": True,
                    "frt_wiper": True,
                    "rr_wiper": True,
                    "accessories": True,
                    "spare_wheel": True,
                    "jack": True,
                    "tool_kit": True,
                    "stereo": True,
                    "battery": True,
                    "number_plate": True,
                    "fuel_percent": 45,
                    "cng_percent": 30 if "CNG" in claim.vehicle.variant.name.upper() else 0,
                    "damage_marks": [{"type": "dent", "x": 35, "y": 42}],
                    "remarks": "Demo inventory checked.",
                },
            )
            for position in ["front_left", "front_right", "rear_left", "rear_right", "stepney"]:
                JobCardTyreInventory.objects.update_or_create(
                    job=job,
                    position=position,
                    defaults={
                        "make": "MRF",
                        "size": "195/60 R16",
                        "depth": Decimal("5.50"),
                        "wheel_cap": "Y",
                    },
                )
            JobCardPart.objects.update_or_create(
                job=job,
                part_no="PANEL-001",
                defaults={
                    "description": "Front Bumper",
                    "qty": 1,
                    "rate": Decimal("8500"),
                    "amount": Decimal("8500"),
                },
            )
            JobCardLabour.objects.update_or_create(
                job=job,
                job_code="LAB-PAINT",
                defaults={
                    "description": "Paint front bumper",
                    "labour_hrs": Decimal("4.00"),
                    "rate": Decimal("1125"),
                    "amount": Decimal("4500"),
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Demo users:")
        self.stdout.write(f"  demo_admin / {password}")
        self.stdout.write(f"  demo_manager / {password}")
        self.stdout.write(f"  demo_advisor / {password}")
        self.stdout.write(f"  demo_denter / {password}")
