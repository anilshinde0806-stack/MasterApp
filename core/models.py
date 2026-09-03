from decimal import Decimal,InvalidOperation
from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class ItemData(models.Model):
    UNIT_CHOICES = [
        ("Nos", "Nos"),
        ("Set", "Set"),
        ("Pair", "Pair"),
        ("Litre", "Litre"),
        ("Kg", "Kg"),
        ("Metre", "Metre"),
    ]

    item_code = models.CharField(max_length=50, unique=True)
    item_name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="Active")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="Nos")
    manufacturer = models.CharField(max_length=120, blank=True)
    hsn_code = models.CharField(max_length=20, blank=True)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    preferred_supplier = models.CharField(max_length=150, blank=True)
    bin_location = models.CharField(max_length=80, blank=True)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.item_name

    @property
    def needs_reorder(self):
        return (
            self.status == "Active"
            and self.reorder_level > 0
            and self.current_stock <= self.reorder_level
        )


class PartStockTransaction(models.Model):
    TRANSACTION_CHOICES = [
        ("Opening", "Opening Stock"),
        ("Receipt", "Stock Receipt"),
        ("Issue", "Stock Issue"),
        ("Return", "Stock Return"),
        ("Adjustment", "Stock Adjustment"),
    ]

    part = models.ForeignKey(
        ItemData,
        on_delete=models.PROTECT,
        related_name="stock_transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_CHOICES,
        default="Adjustment",
    )
    quantity_change = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    remarks = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="part_stock_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.part.item_code}: {self.quantity_change}"


class PartRequisition(models.Model):
    STATUS_CHOICES = [
        ("Submitted", "Submitted"),
        ("Partially Fulfilled", "Partially Fulfilled"),
        ("Fulfilled", "Fulfilled"),
        ("Cancelled", "Cancelled"),
    ]
    PRIORITY_CHOICES = [
        ("Normal", "Normal"),
        ("Urgent", "Urgent"),
        ("Vehicle Hold", "Vehicle Hold"),
    ]

    requisition_no = models.CharField(max_length=40, unique=True, blank=True)
    job = models.ForeignKey(
        "JobCard",
        on_delete=models.PROTECT,
        related_name="part_requisitions",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="part_requisitions_requested",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    needed_by = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="Normal",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Submitted",
    )
    remarks = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at", "-id"]

    def __str__(self):
        return self.requisition_no or f"Requisition #{self.id}"


class PartRequisitionLine(models.Model):
    requisition = models.ForeignKey(
        PartRequisition,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    part = models.ForeignKey(
        ItemData,
        on_delete=models.PROTECT,
        related_name="requisition_lines",
    )
    estimated_part = models.ForeignKey(
        "JobCardPart",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="requisition_lines",
    )
    requested_qty = models.DecimalField(max_digits=12, decimal_places=2)
    fulfilled_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["requisition", "part"],
                name="unique_part_per_requisition",
            )
        ]

    @property
    def pending_qty(self):
        return max(self.requested_qty - self.fulfilled_qty, Decimal("0"))


class PartRequisitionFulfillment(models.Model):
    line = models.ForeignKey(
        PartRequisitionLine,
        on_delete=models.PROTECT,
        related_name="fulfillments",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    stock_transaction = models.OneToOneField(
        PartStockTransaction,
        on_delete=models.PROTECT,
        related_name="requisition_fulfillment",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="part_requisition_fulfillments",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-issued_at", "-id"]




# Create your models here.



class InsuranceCompany(models.Model):
    ins_co_name = models.CharField(max_length=255)

    branch = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)

    pin_code = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{6}$', 'Enter valid 6 digit PIN code')]
    )

    gst_no = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[0-9A-Z]{15}$', 'Enter valid GSTIN')]
    )

    cashless = models.BooleanField(default=False)

    claim_manager_name = models.CharField(max_length=255, blank=True, null=True)

    mobile_no = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{10}$', 'Enter valid 10 digit mobile number')]
    )

    email = models.EmailField(blank=True, null=True)

    moa_date = models.DateField(blank=True, null=True)
    net_moa_date = models.DateField(blank=True, null=True)

    dms_code = models.CharField(max_length=20, blank=True, null=True)

    customer_hash = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ins_co_name']
        indexes = [
            models.Index(fields=['ins_co_name']),
            models.Index(fields=['city']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['ins_co_name', 'branch'], name='unique_company_branch')
        ]
    def __str__(self):
        return f"{self.ins_co_name}"

class VehicleModel(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
class VehicleVariant(models.Model):
    model = models.ForeignKey(
        VehicleModel,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('model', 'name')

    def __str__(self):
        return f"{self.model.name} - {self.name}"


class Vehicle(models.Model):

    VEHICLE_TYPE_CHOICES = [
        ('PV', 'PV'),
        ('EV', 'EV'),
    ]

    registration_no = models.CharField(max_length=20, unique=True)
    chassis_no = models.CharField(max_length=50, unique=True)
    engine_no = models.CharField(max_length=50, unique=True)

    model = models.ForeignKey(
        VehicleModel,
        on_delete=models.PROTECT
    )

    variant = models.ForeignKey(
        VehicleVariant,
        on_delete=models.PROTECT
    )

    color = models.CharField(max_length=30)
    sale_date = models.DateField()
    insurance_company = models.ForeignKey(
        "InsuranceCompany",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehicles"
    )
    policy_no = models.CharField(max_length=100, blank=True)
    policy_start_date = models.DateField(null=True, blank=True)
    policy_end_date = models.DateField(null=True, blank=True)
    rc_document = models.FileField(upload_to="vehicle_documents/rc/", null=True, blank=True)
    insurance_policy_document = models.FileField(upload_to="vehicle_documents/insurance/", null=True, blank=True)
    primary_driver = models.ForeignKey(
        "DriverMaster", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vehicles"
    )
    last_service_km = models.PositiveIntegerField(null=True, blank=True)
    last_service_type = models.CharField(max_length=50, blank=True)
    last_service_date = models.DateField(null=True, blank=True)

    vehicle_type = models.CharField(
        max_length=2,
        choices=VEHICLE_TYPE_CHOICES
    )

    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE
    )

    def __str__(self):
      return f"{self.registration_no} - {self.model}"


class DriverMaster(models.Model):
    DRIVER_TYPE_CHOICES = [
        ("SELF", "Self"),
        ("PAID", "Paid Driver"),
        ("RELATIVE", "Relative"),
    ]

    name = models.CharField(max_length=150)
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="driver_master_records"
    )
    driver_type = models.CharField(max_length=20, choices=DRIVER_TYPE_CHOICES, default="SELF")
    mobile_no = models.CharField(max_length=15, blank=True)
    driving_license_no = models.CharField(max_length=50, unique=True)
    license_valid_until = models.DateField(null=True, blank=True)
    license_document = models.FileField(upload_to="driver_documents/licenses/", null=True, blank=True)
    face_photo = models.ImageField(upload_to="driver_documents/faces/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.driving_license_no})"

# core/models.py



class ColumnPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    screen = models.CharField(max_length=100)  # "vehicle_grid"
    name = models.CharField(max_length=100, default="default")  # preset name

    state = models.JSONField()  # AG Grid column state
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'screen', 'name')

    def __str__(self):
        return f"{self.user} - {self.screen} - {self.name}"


class UserLoginActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_activities")
    login_at = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=80, blank=True, db_index=True)

    class Meta:
        ordering = ["-login_at"]
        indexes = [
            models.Index(fields=["user", "login_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} logged in at {self.login_at:%Y-%m-%d %H:%M:%S}"


class Surveyor(models.Model):
        name = models.CharField(max_length=150)

        mobile_no = models.CharField(
            max_length=10,
            blank=True,
            null=True,
            validators=[RegexValidator(r'^\d{10}$', 'Enter valid 10 digit mobile number')]
        )

        email = models.EmailField(blank=True, null=True)

        license_no = models.CharField(
            max_length=50,
            blank=True,
            null=True,
            unique=True
        )

        company = models.CharField(max_length=150, blank=True, null=True)

        city = models.CharField(max_length=100, blank=True, null=True)

        address = models.TextField(blank=True, null=True)

        def __str__(self):
         return self.name

        # core/models.py

class Employee(models.Model):

    EMP_TYPE = [
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
        ('Advisor', 'Advisor'),
        ('MANAGER', 'Manager'),
        ('Floor Supervisor', 'Floor Supervisor'),
        ('Gate Security', 'Gate Security'),
        ('Reception', 'Reception'),
        ('Quality Inspector', 'Quality Inspector'),
        ('Parts Manager', 'Parts Manager'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=150)

    mobile_no = models.CharField(max_length=10, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    employee_code = models.CharField(max_length=20, unique=True)

    profile_photo = models.ImageField(
        upload_to="employee_profile_photos/",
        blank=True,
        null=True
    )

    branch = models.ForeignKey(
        "Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees"
    )

    designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    employee_type = models.CharField(
        max_length=20,
        choices=EMP_TYPE,
        default='STAFF'
    )

    joining_date = models.DateField(blank=True, null=True)

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    address = models.TextField(blank=True, null=True)

    def __str__(self):
        code = self.employee_code or "NO-CODE"
        name = self.name or "Unnamed"

        return f"{code} - {name}"
class ClaimStageCode(models.IntegerChoices):

    CLAIM_CREATED = 1, "Claim Created"
    ADVISOR_ASSIGNED = 2, "Advisor Assigned"
    ESTIMATE_CREATED = 3, "Estimate Created"
    INTIMATION = 4, "Claim Intimation"
    SURVEY = 5, "Survey Done"
    INSURANCE_APPROVAL = 6, "Insurance Approval"

    WORK_ALLOCATION = 7, "Work Allocation Pending"
    REPAIR_IN_PROGRESS = 8, "Repair Work In Progress"
    WORK_COMPLETED = 9, "Work Completed"
    RE_INSPECTION = 10, "Re Inspection"
    LIABILITY = 11, "Liability"
    INVOICED = 12, "Invoiced"
    DELIVERY = 13, "Delivery"
    CLOSED = 14, "Closed"

class Claim(models.Model):

    CLAIM_TYPE_CHOICES = [
        ("Cashless", "Cashless"),
        ("NonCashless", "NonCashless"),
        ("Paid", "Paid"),
        ("Warranty", "Warranty"),
        ("FOC", "FOC")

    ]

    INWARD_TYPE_CHOICES = [
        ("Pickup", "Pickup"),
        ("Walk-in", "Walk-in"),
        ("Breakdown", "Breakdown")
    ]

    SURVEY_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Re-Inspection", "Re-Inspection")
    ]

    CLAIM_STAGES = [
        (1, "Claim Created"),
        (2, "Advisor Assigned"),
        (3, "Estimate Created"),
        (4, "Claim Intimation"),
        (5, "Survey Done"),
        (6, "Insurance Approval"),
        (7, "Work Allocation Pending"),
        (8, "Repair Work In Progress"),
        (9, "Work Completed"),
        (10, "Re Inspection"),
        (11, "Liability"),
        (12, "Invoiced"),
        (13, "Delivery"),
        (14, "Closed"),
    ]

    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Closed", "Closed"),
        ("Cancelled", "Cancelled")
    ]

    # =========================
    # BASIC
    # =========================

    claim_no = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="claims"
    )

    branch = models.ForeignKey(
        "Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims"
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # =========================
    # INSURANCE
    # =========================

    insurance_company = models.ForeignKey(
        InsuranceCompany,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    policy_no = models.CharField(
        max_length=100,
        blank=True
    )

    ic_claim_no = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Insurance Claim No"
    )

    claim_type = models.CharField(
        max_length=30,
        choices=CLAIM_TYPE_CHOICES,
        default="Cashless"
    )



    # =========================
    # ACCIDENT
    # =========================

    accident_date = models.DateField(
        null=True,
        blank=True
    )

    intimation_date = models.DateTimeField(
        null=True,
        blank=True
    )

    # =========================
    # SURVEY
    # =========================

    survey_date = models.DateTimeField(null=True, blank=True)

    surveyor = models.ForeignKey(
        Surveyor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    survey_status = models.CharField(
        max_length=30,
        choices=SURVEY_STATUS_CHOICES,
        default="Pending",
        null=True,
        blank=True
    )

    self_survey = models.BooleanField(default=False)

    insurance_approval_date = models.DateTimeField(null=True, blank=True)

    insurance_note = models.TextField(blank=True)

    assessment_file = models.FileField(
        upload_to="claim_assessments/",
        null=True,
        blank=True
    )




    # =========================
    # WORKFLOW
    # =========================

    claim_stage = models.IntegerField(
        choices=CLAIM_STAGES,
        default=1
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Open"
    )

    # =========================
    # FINANCIAL
    # =========================

    estimated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null = True,
        blank = True
    )

    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null = True,
        blank = True
    )

    pre_invoice_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    pre_invoice_part_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    pre_invoice_labour_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    pre_invoice_total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    pre_invoice_file = models.FileField(
        upload_to="claim_pre_invoices/",
        null=True,
        blank=True
    )

    liability_received_at = models.DateTimeField(
        null=True,
        blank=True
    )

    liability_do_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    liability_document = models.FileField(
        upload_to="claim_liability_documents/",
        null=True,
        blank=True
    )

    PAYMENT_MODE_CHOICES = [
        ("Online", "Online"),
        ("UPI", "UPI"),
        ("Card", "Card"),
        ("Cash", "Cash"),
        ("DD", "DD"),
        ("Other", "Other"),
    ]

    invoice_datetime = models.DateTimeField(
        null=True,
        blank=True
    )

    invoice_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    invoice_parts_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    invoice_labour_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    customer_difference_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True
    )

    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        blank=True
    )

    payment_details = models.TextField(
        blank=True
    )

    DELIVERY_TO_CHOICES = [
        ("Customer Self", "Customer Self"),
        ("Customer Representative", "Customer Representative"),
        ("Drop By Driver", "Drop By Driver"),
    ]

    delivery_datetime = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivered_claims"
    )

    delivered_to = models.CharField(
        max_length=40,
        choices=DELIVERY_TO_CHOICES,
        blank=True
    )

    delivery_driver_name = models.CharField(
        max_length=100,
        blank=True
    )

    delivery_remarks = models.TextField(
        blank=True
    )

    # =========================
    # REMARKS
    # =========================

    remarks = models.TextField(blank=True)

    # =========================
    # AUDIT
    # =========================

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    # =========================
    # META
    # =========================

    class Meta:

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["claim_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["claim_stage"]),
        ]

    def __str__(self):
        return self.claim_no


