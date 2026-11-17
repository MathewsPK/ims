from django import forms
from .models import Task, TimeLog, OutOfOffice


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('title', 'description', 'assigned_to', 'project',
                  'start_date', 'end_date', 'completed_date', 'status',
                  'priority', 'depends_on')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'completed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'depends_on': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['completed_date'].required = False
        self.fields['depends_on'].required = False
        # A task can't depend on itself, and only show other tasks as options
        qs = Task.objects.all().order_by('-created_at')
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        self.fields['depends_on'].queryset = qs
        self.fields['depends_on'].label = "Depends on (optional)"


class TimeLogForm(forms.ModelForm):
    class Meta:
        model = TimeLog
        fields = ('hours', 'date', 'notes')
        widgets = {
            'hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class OutOfOfficeForm(forms.ModelForm):
    class Meta:
        model = OutOfOffice
        fields = ('user', 'start_date', 'end_date', 'reason')
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional — e.g. Leave, Travel'}),
        }

    def __init__(self, *args, can_pick_user=False, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_pick_user:
            # Self-service: lock the user field to themselves and hide it
            self.fields['user'].widget = forms.HiddenInput()
            if current_user is not None:
                self.initial['user'] = current_user.pk

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError("End date can't be before start date.")
        return cleaned
