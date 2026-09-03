from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import InsuranceCompany, Claim, DriverMaster
from .models import JobCard
from .models import Vehicle
from .models import Customer
from django import forms
from django.db.models import Q
from .models import Surveyor
from .models import Employee
from .validators import VEHICLE_NUMBER_ERROR, is_valid_vehicle_number, normalize_vehicle_number


def logged_employee_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return Employee.objects.filter(user=user).select_related("branch").first()


def is_manager_user(user, employee=None):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    employee = employee or logged_employee_for_user(user)
    role = (employee.employee_type or "").upper() if employee else ""
    return role == "MANAGER" or user.groups.filter(name__iexact="Manager").exists()


def branch_limited_employee_queryset(user, queryset=None):
    queryset = queryset or Employee.objects.all()
    employee = logged_employee_for_user(user)
    if is_manager_user(user, employee) and employee and employee.branch_id and not user.is_superuser:
        queryset = queryset.filter(branch=employee.branch)
    return queryset


def advisor_queryset_for_user(user):
    return branch_limited_employee_queryset(
        user,
        Employee.objects.filter(
            Q(employee_type__iexact="Advisor")
            | Q(designation__iexact="Advisor"),
            is_active=True
        ),
    ).order_by("name")


def active_employee_queryset_for_user(user):
    return branch_limited_employee_queryset(
        user,
        Employee.objects.filter(is_active=True),
    ).order_by("name")



class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class InsuranceCompanyForm(forms.ModelForm):
    class Meta:
        model = InsuranceCompany
        fields = '__all__'
        widgets = {
            'ins_co_name': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_no': forms.TextInput(attrs={'class': 'form-control'}),

            'cashless': forms.CheckboxInput(attrs={'class': 'form-check-input'}),

            'claim_manager_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),

            'moa_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'net_moa_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),

            'dms_code': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_hash': forms.TextInput(attrs={'class': 'form-control'}),
        }
# forms.py



