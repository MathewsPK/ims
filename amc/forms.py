from django import forms
from .models import AMCProject, Equipment


class AMCProjectForm(forms.ModelForm):
    class Meta:
        model = AMCProject
        fields = ('project', 'contract_number', 'amc_start_date',
                  'amc_end_date', 'contract_value', 'notes')
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'amc_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amc_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = (
            'amc_project', 'name', 'brand', 'model_number', 'serial_number',
            'location', 'installation_date', 'warranty_expiry',
            'amc_date', 'amc_end_date', 'invoice_date', 'invoice_no',
            'win_license', 'notes',
        )
        widgets = {
            'amc_project': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model_number': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Gallery 1, Reception',
            }),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amc_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amc_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'invoice_no': forms.TextInput(attrs={'class': 'form-control'}),
            'win_license': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. XXXXX-XXXXX-XXXXX-XXXXX-XXXXX',
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