class JobCardType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mst_jobcard_type"
        ordering = ["display_order", "name"]
        verbose_name = "Job Card Type"
        verbose_name_plural = "Job Card Types"

    def __str__(self):
        return self.name


class JobCard(models.Model):


    INWARD_TYPE_CHOICES = [
        ("Pickup", "Pickup"),
        ("Walk-in", "Walk-in"),
        ("Breakdown", "Breakdown")
    ]
    PART_ORDER_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Order Placed", "Order Placed"),
        ("In Transit", "In Transit"),
        ("Partially Received", "Partially Received"),
        ("Back Order", "Back Order"),
        ("Cancelled", "Cancelled"),
        ("Completed", "Completed")
    ]

    claim = models.OneToOneField(
            Claim,
            on_delete=models.SET_NULL,
            null=True,
            blank=True
        )

    vehicle = models.ForeignKey(
            Vehicle,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="direct_jobcards"
        )

    branch = models.ForeignKey(
            "Branch",
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name="jobcards"
        )


    job_no = models.CharField(
            max_length=30,
            unique=True
        )

    job_date = models.DateTimeField(auto_now_add=True)

    jobcard_type = models.ForeignKey(
        JobCardType,
        on_delete=models.PROTECT,
        related_name="jobcards"
    )


    advisor = models.ForeignKey(
            Employee,
            on_delete=models.SET_NULL,
            null=True,
            related_name="advisor_jobs"
        )
    vehicle_inward_type = models.CharField(
            max_length=20,
            choices=INWARD_TYPE_CHOICES,
            default="Walk-in"
        )
    vehicle_inward_by = models.CharField(
        max_length=20,
        blank=True
    )
    gate_in_datetime = models.DateTimeField(verbose_name="Gate In Time", null=True, blank=True)
    expected_delivery_datetime = models.DateTimeField(verbose_name="Actual PromisedDelivery Date", null=True, blank=True)
    km = models.PositiveIntegerField(
            null=True,
            blank=True,
            verbose_name="Current KM"
        )

    fuel_level = models.CharField(
            max_length=20,
            blank=True
        )
    # =========================
    # PARTS ORDER
    # =========================

    part_order_date = models.DateField(null=True, blank=True)

    part_order_no = models.CharField(
        max_length=50,
        blank=True
    )

    repair_status = models.CharField(
            max_length=30,
            choices=[
                ("Open", "Open"),
                ("Completed", "Completed"),
                ("Closed", "Closed"),
                ("Cancellation", "Cancellation"),
            ],
            default="Open"
        )


    estimated_delivery = models.DateTimeField(
            null=True,
            blank=True
        )

    actual_delivery = models.DateTimeField(
            null=True,
            blank=True
        )



    parts_total = models.DecimalField(
            max_digits=12,
            decimal_places=2,
            default=0
        )

    labour_total = models.DecimalField(
            max_digits=12,
            decimal_places=2,
            default=0
        )

    grand_total = models.DecimalField(
            max_digits=12,
            decimal_places=2,
            default=0
        )
    # =========================
    # WORK DETAILS
    # =========================
    repair_instructions = models.TextField(blank=True)

    qc_done = models.BooleanField(default=False)

    reinspection_done = models.BooleanField(default=False)

    reinspection_date = models.DateTimeField(
            null=True,
            blank=True
        )

    reinspection_done_by = models.CharField(
            max_length=100,
            blank=True
        )

    road_test_done = models.BooleanField(default=False)

    washing_done = models.BooleanField(default=False)

    ready_for_delivery = models.BooleanField(default=False)

    additional_approval_required = models.BooleanField(default=False)

    second_approval_status = models.CharField(
            max_length=20,
            choices=[
                ("", "Not Required"),
                ("Pending", "Pending"),
                ("Approved", "Approved"),
                ("Rejected", "Rejected"),
            ],
            blank=True,
            default=""
        )

    additional_approval_reason = models.TextField(blank=True)

    advisor_signature = models.ImageField(
            upload_to="jobcard_signatures/",
            blank=True,
            null=True
        )

    customer_signature = models.ImageField(
            upload_to="jobcard_signatures/",
            blank=True,
            null=True
        )

    # =========================
    # META
    # =========================
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    def __str__(self):
            return self.job_no