class VehicleForm(forms.ModelForm):
    assigned_drivers = forms.ModelMultipleChoiceField(
        queryset=DriverMaster.objects.none(), required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 5})
    )
    class Meta:
        model = Vehicle
        fields = '__all__'
        widgets = {
            'sale_date': forms.DateInput(attrs={'type': 'date'}),
            'policy_start_date': forms.DateInput(attrs={'type': 'date'}),
            'policy_end_date': forms.DateInput(attrs={'type': 'date'}),
            'last_service_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_registration_no(self):
        reg = normalize_vehicle_number(self.cleaned_data.get('registration_no'))

        if not is_valid_vehicle_number(reg):
            raise forms.ValidationError(VEHICLE_NUMBER_ERROR)

        qs = Vehicle.objects.filter(registration_no__iexact=reg)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Registration number already exists")

        return reg

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "primary_driver" in self.fields:
            vehicle_id = self.instance.pk if self.instance and self.instance.pk else None
            self.fields["primary_driver"].queryset = DriverMaster.objects.filter(
                Q(vehicle_id=vehicle_id) | Q(vehicle__isnull=True), is_active=True
            ).order_by("name")
            self.fields["primary_driver"].widget.attrs.update({"class": "form-select"})
        if self.instance and self.instance.pk:
            # While editing, show only drivers already assigned to this vehicle.
            self.fields["assigned_drivers"].queryset = DriverMaster.objects.filter(
                Q(vehicle=self.instance) | Q(vehicle__isnull=True), is_active=True
            ).order_by("name")
        else:
            # A new vehicle has no related drivers yet; allow assigning active
            # unassigned drivers during the initial save.
            self.fields["assigned_drivers"].queryset = DriverMaster.objects.filter(
                vehicle__isnull=True, is_active=True
            ).order_by("name")
        if self.instance and self.instance.pk:
            self.fields["assigned_drivers"].initial = DriverMaster.objects.filter(vehicle=self.instance)

    def clean_assigned_drivers(self):
        drivers = self.cleaned_data.get("assigned_drivers")
        if drivers and len(drivers) > 5:
            raise forms.ValidationError("A vehicle can have a maximum of 5 drivers.")
        return drivers

        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

        # dropdown styling
        self.fields['model'].widget.attrs.update({'class': 'form-select'})
        self.fields['variant'].widget.attrs.update({'class': 'form-select'})
        self.fields['vehicle_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['customer'].widget.attrs.update({'class': 'form-select'})
        self.fields['insurance_company'].widget.attrs.update({
            'class': 'form-select',
            'id': 'id_vehicle_insurance_company',
        })


class DriverMasterForm(forms.ModelForm):
    class Meta:
        model = DriverMaster
        fields = "__all__"
        widgets = {
            "license_valid_until": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "driver_type": forms.Select(attrs={"class": "form-select"}),
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "license_document": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".pdf,image/*"}),
            "face_photo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }



class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'customer_type',
            'name',
            'salutation',
            'gender',
            'date_of_birth',
            'anniversary_date',
            'gst_registered',
            'gst_no',
            'pan_no',
            'aadhaar_no',
            'mobile_no',
            'alternate_mobile_no',
            'whatsapp_no',
            'email',
            'preferred_contact_method',
            'address_line_1',
            'address_line_2',
            'address',
            'city',
            'state',
            'pin_code',
            'country',
            'company_name',
            'contact_person',
            'designation',
            'company_gst_no',
        ]

        widgets = {
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'salutation': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'anniversary_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gst_registered': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gst_no': forms.TextInput(attrs={'class': 'form-control'}),
            'pan_no': forms.TextInput(attrs={'class': 'form-control'}),
            'aadhaar_no': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'alternate_mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp_no': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'preferred_contact_method': forms.Select(attrs={'class': 'form-select'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'company_gst_no': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_mobile_no(self):
        mobile = self.cleaned_data.get('mobile_no')

        if mobile:
            qs = Customer.objects.filter(mobile_no=mobile)

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError("Mobile number already exists")

        return mobile

    def clean_gst_no(self):
        gst = self.cleaned_data.get('gst_no')

        if gst:
            qs = Customer.objects.filter(gst_no=gst)

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError("GST already exists")

        return gst

    def save(self, commit=True):
        instance = super().save(commit=False)

        if instance.gst_no:
            instance.gst_registered = True

        if not instance.address and (instance.address_line_1 or instance.address_line_2):
            instance.address = "\n".join(
                part for part in [
                    instance.address_line_1,
                    instance.address_line_2
                ]
                if part
            )

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class SurveyorForm(forms.ModelForm):
                    class Meta:
                        model = Surveyor
                        fields = '__all__'

                    def clean_mobile_no(self):
                        mobile = self.cleaned_data.get("mobile_no")

                        if mobile and Surveyor.objects.filter(mobile_no=mobile).exists():
                            raise forms.ValidationError("Mobile already exists")

                        return mobile



class EmployeeForm(forms.ModelForm):
                        class Meta:
                            model = Employee
                            fields = '__all__'

                        def clean_employee_code(self):
                            code = self.cleaned_data.get("employee_code")

                            self.fields['employee_type'].widget.attrs.update({'class': 'form-select'})

                            if Employee.objects.filter(employee_code=code).exclude(id=self.instance.id).exists():
                                raise forms.ValidationError("Employee code already exists")


                            return code



class ClaimForm(forms.ModelForm):

    class Meta:
        model = Claim

        exclude = [
            "claim_stage",
        ]

        widgets = {
            'claim_no': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),

            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'insurance_company': forms.Select(attrs={'class': 'form-select'}),
            'policy_no': forms.TextInput(attrs={'class': 'form-control'}),
            'ic_claim_no': forms.TextInput(attrs={'class': 'form-control'}),
            'claim_type': forms.Select(attrs={'class': 'form-select'}),
            'accident_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'intimation_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format="%Y-%m-%dT%H:%M"),
            'survey_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format="%Y-%m-%dT%H:%M"),
            'surveyor': forms.Select(attrs={'class': 'form-select'}),
            'survey_status': forms.Select(attrs={'class': 'form-select'}),
            'self_survey': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estimated_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'approved_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'pre_invoice_sent_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format="%Y-%m-%dT%H:%M"),
            'pre_invoice_part_amount': forms.NumberInput(attrs={
                'class': 'form-control liability-amount',
                'step': '1',
            }),
            'pre_invoice_labour_amount': forms.NumberInput(attrs={
                'class': 'form-control liability-amount',
                'step': '1',
            }),
            'pre_invoice_total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'readonly': True
            }),
            'pre_invoice_file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'liability_received_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format="%Y-%m-%dT%H:%M"),
            'liability_do_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1','step': '1'
            }),
            'liability_document': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'invoice_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format="%Y-%m-%dT%H:%M"),
            'invoice_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
            }),
            'invoice_parts_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
            }),
            'invoice_labour_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
            }),
            'customer_difference_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'readonly': True
            }),
            'payment_mode': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'delivery_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format="%Y-%m-%dT%H:%M"),
            'delivered_by': forms.Select(attrs={
                'class': 'form-select'
            }),
            'delivered_to': forms.Select(attrs={
                'class': 'form-select'
            }),
            'delivery_driver_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'delivery_remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            "insurance_approval_date": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }, format="%Y-%m-%dT%H:%M"),

            "insurance_note": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "assessment_file": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }


    def __init__(self, *args, **kwargs):

        user = kwargs.pop('user', None)
        if args:
            data = args[0]
            if hasattr(data, "get") and data.get("status") == "Created":
                data = data.copy()
                data["status"] = "Open"
                args = (data, *args[1:])

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.status == "Created":
            self.instance.status = "Open"
            self.initial["status"] = "Open"

        self.fields["pre_invoice_sent_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["liability_received_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["invoice_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["delivery_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["intimation_date"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["survey_date"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["insurance_approval_date"].input_formats = ["%Y-%m-%dT%H:%M"]

        # =====================================
        # ONLY ADVISORS
        # =====================================

        self.fields['employee'].queryset = advisor_queryset_for_user(user)

        self.fields["delivered_by"].queryset = active_employee_queryset_for_user(user)

        logged_emp = logged_employee_for_user(user)

        # =====================================
        # ADVISOR LOGIN
        # =====================================

        if logged_emp and logged_emp.employee_type.upper() == "ADVISOR":

            self.fields['employee'].initial = logged_emp.id

            self.fields['employee'].disabled = True

    def clean_status(self):
        status = self.cleaned_data.get("status")
        return "Open" if status == "Created" else status




class JobCardForm(forms.ModelForm):

    class Meta:

        model = JobCard

        fields = "__all__"

        exclude = [
            "claim",
            "vehicle",
            "branch",
            "created_at",
            "job_date",
            "parts_total",
            "labour_total",
            "grand_total",
            "gst_amount",
            "net_total",
            "repair_status",
            "qc_done",
            "reinspection_done",
            "reinspection_date",
            "reinspection_done_by",
        ]

        widgets = {

            # =====================================
            # BASIC
            # =====================================

            "job_no": forms.TextInput(attrs={
                "class": "form-control",
                "readonly": False
            }),

            "job_date": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            "jobcard_type": forms.Select(attrs={
                "class": "form-select"
            }),

            'employee': forms.Select(attrs={'class': 'form-select'}),

            "advisor": forms.Select(attrs={
                "class": "form-select"
            }),

            # =====================================
            # VEHICLE INWARD
            # =====================================

            "vehicle_inward_type": forms.Select(attrs={
                "class": "form-select"
            }),

            "vehicle_inward_by": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "gate_in_datetime": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            "expected_delivery_datetime": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            "km": forms.NumberInput(attrs={
                "class": "form-control"
            }),

            "fuel_level": forms.TextInput(attrs={
                "class": "form-control"
            }),

            # =====================================
            # PART ORDER
            # =====================================

            "part_order_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            "part_order_no": forms.TextInput(attrs={
                "class": "form-control"
            }),

            # =====================================
            # WORKSHOP
            # =====================================

            "estimated_delivery": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            "actual_delivery": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local"
            }),

            # =====================================
            # REPAIR DETAILS
            # =====================================

            "repair_instructions": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4
            }),

            "road_test_done": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

            "washing_done": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

            "ready_for_delivery": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        # =====================================
        # AUTOCOMPLETE OFF
        # =====================================

        for field in self.fields.values():

            field.widget.attrs.setdefault(
                "autocomplete",
                "off"
            )

        # =====================================
        # ONLY TECHNICIAN IN TECHNICIAN DROPDOWN
        # =====================================

        # =====================================
        # ONLY ADVISOR IN ADVISOR DROPDOWN
        # =====================================

        self.fields["advisor"].queryset = advisor_queryset_for_user(user)
        if "employee" in self.fields:
            self.fields["employee"].queryset = active_employee_queryset_for_user(user)

from django import forms
from .models import CompanySetup

class CompanySetupForm(forms.ModelForm):
    class Meta:
        model = CompanySetup
        fields = '__all__'

        widgets = {
            'address': forms.Textarea(attrs={'rows':3}),
            'invoice_footer': forms.Textarea(attrs={'rows':3}),
        }


class ItemExcelUploadForm(forms.Form):
    excel_file = forms.FileField()
from django.contrib.auth.models import User
from django import forms
from rbac.models import Menu


class UserCreateForm(forms.ModelForm):

    menus = forms.ModelMultipleChoiceField(

        queryset=Menu.objects.all(),

        required=False,

        widget=forms.CheckboxSelectMultiple

    )

    class Meta:

        model = User

        fields = [

            "username",

            "email",

            "password",

            "menus"

        ]
