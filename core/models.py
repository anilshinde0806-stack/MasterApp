from typing import Any

from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.db import models

class ItemData(models.Model):
    item_code = models.CharField(max_length=50, unique=True)
    item_name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="Active")

    def __str__(self):
        return self.item_name




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

    WORK_ALLOCATION = 7, "Work Allocation"
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
        (7, "Work Allocation"),
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

    intimation_date = models.DateField(
        null=True,
        blank=True
    )

    # =========================
    # SURVEY
    # =========================

    survey_date = models.DateField(null=True, blank=True)

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
    insurance_approval_date = models.DateField(null=True, blank=True)

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
        default="Created"
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
            on_delete=models.CASCADE
        )


    job_no = models.CharField(
            max_length=30,
            unique=True
        )

    job_date = models.DateField(auto_now_add=True)


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

    reinspection_date = models.DateField(
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

    # =========================
    # META
    # =========================
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    def __str__(self):
            return self.job_no

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

    def save(self, *args, **kwargs):
        self.amount = self.labour_hrs * self.rate
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

    def save(self, *args, **kwargs):
        self.amount = self.qty * self.rate
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

        allotment_date = models.DateField(
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


    name = models.CharField(
        max_length=150
    )

    mobile_no = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    email = models.EmailField(
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