class JobCardQualityCheck(models.Model):
    jobcard = models.OneToOneField(
        "JobCard",
        on_delete=models.CASCADE,
        related_name="quality_check",
    )

    paint_finish = models.BooleanField(default=False)
    color_match = models.BooleanField(default=False)
    panel_alignment = models.BooleanField(default=False)
    electrical_check = models.BooleanField(default=False)
    ac_check = models.BooleanField(default=False)
    road_test = models.BooleanField(default=False)
    washing_done = models.BooleanField(default=False)
    interior_cleaning = models.BooleanField(default=False)
    exterior_cleaning = models.BooleanField(default=False)
    tool_kit_available = models.BooleanField(default=False)
    spare_wheel_available = models.BooleanField(default=False)
    fuel_level_checked = models.BooleanField(default=False)
    customer_belongings_checked = models.BooleanField(default=False)
    documents_checked = models.BooleanField(default=False)
    final_inspection = models.BooleanField(default=False)

    remarks = models.TextField(
        blank=True,
        default="",
    )

    inspector_signature = models.ImageField(
        upload_to="quality_check/signatures/",
        blank=True,
        null=True,
    )

    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobcard_quality_checks",
    )

    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Job Card Quality Check"
        verbose_name_plural = "Job Card Quality Checks"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def ok_items(self):
        return self.items.filter(
            status="OK",
        ).count()

    @property
    def not_ok_items(self):
        return self.items.filter(
            status="NOT_OK",
        ).count()

    @property
    def pending_items(self):
        return self.items.filter(
            status="PENDING",
        ).count()

    @property
    def checked_items(self):
        return self.ok_items + self.not_ok_items

    @property
    def completion_percentage(self):
        total = self.total_items

        if total == 0:
            return 0

        return round(
            (self.checked_items / total) * 100,
            2,
        )

    @property
    def result(self):
        if self.not_ok_items > 0:
            return "NOT_OK"

        if self.total_items > 0 and self.pending_items == 0:
            return "OK"

        return "PENDING"
    def __str__(self):
        return f"QC - {self.jobcard.job_no}"


class QualityCheckEvidencePhoto(models.Model):
    quality_check = models.ForeignKey(
        "JobCardQualityCheck",
        on_delete=models.CASCADE,
        related_name="evidence_photos",
    )
    image = models.ImageField(
        upload_to="quality_check/evidence/%Y/%m/",
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_check_evidence_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.quality_check_id} - {self.caption or self.image.name}"


class QualityCheckInspectorSignature(models.Model):
    quality_check = models.ForeignKey(
        "JobCardQualityCheck",
        on_delete=models.CASCADE,
        related_name="inspector_signatures",
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_check_signatures",
    )
    image = models.ImageField(
        upload_to="quality_check/signatures/",
    )
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["signed_at", "id"]

    def __str__(self):
        return f"{self.quality_check_id} - {self.inspector or 'Inspector'}"



class QualityCheckItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        OK = "OK", "OK"
        NOT_OK = "NOT_OK", "Not OK"

    quality_check = models.ForeignKey(
        "JobCardQualityCheck",
        on_delete=models.CASCADE,
        related_name="items",
    )

    item_key = models.CharField(
        max_length=50,
    )

    item_name = models.CharField(
        max_length=100,
    )

    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    remarks = models.TextField(
        blank=True,
        default="",
    )

    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_check_items_checked",
    )

    checked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "quality_check",
                    "item_key",
                ],
                name="unique_quality_check_item",
            ),
        ]

    @property
    def total_items(self):
        return self.items.count()

    @property
    def ok_items(self):
        return self.items.filter(
            status=QualityCheckItem.Status.OK,
        ).count()

    @property
    def not_ok_items(self):
        return self.items.filter(
            status=QualityCheckItem.Status.NOT_OK,
        ).count()

    @property
    def pending_items(self):
        return self.items.filter(
            status=QualityCheckItem.Status.PENDING,
        ).count()

    @property
    def checked_items(self):
        return self.items.exclude(
            status=QualityCheckItem.Status.PENDING,
        ).count()

    @property
    def completion_percentage(self):
        total = self.total_items

        if total == 0:
            return 0

        return round(
            (self.checked_items / total) * 100,
            2,
        )

    @property
    def has_failures(self):
        return self.not_ok_items > 0

    @property
    def result(self):
        if self.total_items == 0:
            return "PENDING"

        if self.pending_items > 0:
            return "PENDING"

        if self.not_ok_items > 0:
            return "NOT_OK"

        return "OK"

    @property
    def can_complete(self):
        return (
                self.total_items > 0
                and self.pending_items == 0
                and self.not_ok_items == 0
        )
    def __str__(self):
        return (
            f"{self.quality_check_id} - "
            f"{self.item_name} - "
            f"{self.get_status_display()}"
        )
class GateInEntry(models.Model):
    SERVICE_TYPE_CHOICES = [
        ("Service", "Service"),
        ("Bodyshop", "Bodyshop"),
        ("Other", "Other"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Converted", "Converted"),
        ("Gate Out", "Gate Out"),
        ("Cancelled", "Cancelled"),
    ]

    registration_no = models.CharField(max_length=20, db_index=True)
    current_km = models.PositiveIntegerField()
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default="Bodyshop",
    )
    gate_in_datetime = models.DateTimeField(default=timezone.now, db_index=True)
    branch = models.ForeignKey(
        "Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_in_entries",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_in_entries",
    )
    jobcard = models.OneToOneField(
        JobCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_in_entry",
    )
    entered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_in_entries",
    )
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_gate_in_entries",
    )
    gate_out_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_out_entries",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
        db_index=True,
    )
    remarks = models.TextField(blank=True)
    cancellation_remark = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    gate_out_datetime = models.DateTimeField(null=True, blank=True)
    out_km = models.PositiveIntegerField(null=True, blank=True)
    gate_pass_no = models.CharField(max_length=80, blank=True)
    gate_pass_evidence = models.ImageField(upload_to="gate_pass/evidence/", null=True, blank=True)
    customer_signature = models.ImageField(upload_to="gate_pass/signatures/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-gate_in_datetime"]
        indexes = [
            models.Index(fields=["registration_no", "status"]),
            models.Index(fields=["service_type", "status"]),
        ]

    def save(self, *args, **kwargs):
        self.registration_no = (self.registration_no or "").strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.registration_no} - {self.service_type}"


