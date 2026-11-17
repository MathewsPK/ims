"""Tender Radar module tests. A fake tender-radar executable stands in for the real tool."""
import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import User

from . import runner
from .models import TenderRun

FAKE_CLI = r'''#!{python}
import json, pathlib, sys
args = sys.argv[1:]
root = pathlib.Path(__file__).parent
if args[:1] == ["open"]:
    print(json.dumps([{{"portal": "goa", "tender_id": "2026_DOT_1", "score": 95, "label": "Strong match",
        "bucket": "daily", "title": "Ponda Fort Digital Museum O&M", "authority": "Department of Tourism",
        "portal_name": "Goa", "closes": "6 Nov 2026, 6:00 PM", "closes_iso": "2026-11-06T18:00:00+05:30",
        "days_left_text": "21 days left", "urgent": False, "value": "Not stated",
        "eligibility": "Check eligibility in the tender documents", "why": "digital museum",
        "link": "https://eprocure.goa.gov.in/nicgep/app?page=FrontEndAdvancedSearch&service=page",
        "link_is_direct": False, "emailed": False, "first_seen": "2026-10-16T07:00:00+00:00"}},
        {{"portal": "odisha", "tender_id": "2026_OCCL_9", "score": 70, "label": "Good match", "bucket": "daily",
        "title": "Hirakud Dam Museum Interiors", "authority": "Odisha Construction Corporation Ltd",
        "portal_name": "Odisha", "closes": "18 Oct 2026, 5:00 PM", "closes_iso": "2026-10-18T17:00:00+05:30",
        "days_left_text": "2 days left", "urgent": True, "value": "Not stated", "eligibility": "x", "why": "museum",
        "link": "", "link_is_direct": False, "emailed": True, "first_seen": "2026-10-15T07:00:00+00:00"}}]))
    sys.exit(0)
if "{fail}" == "1":
    print("[cppp] aborted: network down")
    sys.exit(2)
print("[cppp] harvesting CPPP (Central) ...")
print('[cppp] {{"tenders_new": 3, "candidates": 1}}')
d = root / "data" / "digests"; d.mkdir(parents=True, exist_ok=True)
(d / "digest-2026-10-16.md").write_text("Tender radar")
(d / "digest-2026-10-16.html").write_text("<h2>Tender radar</h2><p>Ponda Fort</p>")
print(f"5 tenders, 1 updates -> {{d / 'digest-2026-10-16.md'}} (sent: email)")
'''


def make_fake_radar(fail=False) -> Path:
    root = Path(tempfile.mkdtemp())
    (root / "pyproject.toml").write_text("[project]\nname='tender-radar'\n")
    exe = root / "fake-tender-radar"
    exe.write_text(FAKE_CLI.format(python=sys.executable, fail="1" if fail else "0"))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return root


