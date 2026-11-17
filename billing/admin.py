from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'cost', 'currency', 'billing_cycle',
        'next_renewal_date', 'managed_by', 'is_active',
    )
    list_filter = ('category', 'billing_cycle', 'is_active')
    search_fields = ('name', 'vendor', 'account_email')
    readonly_fields = ('last_reminder_sent',)
