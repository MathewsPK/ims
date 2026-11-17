from django import forms
from .models import Project, ProjectMedia


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'client', 'location', 'description',
                  'start_date', 'end_date', 'status', 'assigned_users')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'client': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_users': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
        }


class ProjectMediaForm(forms.ModelForm):
    class Meta:
        model = ProjectMedia
        fields = ('image', 'caption')
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
        }