def reinspection_photo_upload_path(instance, filename):
        claim_no = "unknown_claim"

        if (
            instance.job
            and instance.job.claim
            and instance.job.claim.claim_no
        ):
            claim_no = instance.job.claim.claim_no

        safe_claim_no = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in claim_no
        )

        return f"jobcard_reinspection/{safe_claim_no}/{filename}"


class JobCardReInspectionPhoto(models.Model):
        job = models.ForeignKey(
            JobCard,
            on_delete=models.CASCADE,
            related_name="reinspection_photos"
        )

        image = models.ImageField(
            upload_to=reinspection_photo_upload_path
        )

        uploaded_at = models.DateTimeField(auto_now_add=True)


def additional_approval_photo_upload_path(instance, filename):
        claim_no = "unknown_claim"
        job_no = "unknown_job"

        if instance.job:
            job_no = instance.job.job_no or job_no
            if instance.job.claim and instance.job.claim.claim_no:
                claim_no = instance.job.claim.claim_no

        safe_claim_no = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in claim_no
        )
        safe_job_no = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in job_no
        )

        return f"additional_approval_photos/{safe_claim_no}/{safe_job_no}/{filename}"


class JobCardAdditionalApprovalPhoto(models.Model):
        job = models.ForeignKey(
            JobCard,
            on_delete=models.CASCADE,
            related_name="additional_approval_photos"
        )

        work_allocation_part = models.ForeignKey(
            "WorkAllocationPart",
            on_delete=models.CASCADE,
            related_name="additional_approval_photos",
            blank=True,
            null=True
        )

        work_allocation_labour = models.ForeignKey(
            "WorkAllocationLabour",
            on_delete=models.CASCADE,
            related_name="additional_approval_photos",
            blank=True,
            null=True
        )

        image = models.ImageField(
            upload_to=additional_approval_photo_upload_path
        )

        uploaded_at = models.DateTimeField(auto_now_add=True)


def vehicle_condition_photo_upload_path(instance, filename):
        claim_no = "unknown_claim"

        if (
            instance.job
            and instance.job.claim
            and instance.job.claim.claim_no
        ):
            claim_no = instance.job.claim.claim_no

        safe_claim_no = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in claim_no
        )
        safe_caption = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in instance.caption
        )

        return f"jobcard_vehicle_condition/{safe_claim_no}/{safe_caption}_{filename}"


class JobCardVehicleConditionPhoto(models.Model):

        job = models.ForeignKey(
            JobCard,
            on_delete=models.CASCADE,
            related_name="vehicle_condition_photos"
        )

        caption = models.CharField(max_length=100)

        image = models.ImageField(
            upload_to=vehicle_condition_photo_upload_path
        )

        uploaded_at = models.DateTimeField(auto_now=True)

        class Meta:
            constraints = [
                models.UniqueConstraint(
                    fields=["job", "caption"],
                    name="unique_jobcard_vehicle_condition_caption"
                )
            ]
class JobCardPhotoAnnotation(models.Model):

    ANNOTATION_TYPE_CHOICES = [
        ("circle", "Circle"),
        ("rectangle", "Rectangle"),
        ("arrow", "Arrow"),
        ("text", "Text"),
    ]

    photo = models.ForeignKey(
        JobCardVehicleConditionPhoto,
        on_delete=models.CASCADE,
        related_name="annotations",
    )

    annotation_type = models.CharField(
        max_length=20,
        choices=ANNOTATION_TYPE_CHOICES,
    )

    # ---------------------------------------------------------
    # Normalized coordinates
    # 0.0 -> 1.0
    # ---------------------------------------------------------

    start_x = models.FloatField(
        default=0.0,
    )

    start_y = models.FloatField(
        default=0.0,
    )

    end_x = models.FloatField(
        null=True,
        blank=True,
    )

    end_y = models.FloatField(
        null=True,
        blank=True,
    )

    # ---------------------------------------------------------
    # Text annotation
    # ---------------------------------------------------------

    text = models.TextField(
        blank=True,
        default="",
    )

    # ---------------------------------------------------------
    # Drawing appearance
    # ---------------------------------------------------------

    color = models.CharField(
        max_length=20,
        default="#FF0000",
    )

    stroke_width = models.FloatField(
        default=4.0,
    )

    font_size = models.FloatField(
        default=18.0,
    )

    # ---------------------------------------------------------
    # Ordering
    # ---------------------------------------------------------

    display_order = models.PositiveIntegerField(
        default=0,
    )

    # ---------------------------------------------------------
    # Audit
    # ---------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]

    def __str__(self):
        return (
            f"{self.annotation_type} "
            f"- Photo {self.photo_id}"
        )

class ClaimDocument(models.Model):
        claim = models.ForeignKey(
            Claim,
            on_delete=models.CASCADE
        )

        document_type = models.CharField(max_length=50)

        file = models.FileField(upload_to="claims/")

        uploaded_at = models.DateTimeField(auto_now_add=True)

class ClaimNote(models.Model):

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE
    )

    note = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

class ClaimPhoto(models.Model):

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE
    )

    image = models.ImageField(upload_to="claim_photos/")

class ClaimTimeline(models.Model):

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name="timeline"
    )

    stage = models.CharField(max_length=100)

    remarks = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

class JobCardLabour(models.Model):
    PAINT_PANEL_TYPE_CHOICES = [
        ("", "No Paint Panel"),
        ("New", "New Panel Painting"),
        ("Repair", "Repair Panel Painting"),
    ]

    job = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name="labours"
    )

    job_code = models.CharField(max_length=50)
    description = models.CharField(max_length=255)

    labour_hrs = models.DecimalField(max_digits=5, decimal_places=2)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paint_panel_type = models.CharField(
        max_length=20,
        blank=True,
        choices=PAINT_PANEL_TYPE_CHOICES,
        default=""
    )

    def save(self, *args, **kwargs):
        try:
            labour_hrs = Decimal(str(self.labour_hrs or 0))
        except (InvalidOperation, TypeError):
            labour_hrs = Decimal("0")

        try:
            rate = Decimal(str(self.rate or 0))
        except (InvalidOperation, TypeError):
            rate = Decimal("0")

        self.amount = labour_hrs * rate

        super().save(*args, **kwargs)

