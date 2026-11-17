from django import forms
from .models import AMCReport, ReportImage, InstallationReport


class AMCReportForm(forms.ModelForm):
    class Meta:
        model = AMCReport
        fields = ('project', 'amc_project', 'date', 'work_done',
                  'issues_found', 'recommendations', 'client_signature')
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'amc_project': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'work_done': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Describe the maintenance work performed...',
            }),
            'issues_found': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'List any issues found...',
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Recommendations for next visit...',
            }),
            'client_signature': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ReportReviewForm(forms.ModelForm):
    class Meta:
        model = AMCReport
        fields = ('status', 'review_note')
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'review_note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InstallationReportForm(forms.ModelForm):
    class Meta:
        model = InstallationReport
        fields = ('project', 'installation_date', 'notes')
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Optional notes about the installed equipment...',
            }),
        }