class RunnerTests(TestCase):
    def setUp(self):
        self.root = make_fake_radar()
        self.ov = override_settings(TENDER_RADAR_DIR=str(self.root), TENDER_RADAR_CMD=str(self.root / "fake-tender-radar"))
        self.ov.enable()

    def tearDown(self):
        self.ov.disable()

    def test_execute_run_records_output_summary_and_email(self):
        run = TenderRun.objects.create(kind=TenderRun.Kind.SEARCH)
        runner.execute_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, TenderRun.Status.DONE)
        self.assertEqual((run.tenders_emailed, run.updates_emailed, run.email_sent), (5, 1, True))
        self.assertIn("harvesting CPPP", run.log)
        self.assertIn("Ponda Fort", run.digest_html)
        self.assertIn("emailed (email)", run.summary)

    def test_failed_tool_marks_run_failed(self):
        root = make_fake_radar(fail=True)
        with override_settings(TENDER_RADAR_DIR=str(root), TENDER_RADAR_CMD=str(root / "fake-tender-radar")):
            run = runner.execute_run(TenderRun.objects.create())
        self.assertEqual(run.status, TenderRun.Status.FAILED)
        self.assertIn("network down", run.log)

    def test_open_tenders(self):
        rows, err = runner.open_tenders()
        self.assertIsNone(err)
        self.assertEqual([r["tender_id"] for r in rows], ["2026_DOT_1", "2026_OCCL_9"])

    def test_only_one_run_at_a_time(self):
        with mock.patch.object(runner, "_spawn_worker") as spawn:
            first = runner.start_run(TenderRun.Kind.SEARCH)
            spawn.assert_called_once_with(first.pk)
            with self.assertRaises(runner.RunInProgress):
                runner.start_run(TenderRun.Kind.RESEND)

    def test_stale_run_does_not_block_forever(self):
        from django.utils import timezone
        from datetime import timedelta
        old = TenderRun.objects.create(status=TenderRun.Status.RUNNING)
        TenderRun.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(hours=4))
        self.assertIsNone(runner.active_run())
        old.refresh_from_db()
        self.assertEqual(old.status, TenderRun.Status.FAILED)

    def test_not_configured_message(self):
        with override_settings(TENDER_RADAR_DIR="", TENDER_RADAR_CMD=""):
            with mock.patch.dict(os.environ, {"TENDER_RADAR_DIR": "", "TENDER_RADAR_CMD": ""}):
                self.assertIn("TENDER_RADAR_DIR", runner.check_config())


class ViewTests(TestCase):
    def setUp(self):
        self.root = make_fake_radar()
        self.ov = override_settings(
            TENDER_RADAR_DIR=str(self.root), TENDER_RADAR_CMD=str(self.root / "fake-tender-radar"),
            SECURE_SSL_REDIRECT=False,
            STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                      "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
        self.ov.enable()
        self.manager = User.objects.create_user(email="m@test.local", password="x", name="Manager", role="MANAGER")
        self.engineer = User.objects.create_user(email="e@test.local", password="x", name="Eng", role="ENGINEER")

    def tearDown(self):
        self.ov.disable()

    def test_engineer_cannot_see_page(self):
        self.client.force_login(self.engineer)
        self.assertEqual(self.client.get(reverse("tenders:home")).status_code, 403)

    def test_manager_sees_tenders_and_buttons(self):
        self.client.force_login(self.manager)
        r = self.client.get(reverse("tenders:home"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("Ponda Fort Digital Museum O&amp;M", html)
        self.assertIn("Search now &amp; email", html)
        self.assertIn("1 closing within 3 days", html)
        self.assertIn("Tender Radar", html)            # sidebar link

    def test_filters(self):
        self.client.force_login(self.manager)
        html = self.client.get(reverse("tenders:home"), {"portal": "Odisha"}).content.decode()
        self.assertIn("Hirakud", html)
        self.assertNotIn("Ponda Fort", html)

    def test_button_starts_background_run(self):
        self.client.force_login(self.manager)
        with mock.patch.object(runner, "_spawn_worker") as spawn:
            r = self.client.post(reverse("tenders:start"), {"kind": "SEARCH"})
        run = TenderRun.objects.get()
        spawn.assert_called_once_with(run.pk)
        self.assertEqual(run.triggered_by, self.manager)
        self.assertRedirects(r, reverse("tenders:run_detail", args=[run.pk]), fetch_redirect_response=False)
        status = self.client.get(reverse("tenders:run_status", args=[run.pk])).json()
        self.assertTrue(status["active"])

    def test_get_does_not_start_a_run(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("tenders:start")).status_code, 405)

    def test_run_detail_shows_email(self):
        self.client.force_login(self.manager)
        run = runner.execute_run(TenderRun.objects.create(triggered_by=self.manager))
        html = self.client.get(reverse("tenders:run_detail", args=[run.pk])).content.decode()
        self.assertIn("srcdoc=", html)
        self.assertIn("Ponda Fort", html)

    def test_scheduled_command(self):
        from django.core.management import call_command
        call_command("run_tender_radar", "--scheduled")
        run = TenderRun.objects.get()
        self.assertTrue(run.scheduled)
        self.assertEqual(run.status, TenderRun.Status.DONE)
