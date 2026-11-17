"""Bridge between IMS and the tender_radar tool (a separate Python project with its own venv).

IMS never imports tender_radar; it runs its command-line tool. That keeps the two projects'
dependencies apart and means tender_radar can be updated on its own.

    start_run()      called by the button: records a TenderRun, launches a detached worker, returns
    execute_run()    the worker (manage.py run_tender_radar): runs the tool, streams its output
                     into TenderRun.log, stores the emailed digest
    open_tenders()   current open matches for the IMS page (tender-radar open)

Settings (in IMS .env):
    TENDER_RADAR_DIR   folder of the tender_radar project (the one with pyproject.toml)
    TENDER_RADAR_CMD   optional full path to the tender-radar executable
                       (default: <TENDER_RADAR_DIR>/.venv/Scripts/tender-radar.exe on Windows,
                        <TENDER_RADAR_DIR>/.venv/bin/tender-radar elsewhere)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import TenderRun

MAX_RUNTIME = timedelta(hours=3)
COMMANDS = {
    TenderRun.Kind.SEARCH: ["run", "--send"],
    TenderRun.Kind.RESEND: ["digest", "--send", "--weekly", "--resend"],
}
DIGEST_LINE = re.compile(r"(\d+) tenders?, (\d+) updates? -> (.+?\.md)(?: \(sent: ([^)]*)\))?")


class RadarNotConfigured(Exception):
    pass


class RunInProgress(Exception):
    def __init__(self, run):
        self.run = run
        super().__init__(f"A tender run is already in progress (started {run.created_at:%H:%M}).")


# ----------------------------------------------------------------- configuration
def radar_dir() -> Path:
    d = getattr(settings, 'TENDER_RADAR_DIR', '') or os.environ.get('TENDER_RADAR_DIR', '')
    if not d:
        raise RadarNotConfigured("TENDER_RADAR_DIR is not set in IMS .env")
    p = Path(d)
    if not (p / 'pyproject.toml').exists():
        raise RadarNotConfigured(f"TENDER_RADAR_DIR={p} does not contain the tender_radar project (no pyproject.toml)")
    return p


def radar_cmd() -> list[str]:
    explicit = getattr(settings, 'TENDER_RADAR_CMD', '') or os.environ.get('TENDER_RADAR_CMD', '')
    if explicit:
        return [explicit]
    base = radar_dir() / '.venv'
    exe = base / ('Scripts/tender-radar.exe' if os.name == 'nt' else 'bin/tender-radar')
    if not exe.exists():
        raise RadarNotConfigured(f"tender-radar not found at {exe}. Set TENDER_RADAR_CMD in IMS .env")
    return [str(exe)]


def check_config() -> str | None:
    """None if ready, else a human-readable problem for the page."""
    try:
        radar_cmd()
        return None
    except RadarNotConfigured as e:
        return str(e)


# ----------------------------------------------------------------- run lifecycle
def expire_stale_runs():
    """Runs whose worker died (server restart, PC shut down) would otherwise block new runs forever."""
    cutoff = timezone.now() - MAX_RUNTIME
    for run in TenderRun.objects.filter(status__in=[TenderRun.Status.QUEUED, TenderRun.Status.RUNNING],
                                        created_at__lt=cutoff):
        run.status = TenderRun.Status.FAILED
        run.finished_at = timezone.now()
        run.summary = "Stopped: no result after 3 hours (worker was interrupted)"
        run.save(update_fields=['status', 'finished_at', 'summary'])


def active_run():
    expire_stale_runs()
    return TenderRun.objects.filter(status__in=[TenderRun.Status.QUEUED, TenderRun.Status.RUNNING]).first()


def start_run(kind: str = TenderRun.Kind.SEARCH, user=None) -> TenderRun:
    """Record a run and launch the worker in the background. Returns immediately."""
    radar_cmd()                      # fail fast with a clear message if not configured
    running = active_run()
    if running:
        raise RunInProgress(running)
    run = TenderRun.objects.create(kind=kind, triggered_by=user)
    _spawn_worker(run.pk)
    return run


def _spawn_worker(run_id: int):
    manage = Path(settings.BASE_DIR) / 'manage.py'
    args = [sys.executable, str(manage), 'run_tender_radar', '--run-id', str(run_id)]
    kw = dict(cwd=str(settings.BASE_DIR), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL, close_fds=True)
    if os.name == 'nt':
        kw['creationflags'] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw['start_new_session'] = True   # survives the gunicorn worker that started it
    subprocess.Popen(args, **kw)


def execute_run(run: TenderRun) -> TenderRun:
    """Run tender_radar for this TenderRun, streaming output into run.log. Blocking."""
    run.status = TenderRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=['status', 'started_at'])
    lines: list[str] = []
    try:
        cmd = radar_cmd() + COMMANDS[run.kind]
        env = {**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8'}
        proc = subprocess.Popen(cmd, cwd=str(radar_dir()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace', env=env)
        last_save = timezone.now()
        for line in proc.stdout:
            lines.append(line.rstrip())
            if (timezone.now() - last_save).total_seconds() > 3:
                run.log = "\n".join(lines[-400:])
                run.save(update_fields=['log'])
                last_save = timezone.now()
        code = proc.wait(timeout=MAX_RUNTIME.total_seconds())
        _record_result(run, lines)
        run.status = TenderRun.Status.DONE if code == 0 else TenderRun.Status.FAILED
        if code != 0 and not run.summary:
            run.summary = f"tender-radar exited with code {code}; see log"
    except Exception as e:  # noqa: BLE001 - any failure must end up visible on the page
        lines.append(f"ERROR: {type(e).__name__}: {e}")
        run.status = TenderRun.Status.FAILED
        run.summary = f"{type(e).__name__}: {e}"[:300]
    run.log = "\n".join(lines[-400:])
    run.finished_at = timezone.now()
    run.save()
    return run


def _record_result(run: TenderRun, lines: list[str]):
    for line in reversed(lines):
        m = DIGEST_LINE.search(line)
        if not m:
            continue
        run.tenders_emailed, run.updates_emailed = int(m.group(1)), int(m.group(2))
        channels = (m.group(4) or '').strip()
        run.email_sent = 'email' in channels or 'telegram' in channels
        html_path = Path(m.group(3).strip()).with_suffix('.html')
        if not html_path.is_absolute():
            html_path = radar_dir() / html_path
        if html_path.exists():
            run.digest_html = html_path.read_text(encoding='utf-8', errors='replace')
        sent = f"emailed ({channels})" if run.email_sent else "not emailed (no email set up in tender_radar.env)"
        run.summary = f"{run.tenders_emailed} tenders, {run.updates_emailed} updates · {sent}"
        return
    if not run.summary:
        run.summary = "Finished, but no digest line found in the output"


# ----------------------------------------------------------------- data for the page
def open_tenders(min_score: int = 60) -> tuple[list[dict], str | None]:
    """Current open matches from tender_radar's database. Returns (rows, error)."""
    try:
        out = subprocess.run(radar_cmd() + ['open', '--min', str(min_score)], cwd=str(radar_dir()),
                             capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    except RadarNotConfigured as e:
        return [], str(e)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [], f"Could not read tenders: {e}"
    if out.returncode != 0:
        return [], (out.stderr or out.stdout or 'tender-radar open failed').strip()[-500:]
    try:
        return json.loads(out.stdout or '[]'), None
    except json.JSONDecodeError:
        return [], "tender-radar returned unreadable data (is tender_radar v0.4 or newer installed?)"
