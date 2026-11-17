from django import forms
from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ('project', 'date', 'amount', 'category', 'description', 'receipt')
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ExpenseReviewForm(forms.ModelForm):
    """Admin/Manager review form."""
    class Meta:
        model = Expense
        fields = ('approval_status', 'review_note')
        widgets = {
            'approval_status': forms.Select(attrs={'class': 'form-select'}),
            'review_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
