from django import forms
from .models import GoogleCalendarFeed, NotificationEvent


class GoogleCalendarFeedForm(forms.ModelForm):
    """Self-service form: users connect their own private calendar."""

    class Meta:
        model = GoogleCalendarFeed
        fields = ('name', 'ical_url', 'color')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. My Google Calendar',
            }),
            'ical_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://calendar.google.com/calendar/ical/…/basic.ics',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color', 'type': 'color',
            }),
        }

    def clean_ical_url(self):
        url = self.cleaned_data['ical_url'].strip()
        if 'calendar.google.com' in url and not url.endswith('.ics'):
            raise forms.ValidationError(
                "That doesn't look like the secret iCal address — it should end in .ics. "
                "In Google Calendar: Settings → your calendar → Integrate calendar → "
                "'Secret address in iCal format'."
            )
        return url


class NotificationEventForm(forms.ModelForm):
    class Meta:
        model = NotificationEvent
        fields = ('title', 'description', 'event_type', 'event_datetime',
                  'location', 'meeting_link', 'assigned_to', 'all_users')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'event_datetime': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'meeting_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://meet.google.com/… or Teams/Zoom link',
            }),
            'assigned_to': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'all_users': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate datetime field in correct format
        if self.instance.pk and self.instance.event_datetime:
            self.initial['event_datetime'] = self.instance.event_datetime.strftime(
                '%Y-%m-%dT%H:%M'
            )
