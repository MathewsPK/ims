from django.contrib import admin

from .models import TenderRun


@admin.register(TenderRun)
class TenderRunAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'kind', 'status', 'scheduled', 'triggered_by', 'tenders_emailed', 'email_sent')
    list_filter = ('kind', 'status', 'scheduled')
    readonly_fields = [f.name for f in TenderRun._meta.fields]
