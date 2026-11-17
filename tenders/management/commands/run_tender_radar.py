"""Run the tender radar and record it in IMS.

    python manage.py run_tender_radar --run-id 12     # worker for a run started by the IMS button
    python manage.py run_tender_radar --scheduled     # daily job (cron / Task Scheduler)
    python manage.py run_tender_radar --scheduled --resend

The scheduled form creates its own TenderRun so every run, manual or automatic, shows on the
Tender Radar page.
"""
from django.core.management.base import BaseCommand, CommandError

from tenders import runner
from tenders.models import TenderRun


class Command(BaseCommand):
    help = "Search tender portals and email matching tenders (records the run in IMS)."

    def add_arguments(self, parser):
        parser.add_argument('--run-id', type=int, help='Execute an already-recorded run (used by the IMS button)')
        parser.add_argument('--scheduled', action='store_true', help='Start and execute a new run now (daily job)')
        parser.add_argument('--resend', action='store_true', help='With --scheduled: only re-send open tenders')

    def handle(self, *args, **opts):
        if opts['run_id']:
            try:
                run = TenderRun.objects.get(pk=opts['run_id'])
            except TenderRun.DoesNotExist:
                raise CommandError(f"No TenderRun {opts['run_id']}")
        elif opts['scheduled']:
            if runner.active_run():
                self.stdout.write("A tender run is already in progress; skipping this scheduled run.")
                return
            kind = TenderRun.Kind.RESEND if opts['resend'] else TenderRun.Kind.SEARCH
            run = TenderRun.objects.create(kind=kind, scheduled=True)
        else:
            raise CommandError("Use --scheduled (daily job) or --run-id N")
        run = runner.execute_run(run)
        self.stdout.write(f"{run.get_status_display()}: {run.summary}")
        if run.status == TenderRun.Status.FAILED:
            raise CommandError(run.summary)