class JobCardPart(models.Model):

    job = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name="parts"
    )

    part_no = models.CharField(max_length=50)
    description = models.CharField(max_length=255)

    qty = models.PositiveIntegerField(default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    from decimal import Decimal, InvalidOperation

    def save(self, *args, **kwargs):
        try:
            qty = Decimal(str(self.qty or 0))
        except (InvalidOperation, TypeError):
            qty = Decimal("0")

        try:
            rate = Decimal(str(self.rate or 0))
        except (InvalidOperation, TypeError):
            rate = Decimal("0")

        self.total = qty * rate

        super().save(*args, **kwargs)

class PartOrderHeader(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Order Placed", "Order Placed"),
        ("In Transit", "In Transit"),
        ("Partially Received", "Partially Received"),
        ("Received", "Received"),
        ("Back Order", "Back Order"),
        ("Cancelled", "Cancelled"),
    ]

    job = models.ForeignKey(
        JobCard,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="part_order_headers"
    )
    vehicle = models.ForeignKey(
        Vehicle,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="part_order_headers"
    )
    order_no = models.CharField(max_length=50, blank=True)
    order_date = models.DateField(null=True, blank=True)
    expected_date = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Pending"
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.order_no or f"Part Order #{self.id}"

class PartOrder(models.Model):
    STATUS_CHOICES = PartOrderHeader.STATUS_CHOICES

    order = models.ForeignKey(
        PartOrderHeader,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="lines"
    )
    job = models.ForeignKey(
        JobCard,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="part_orders"
    )
    part = models.ForeignKey(
        JobCardPart,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="part_orders"
    )
    manual_part_no = models.CharField(max_length=100, blank=True)
    manual_description = models.CharField(max_length=255, blank=True)
    order_no = models.CharField(max_length=50, blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    order_date = models.DateField(null=True, blank=True)
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    ordered_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    received_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Pending"
    )
    tracking_ref = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        job_no = self.job.job_no if self.job else "Advance"
        part_no = self.part.part_no if self.part else self.manual_part_no
        return f"{job_no} - {part_no}"

class ClaimStage(models.Model):
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
from django.db import models

class CompanySetup(models.Model):
    company_name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='company/', blank=True, null=True)

    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)

    phone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)

    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    gst_no = models.CharField(max_length=50, blank=True, null=True)
    pan_no = models.CharField(max_length=50, blank=True, null=True)
    cin_no = models.CharField(max_length=50, blank=True, null=True)

    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_no = models.CharField(max_length=100, blank=True, null=True)
    ifsc_code = models.CharField(max_length=50, blank=True, null=True)

    invoice_footer = models.TextField(blank=True, null=True)

    signature = models.ImageField(upload_to='signature/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Branch(models.Model):
    parent = models.ForeignKey(
        CompanySetup,
        on_delete=models.CASCADE,
        related_name="branches",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)
    claim_no_alias = models.CharField(max_length=16, blank=True, null=True)
    jobcard_no_alias = models.CharField(max_length=16, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    gst_no = models.CharField(max_length=50, blank=True, null=True)
    is_head_office = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

class JobCardAssessmentPart(models.Model):
    job = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name="assessment_parts"
    )
    part = models.ForeignKey(JobCardPart, on_delete=models.CASCADE)

    decision = models.CharField(
        max_length=20,
        choices=[
            ("New", "New"),
            ("Repair", "Repair"),
            ("KO", "KO"),
            ("Reject", "Reject"),
        ],
        default="New"
    )

    revised_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    approval_date = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    assessment_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assessed_jobcard_parts"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="updated_jobcard_assessment_parts"
    )
    updated_date_time = models.DateTimeField(auto_now=True)



class JobCardAssessmentLabour(models.Model):
        job = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="assessment_labours")
        labour = models.ForeignKey(JobCardLabour, on_delete=models.CASCADE)

        decision = models.CharField(
            max_length=20,
            choices=[
                ("Approved", "Approved"),
                ("Reject", "Reject"),

            ],
            default="Approved"
        )
        deduction_percent = models.DecimalField(
            max_digits=5,
            decimal_places=2,
            default=0
        )
        revised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

        approval_date = models.DateTimeField(null=True, blank=True)
        remarks = models.TextField(blank=True)
        assessment_by = models.ForeignKey(
            User, on_delete=models.SET_NULL, null=True, blank=True,
            related_name="assessed_jobcard_labours"
        )
        updated_by = models.ForeignKey(
            User, on_delete=models.SET_NULL, null=True, blank=True,
            related_name="updated_jobcard_assessment_labours"
        )
        updated_date_time = models.DateTimeField(auto_now=True)


class JobCardInventory(models.Model):

    job = models.OneToOneField(
        JobCard,
        on_delete=models.CASCADE,
        related_name="inventory"
    )

    # count based inventory

    mud_flap_count = models.PositiveIntegerField(default=0)
    floor_mat_count = models.PositiveIntegerField(default=0)
    lh_mirror = models.BooleanField(default=False)
    rh_mirror = models.BooleanField(default=False)
    center_mirror = models.BooleanField(default=False)
    frt_wiper =models.BooleanField(default=False)
    rr_wiper =models.BooleanField(default=False)
    accessories=models.BooleanField(default=False)
    spare_wheel = models.BooleanField(default=False)
    jack = models.BooleanField(default=False)
    tool_kit = models.BooleanField(default=False)
    stereo = models.BooleanField(default=False)
    battery = models.BooleanField(default=False)
    number_plate = models.BooleanField(default=False)

    fuel_percent = models.PositiveIntegerField(default=0)
    cng_percent = models.PositiveIntegerField(default=0)

    damage_marks = models.JSONField(default=list, blank=True)

    remarks = models.TextField(blank=True)

class JobCardTyreInventory(models.Model):

    POSITION_CHOICES = [
        ("front_left", "Front Left"),
        ("front_right", "Front Right"),
        ("rear_left", "Rear Left"),
        ("rear_right", "Rear Right"),
        ("stepney", "Stepney"),
    ]
    WHEELCAP_CHOICES = [
        ("Y", "Yes"),
        ("N", "No"),
        ]

    job = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name="tyres"
    )

    position = models.CharField(
        max_length=30,
        choices=POSITION_CHOICES
    )

    make = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=50, blank=True)
    depth = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    wheel_cap = models.CharField(
        max_length=3,
        choices=WHEELCAP_CHOICES)
    class Meta:
        unique_together = ("job", "position")

import os

