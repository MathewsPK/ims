from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import IntegerWidget
from import_export.admin import ImportExportModelAdmin

from projects.models import Project
from .models import AMCProject, Equipment


# ---------------------------------------------------------------------------
# Date helper
# ---------------------------------------------------------------------------

def _to_iso_date(val):
    """
    Convert a date string to YYYY-MM-DD. Handles:
        DD-MM-YYYY, DD/MM/YYYY, DD-Mon-YY, DD-Mon-YYYY, YYYY-MM-DD
    Returns the original string unchanged if unparseable.
    """
    from datetime import datetime
    if not val or not str(val).strip():
        return val
    s = str(val).strip()
    for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%d-%b-%y', '%d-%b-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return s


DATE_COLUMNS = (
    'installation_date', 'warranty_expiry',
    'amc_date', 'amc_end_date', 'invoice_date',
)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

class AMCProjectResource(resources.ModelResource):
    class Meta:
        model = AMCProject
        fields = (
            'id', 'project', 'contract_number',
            'amc_start_date', 'amc_end_date',
            'contract_value', 'notes',
        )
        export_order = fields
        import_id_fields = ('contract_number',)
        skip_unchanged = True
        report_skipped = True

    def before_import(self, dataset, **kwargs):
        headers = dataset.headers or []
        for col in ('id', 'contract_number'):
            if col not in headers:
                dataset.append_col([''] * dataset.height, header=col)
        super().before_import(dataset, **kwargs)

    def get_instance(self, instance_loader, row):
        """
        If duplicate contract_numbers exist in the DB, pick the first (lowest pk)
        rather than crashing with MultipleObjectsReturned.
        """
        try:
            return super().get_instance(instance_loader, row)
        except AMCProject.MultipleObjectsReturned:
            contract_number = (row.get('contract_number') or '').strip()
            return AMCProject.objects.filter(
                contract_number=contract_number
            ).order_by('id').first()


class EquipmentResource(resources.ModelResource):
    """
    Handles myth-db CSV format.

    Key steps
    ---------
    before_import()     – inject blank 'amc_project_id'/'id' columns so
                          header-validation passes.
    before_import_row() – normalise keys, convert dates to ISO,
                          auto-create Project + AMCProject, inject FK id.
    get_instance()      – gracefully handle MultipleObjectsReturned by
                          returning the first (lowest pk) match.
    """

    amc_project_id = fields.Field(
        column_name='amc_project_id',
        attribute='amc_project_id',
        widget=IntegerWidget(),
    )

    class Meta:
        model = Equipment
        fields = (
            'id',
            'amc_project_id',
            'name',
            'brand',
            'model_number',
            'serial_number',
            'location',
            'installation_date',
            'warranty_expiry',
            'amc_date',
            'amc_end_date',
            'invoice_date',
            'invoice_no',
            'win_license',
            'notes',
        )
        export_order = fields
        import_id_fields = ('amc_project_id', 'name', 'serial_number')
        skip_unchanged = True
        report_skipped = True

    # ------------------------------------------------------------------
    def before_import(self, dataset, **kwargs):
        headers = dataset.headers or []
        for col in ('amc_project_id', 'id'):
            if col not in headers:
                dataset.append_col([''] * dataset.height, header=col)
        super().before_import(dataset, **kwargs)

    # ------------------------------------------------------------------
    def before_import_row(self, row, row_number=None, **kwargs):
        from datetime import date

        # 1. Normalise keys
        normalised = {}
        for k, v in row.items():
            key = k.strip().rstrip('.').lower().replace(' ', '_')
            normalised[key] = v
        row.clear()
        row.update(normalised)

        # 2. Convert date columns to ISO
        for col in DATE_COLUMNS:
            if col in row:
                row[col] = _to_iso_date(row[col])

        def clean(val):
            return (val or '').strip() or None

        # 3. If the row already points at a real, existing AMCProject, trust
        #    it as-is and skip the auto-create fallback entirely — this is
        #    the normal case for exports that already carry a valid
        #    amc_project_id (e.g. re-importing your own prior export).
        existing_id = (row.get('amc_project_id') or '').strip()
        if existing_id and AMCProject.objects.filter(pk=existing_id).exists():
            return

        contract_no = (row.get('amc_contract_number') or '').strip()
        client_name = clean(row.get('client')) or 'Unknown'

        # 4. Fallback chain for project name (only used when amc_project_id
        #    is missing/invalid, e.g. importing from a brand-new source CSV
        #    that never had our internal AMCProject IDs to begin with)
        proj_name = (
            clean(row.get('project'))
            or clean(row.get('client'))
            or (contract_no if contract_no else None)
            or 'Unknown Project'
        )

        # 5. Ensure Project exists
        project, _ = Project.objects.get_or_create(
            name=proj_name,
            defaults={
                'client':     client_name,
                'start_date': date.today(),
                'status':     'ONGOING',
            },
        )

        # 6. Ensure AMCProject exists
        effective_contract = contract_no or f'AUTO-{project.pk}'
        amc, _ = AMCProject.objects.get_or_create(
            project=project,
            contract_number=effective_contract,
            defaults={
                'amc_start_date': date.today(),
                'amc_end_date':   date.today(),
            },
        )

        row['amc_project_id'] = str(amc.pk)

    # ------------------------------------------------------------------
    def get_instance(self, instance_loader, row):
        """
        Return the existing Equipment for this row, or None if new.
        If duplicates exist in the DB, pick the first (lowest pk) rather
        than crashing with MultipleObjectsReturned.
        """
        try:
            return super().get_instance(instance_loader, row)
        except Equipment.MultipleObjectsReturned:
            return Equipment.objects.filter(
                amc_project_id=row.get('amc_project_id'),
                name=(row.get('name') or '').strip(),
                serial_number=(row.get('serial_number') or '').strip(),
            ).order_by('id').first()

    # ------------------------------------------------------------------
    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not (row.get('name') or '').strip():
            return True
        return super().skip_row(instance, original, row, import_validation_errors)


