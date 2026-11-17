from django import forms
from .models import Subscription


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = (
            'name', 'category', 'vendor', 'cost', 'currency', 'billing_cycle',
            'next_renewal_date', 'managed_by', 'account_email', 'payment_method',
            'reminder_days_before', 'is_active', 'notes',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'vendor': forms.TextInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 3}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'next_renewal_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'managed_by': forms.Select(attrs={'class': 'form-select'}),
            'account_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control'}),
            'reminder_days_before': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
