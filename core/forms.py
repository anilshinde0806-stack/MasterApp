from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import InsuranceCompany, Claim
from .models import JobCard
from .models import Vehicle
from .models import Customer
from django import forms
from .models import Surveyor
from .models import Employee



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
    class Meta:
        model = Vehicle
        fields = '__all__'
        widgets = {
            'sale_date': forms.DateInput(attrs={'type': 'date'})
        }

    def clean_registration_no(self):
        reg = self.cleaned_data.get('registration_no')

        qs = Vehicle.objects.filter(registration_no__iexact=reg)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Registration number already exists")

        return reg

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

        # dropdown styling
        self.fields['model'].widget.attrs.update({'class': 'form-select'})
        self.fields['variant'].widget.attrs.update({'class': 'form-select'})
        self.fields['vehicle_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['customer'].widget.attrs.update({'class': 'form-select'})



class CustomerForm(forms.ModelForm):
            class Meta:
                model = Customer
                fields = [
                    'name',
                    'mobile_no',
                    'email',
                    'address',
                    'city',
                    'state',
                    'pin_code',
                    'gst_no'
                ]

                widgets = {
                    'name': forms.TextInput(attrs={'class': 'form-control'}),
                    'mobile_no': forms.TextInput(attrs={'class': 'form-control'}),
                    'email': forms.EmailInput(attrs={'class': 'form-control'}),
                    'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
                    'city': forms.TextInput(attrs={'class': 'form-control'}),
                    'state': forms.TextInput(attrs={'class': 'form-control'}),
                    'pin_code': forms.TextInput(attrs={'class': 'form-control'}),
                    'gst_no': forms.TextInput(attrs={'class': 'form-control'}),
                }

                def clean_mobile_no(self):
                    mobile = self.cleaned_data.get('mobile_no')

                    if mobile:
                        qs = Customer.objects.filter(mobile_no=mobile)

                        # 🔥 exclude self (for edit case)
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
            'intimation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'survey_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'surveyor': forms.Select(attrs={'class': 'form-select'}),
            'survey_status': forms.Select(attrs={'class': 'form-select'}),
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
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            "insurance_approval_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

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

        super().__init__(*args, **kwargs)

        self.fields["pre_invoice_sent_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["liability_received_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["invoice_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]

        # =====================================
        # ONLY ADVISORS
        # =====================================

        self.fields['employee'].queryset = Employee.objects.filter(
            employee_type="Advisor",
            is_active=True
        )

        logged_emp = Employee.objects.filter(
            user=user
        ).first()

        # =====================================
        # ADVISOR LOGIN
        # =====================================

        if logged_emp and logged_emp.employee_type.upper() == "ADVISOR":

            self.fields['employee'].initial = logged_emp.id

            self.fields['employee'].disabled = True




class JobCardForm(forms.ModelForm):

    class Meta:

        model = JobCard

        fields = "__all__"

        exclude = [
            "claim",
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

        self.fields["advisor"].queryset = (
            self.fields["advisor"]
            .queryset
            .filter(
                employee_type="Advisor"
            )
        )

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