def jobcard_pdf_upload_path(instance, filename):

    return os.path.join(
        "jobcard_pdfs",
        instance.job.job_no,
        filename
    )


class CommunicationLog(models.Model):

    CHANNEL_CHOICES = [
        ("WhatsApp", "WhatsApp"),
        ("Email", "Email"),
        ("SMS", "SMS"),
    ]

    job = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name="communications"
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES
    )

    mobile_no = models.CharField(max_length=20)

    message = models.TextField()

    pdf_file = models.FileField(
        upload_to=jobcard_pdf_upload_path,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        default="Pending"
    )

    response = models.TextField(blank=True)

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

class UserNotification(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=100)

    message = models.TextField()

    url = models.CharField(
        max_length=255,
        blank=True
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

class WorkAllocation(models.Model):
        job = models.OneToOneField(
            JobCard,
            on_delete=models.CASCADE,
            related_name="allocation"
        )

        allotment_date = models.DateTimeField(
            auto_now_add=True
        )

        delivery_date = models.DateField(
            null=True,
            blank=True
        )

        parts_slip_no = models.CharField(
            max_length=50,
            blank=True
        )

        remarks = models.TextField(
            blank=True
        )

        part_entry_complete = models.BooleanField(
            default=False
        )

class WorkProgress(models.Model):
        STAGES = [

            ("Dismantling",
             "Damage Body Parts Dismantling"),

            ("Mechanical",
             "Mechanical Work"),

            ("Repair",
             "Body Repairing"),

            ("Painting",
             "Vehicle Painting"),

            ("Assembly",
             "Body Assembling"),

            ("Fitting",
             "Mechanical Fitting"),
        ]

        allocation = models.ForeignKey(
            WorkAllocation,
            on_delete=models.CASCADE,
            related_name="progress"
        )

        stage = models.CharField(
            max_length=30,
            choices=STAGES
        )

        start_time = models.DateTimeField(
            null=True,
            blank=True
        )

        finish_time = models.DateTimeField(
            null=True,
            blank=True
        )

        employee = models.ForeignKey(
            Employee,
            null=True,
            blank=True,
            on_delete=models.SET_NULL
        )

        remarks = models.TextField(
            blank=True
        )


def work_progress_photo_upload_path(instance, filename):
        claim_no = "unknown_claim"
        job_no = "unknown_job"
        stage = "progress"

        if instance.progress and instance.progress.allocation and instance.progress.allocation.job:
            job = instance.progress.allocation.job
            job_no = job.job_no or job_no
            if job.claim and job.claim.claim_no:
                claim_no = job.claim.claim_no
            stage = instance.progress.stage or stage

        safe_claim_no = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in claim_no
        )
        safe_job_no = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in job_no
        )
        safe_stage = "".join(
            char if char.isalnum() or char in ["-", "_"] else "_"
            for char in stage
        )

        return f"work_progress_photos/{safe_claim_no}/{safe_job_no}/{safe_stage}/{filename}"


class WorkProgressPhoto(models.Model):
        progress = models.ForeignKey(
            WorkProgress,
            on_delete=models.CASCADE,
            related_name="photos"
        )

        image = models.ImageField(
            upload_to=work_progress_photo_upload_path
        )

        uploaded_at = models.DateTimeField(auto_now_add=True)

class WorkAllocationPart(models.Model):
        allocation = models.ForeignKey(
            WorkAllocation,
            on_delete=models.CASCADE,
            related_name="parts"
        )

        job_part = models.ForeignKey(
            JobCardPart,
            on_delete=models.CASCADE
        )

        decision = models.CharField(
            max_length=20
        )

        is_additional = models.BooleanField(default=False)

        advisor_approval_status = models.CharField(
            max_length=20,
            choices=[
                ("", "Not Required"),
                ("Pending", "Pending"),
                ("Approved", "Approved"),
                ("Rejected", "Rejected"),
            ],
            blank=True,
            default=""
        )

        picker_name = models.CharField(
            max_length=100,
            blank=True
        )

        pick_from_store = models.BooleanField(
            default=False
        )

        pick_date = models.DateField(
            null=True,
            blank=True
        )

        ko_order_date = models.DateField(
            null=True,
            blank=True
        )

        ko_order_no = models.CharField(
            max_length=50,
            blank=True
        )

        eta = models.DateField(
            null=True,
            blank=True
        )

        remarks = models.TextField(
            blank=True
        )


class WorkAllocationLabour(models.Model):
        allocation = models.ForeignKey(
            WorkAllocation,
            on_delete=models.CASCADE,
            related_name="labours"
        )

        job_labour = models.ForeignKey(
            JobCardLabour,
            on_delete=models.CASCADE
        )

        decision = models.CharField(
            max_length=20,
            default="Approved"
        )

        is_additional = models.BooleanField(default=False)

        advisor_approval_status = models.CharField(
            max_length=20,
            choices=[
                ("", "Not Required"),
                ("Pending", "Pending"),
                ("Approved", "Approved"),
                ("Rejected", "Rejected"),
            ],
            blank=True,
            default=""
        )

        revised_amount = models.DecimalField(
            max_digits=12,
            decimal_places=2,
            default=0
        )

        employee = models.ForeignKey(
            Employee,
            null=True,
            blank=True,
            on_delete=models.SET_NULL
        )

        remarks = models.TextField(
            blank=True
        )
from django.db import models