# ---------------------------------------------------------------------------
# Inline
# ---------------------------------------------------------------------------

class EquipmentInline(admin.TabularInline):
    model = Equipment
    extra = 0
    fields = (
        'name', 'brand', 'model_number', 'serial_number', 'location',
        'installation_date', 'warranty_expiry', 'amc_date', 'amc_end_date',
        'invoice_date', 'invoice_no', 'win_license', 'notes',
    )


# ---------------------------------------------------------------------------
# Admin registrations
# ---------------------------------------------------------------------------

@admin.register(AMCProject)
class AMCProjectAdmin(ImportExportModelAdmin):
    resource_class = AMCProjectResource
    list_display  = ('project', 'contract_number', 'amc_start_date', 'amc_end_date')
    list_filter   = ('amc_start_date', 'amc_end_date')
    search_fields = ('project__name', 'contract_number')
    inlines       = [EquipmentInline]


@admin.register(Equipment)
class EquipmentAdmin(ImportExportModelAdmin):
    resource_class = EquipmentResource

    def _create_log_entries(self, user_pk, rows):
        """Override to ignore skip/error import types that have no log action."""
        from django.contrib.admin.models import ADDITION, CHANGE, DELETION
        from import_export.results import RowResult
        logentry_map = {
            RowResult.IMPORT_TYPE_NEW: ADDITION,
            RowResult.IMPORT_TYPE_UPDATE: CHANGE,
            RowResult.IMPORT_TYPE_DELETE: DELETION,
        }
        for import_type, instances in rows.items():
            if import_type not in logentry_map:
                continue
            self._create_log_entry(user_pk, instances, import_type, logentry_map[import_type])
    list_display  = (
        'name', 'brand', 'serial_number', 'location',
        'amc_project', 'warranty_expiry', 'amc_end_date', 'invoice_no',
    )
    list_filter   = ('brand', 'amc_end_date', 'warranty_expiry')
    search_fields = ('name', 'serial_number', 'brand', 'location', 'invoice_no', 'win_license')