class Customer(models.Model):
    CUSTOMER_TYPE_CHOICES = [
        ("Individual", "Individual"),
        ("Corporate", "Corporate"),
    ]

    SALUTATION_CHOICES = [
        ("Mr", "Mr"),
        ("Mrs", "Mrs"),
        ("Ms", "Ms"),
    ]

    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
    ]

    CONTACT_METHOD_CHOICES = [
        ("Mobile", "Mobile"),
        ("WhatsApp", "WhatsApp"),
        ("Email", "Email"),
    ]

    customer_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default="Individual"
    )

    salutation = models.CharField(
        max_length=10,
        choices=SALUTATION_CHOICES,
        blank=True
    )

    name = models.CharField(
        max_length=150
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    anniversary_date = models.DateField(
        blank=True,
        null=True
    )

    gst_registered = models.BooleanField(
        default=False
    )

    pan_no = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    aadhaar_no = models.CharField(
        max_length=12,
        blank=True,
        null=True
    )

    mobile_no = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    alternate_mobile_no = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    whatsapp_no = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    preferred_contact_method = models.CharField(
        max_length=20,
        choices=CONTACT_METHOD_CHOICES,
        default="Mobile"
    )

    address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    address = models.TextField(
        blank=True,
        null=True
    )

    gst_no = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )
    pin_code = models.CharField(
        max_length=6,
        blank=True,
        null=True
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="India"
    )

    company_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    contact_person = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    designation = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    company_gst_no = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):

        return (
            f"{self.name}"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.customer_code:
            self.customer_code = f"CUST{self.pk:04d}"
            Customer.objects.filter(pk=self.pk).update(
                customer_code=self.customer_code
            )

class Announcement(models.Model):
        TYPE_CHOICES = [
            ("HR", "HR Notice"),
            ("Offer", "Promotional Offer"),
            ("Scheme", "Scheme"),
            ("General", "General"),
        ]

        title = models.CharField(max_length=150)
        message = models.TextField()

        notice_type = models.CharField(
            max_length=20,
            choices=TYPE_CHOICES,
            default="General"
        )

        is_active = models.BooleanField(default=True)

        show_once = models.BooleanField(
            default=True
        )

        created_by = models.ForeignKey(
            User,
            on_delete=models.SET_NULL,
            null=True,
            blank=True
        )

        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return self.title

class AnnouncementRead(models.Model):
        announcement = models.ForeignKey(
            Announcement,
            on_delete=models.CASCADE
        )

        user = models.ForeignKey(
            User,
            on_delete=models.CASCADE
        )

        read_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            unique_together = ("announcement", "user")


def _base_queryset(self, employee):

    if employee.employee_type == "ADMIN":
        return WorkProgress.objects.select_related(
            "allocation",
            "allocation__job",
            "employee",
        )

    elif employee.employee_type == "MANAGER":
        return WorkProgress.objects.select_related(
            "allocation",
            "allocation__job",
            "employee",
        ).filter(
            allocation__job__branch=employee.branch
        )

    elif employee.employee_type == "Advisor":
        return WorkProgress.objects.select_related(
            "allocation",
            "allocation__job",
            "employee",
        ).filter(
            allocation__job__advisor=employee
        )

    else:
        return WorkProgress.objects.select_related(
            "allocation",
            "allocation__job",
            "employee",
        ).filter(
            employee=employee
        )



def _work_queryset(self, employee):

        queryset = (
            WorkProgress.objects
            .select_related(
                "allocation",
                "allocation__job",
                "allocation__job__vehicle",
                "allocation__job__vehicle__customer",
                "allocation__job__advisor",
                "employee",
            )
        )

        role = employee.employee_type

        if role == "ADMIN":
            return queryset

        if role == "MANAGER":
            return queryset.filter(
                allocation__job__branch=employee.branch
            )

        if role == "Advisor":
            return queryset.filter(
                allocation__job__advisor=employee
            )

        return queryset.filter(
            employee=employee
        )
class EmployeeType(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    MANAGER = "MANAGER", "Body Shop Manager"
    ADVISOR = "ADVISOR", "Service Advisor"
    SURVEYOR = "SURVEYOR", "Surveyor"
    TECHNICIAN = "TECHNICIAN", "Technician"
    PAINTER = "PAINTER", "Painter"
    DENTER = "DENTER", "Denter"
    QC = "QC", "Quality Inspector"




class CustomerApprovalEvidence(models.Model):

    APPROVAL_STATUS = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Need Clarifications", "Need Clarifications"),
    ]

    COMMUNICATION_TYPES = [
        ("Manual", "Manual"),
        ("WhatsApp", "WhatsApp"),
        ("SMS", "SMS"),
        ("Email", "Email"),
    ]

    jobcard = models.ForeignKey(
        JobCard,
        on_delete=models.CASCADE,
        related_name="approval_evidence"
    )

    communication_type = models.CharField(
        max_length=50,
        choices=COMMUNICATION_TYPES,
        default="Manual"
    )

    status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default="Pending"
    )

    customer_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    mobile_no = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    message_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    approval_date = models.DateTimeField(
        null=True,
        blank=True
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return f"{self.jobcard.id} - {self.status}"


class CustomerApprovalAttachment(models.Model):
    EVIDENCE_TYPES = [
        ("WhatsApp", "WhatsApp screenshot"),
        ("Email", "Email"),
        ("SMS", "SMS screenshot"),
        ("Other", "Other"),
    ]

    approval = models.ForeignKey(
        CustomerApprovalEvidence,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    evidence_type = models.CharField(max_length=30, choices=EVIDENCE_TYPES, default="Other")
    file = models.FileField(upload_to="approval_evidence/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_approval_attachments",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return self.caption or f"{self.evidence_type} evidence #{self.id}"


class CustomerApprovalPhotoAnnotation(models.Model):
    jobcard = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="approval_photo_annotations")
    photo = models.ForeignKey(JobCardVehicleConditionPhoto, on_delete=models.CASCADE, related_name="approval_annotations")
    annotations = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["jobcard", "photo"], name="unique_approval_photo_annotation")
        ]

    def __str__(self):
        return f"Annotations for {self.photo_id}"


class JobCardDamageAISuggestion(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending review"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
    ]
    CATEGORY_CHOICES = [
        ("dent", "Dent"),
        ("scratch", "Scratch"),
        ("broken", "Broken / cracked"),
        ("paint", "Paint damage"),
        ("missing", "Missing part"),
        ("glass", "Glass damage"),
        ("other", "Other"),
    ]

    jobcard = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name="damage_ai_suggestions")
    photo = models.ForeignKey(JobCardVehicleConditionPhoto, on_delete=models.CASCADE, related_name="damage_ai_suggestions")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    x = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    y = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    width = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    height = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=50, default="pending_provider")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_damage_ai_suggestions")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_category_display()} ({self.confidence}%)"

class JobCardDamage(models.Model):
    job = models.ForeignKey(JobCard, on_delete=models.CASCADE)
    photo = models.ForeignKey(JobCardVehicleConditionPhoto, on_delete=models.CASCADE)

    damage_type = models.CharField(max_length=50)

    confidence = models.FloatField()

    severity = models.CharField(max_length=20)

    x = models.FloatField()

    y = models.FloatField()

    width = models.FloatField()

    height = models.FloatField()

    approved = models.BooleanField(default=False)

    remarks = models.TextField(blank=True)
