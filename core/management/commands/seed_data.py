"""
python manage.py seed_data

Creates demo users, projects, tasks, AMC contracts, expenses, reports,
and notifications so the app is usable immediately after setup.
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed the database with demo data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding demo data...")
        self._users()
        self._projects()
        self._amc()
        self._tasks()
        self._expenses()
        self._reports()
        self._events()
        self.stdout.write(self.style.SUCCESS("\nDone. Login with admin@ims.local / admin123"))

    # ── Users ──────────────────────────────────────────────────────────────
    def _users(self):
        from users.models import User
        specs = [
            dict(email="admin@ims.local",    name="Admin User",       role="ADMIN",    phone="9000000001"),
            dict(email="manager@ims.local",  name="Priya Sharma",     role="MANAGER",  phone="9000000002"),
            dict(email="engineer@ims.local", name="Rahul Mehta",      role="ENGINEER", phone="9000000003"),
            dict(email="engineer2@ims.local",name="Anjali Desai",     role="ENGINEER", phone="9000000004"),
            dict(email="staff@ims.local",    name="Suresh Kumar",     role="STAFF",    phone="9000000005"),
        ]
        self.users = {}
        for spec in specs:
            u, created = User.objects.get_or_create(
                email=spec["email"],
                defaults={**spec, "username": spec["email"]},
            )
            if created:
                u.set_password("admin123")
                u.save()
                self.stdout.write(f"  Created {u.email}")
            self.users[spec["role"].lower() if spec["role"] != "ENGINEER" else ("engineer" if "2" not in spec["email"] else "engineer2")] = u
        # keep references
        self.admin    = self.users.get("admin")
        self.manager  = self.users.get("manager")
        self.engineer = self.users.get("engineer")
        self.engineer2 = self.users.get("engineer2")
        self.staff    = self.users.get("staff")

    # ── Projects ───────────────────────────────────────────────────────────
    def _projects(self):
        from projects.models import Project
        today = date.today()
        specs = [
            dict(name="Smart Building CCTV System",    client="TechCorp India Pvt Ltd",  location="Mumbai", status="ONGOING",    start_date=today - timedelta(days=120), end_date=today + timedelta(days=60)),
            dict(name="Solar Panel Installation",       client="GreenEnergy Solutions",   location="Pune",   status="ONGOING",    start_date=today - timedelta(days=45),  end_date=today + timedelta(days=90)),
            dict(name="Fire Alarm Upgrade",             client="HousingBoard Gujarat",    location="Surat",  status="COMPLETED",  start_date=today - timedelta(days=200), end_date=today - timedelta(days=20)),
            dict(name="Access Control Deployment",      client="IT Park Vadodara",        location="Vadodara",status="PLANNING", start_date=today + timedelta(days=10),  end_date=today + timedelta(days=120)),
            dict(name="Network Infrastructure Setup",   client="EduCampus Ltd",           location="Ahmedabad",status="ON_HOLD", start_date=today - timedelta(days=30),  end_date=today + timedelta(days=150)),
        ]
        self.projects = []
        for spec in specs:
            p, created = Project.objects.get_or_create(
                name=spec["name"],
                defaults={**spec, "created_by": self.admin, "description": f"Description for {spec['name']}"},
            )
            if created:
                p.assigned_users.set([self.manager, self.engineer, self.engineer2])
                self.stdout.write(f"  Created project: {p.name}")
            self.projects.append(p)

    # ── AMC ────────────────────────────────────────────────────────────────
    def _amc(self):
        from amc.models import AMCProject, Equipment
        today = date.today()
        specs = [
            dict(project=self.projects[0], contract_number="AMC-2024-001",
                 amc_start_date=today - timedelta(days=90), amc_end_date=today + timedelta(days=25)),   # expiring soon
            dict(project=self.projects[1], contract_number="AMC-2024-002",
                 amc_start_date=today - timedelta(days=30), amc_end_date=today + timedelta(days=335)),  # active
            dict(project=self.projects[2], contract_number="AMC-2023-010",
                 amc_start_date=today - timedelta(days=400), amc_end_date=today - timedelta(days=40)),  # expired
        ]
        eq_names = ["DVR Unit", "IP Camera Set", "Network Switch", "UPS Battery", "Control Panel"]
        brands   = ["Hikvision", "Dahua", "Cisco", "APC", "Siemens"]
        for spec in specs:
            amc, created = AMCProject.objects.get_or_create(
                project=spec["project"],
                defaults=spec,
            )
            if created:
                self.stdout.write(f"  Created AMC: {amc.project.name}")
                for i in range(random.randint(2, 4)):
                    Equipment.objects.create(
                        amc_project=amc,
                        name=eq_names[i % len(eq_names)],
                        brand=brands[i % len(brands)],
                        serial_number=f"SN{random.randint(10000,99999)}",
                        warranty_expiry=today + timedelta(days=random.randint(-30, 365)),
                        amc_date=spec["amc_start_date"],
                    )

    # ── Tasks ──────────────────────────────────────────────────────────────
    def _tasks(self):
        from tasks.models import Task
        today = date.today()
        specs = [
            dict(title="Install CCTV cameras on floor 3",  project=self.projects[0], assigned_to=self.engineer,  status="IN_PROGRESS", priority="HIGH",   start_date=today - timedelta(days=5),  end_date=today + timedelta(days=3)),
            dict(title="Configure NVR recording settings",  project=self.projects[0], assigned_to=self.engineer2, status="PENDING",     priority="MEDIUM", start_date=today,                     end_date=today + timedelta(days=7)),
            dict(title="Solar panel site survey",           project=self.projects[1], assigned_to=self.engineer,  status="COMPLETED",   priority="HIGH",   start_date=today - timedelta(days=15), end_date=today - timedelta(days=8)),
            dict(title="Prepare project handover report",   project=self.projects[2], assigned_to=self.manager,   status="PENDING",     priority="LOW",    start_date=today,                     end_date=today + timedelta(days=14)),
            dict(title="Submit monthly expense claims",     project=None,             assigned_to=self.engineer,  status="PENDING",     priority="URGENT", start_date=today,                     end_date=today + timedelta(days=1)),
            dict(title="Update equipment inventory",        project=self.projects[0], assigned_to=self.staff,     status="IN_PROGRESS", priority="MEDIUM", start_date=today - timedelta(days=2),  end_date=today + timedelta(days=5)),
            dict(title="Overdue task example",              project=self.projects[1], assigned_to=self.engineer2, status="PENDING",     priority="HIGH",   start_date=today - timedelta(days=10), end_date=today - timedelta(days=3)),
        ]
        for spec in specs:
            t, created = Task.objects.get_or_create(
                title=spec["title"],
                defaults={**spec, "created_by": self.manager},
            )
            if created:
                self.stdout.write(f"  Created task: {t.title}")

    # ── Expenses ──────────────────────────────────────────────────────────
    def _expenses(self):
        from expenses.models import Expense
        today = date.today()
        specs = [
            dict(user=self.engineer,  date=today - timedelta(days=5),  amount=1250, category="TRAVEL",   description="Train Mumbai → Pune", approval_status="APPROVED", project=self.projects[0]),
            dict(user=self.engineer,  date=today - timedelta(days=4),  amount=850,  category="STAY",     description="Hotel stay 1 night",  approval_status="APPROVED", project=self.projects[0]),
            dict(user=self.engineer2, date=today - timedelta(days=3),  amount=340,  category="FOOD",     description="Site visit meals",    approval_status="PENDING",  project=self.projects[1]),
            dict(user=self.engineer,  date=today - timedelta(days=2),  amount=4500, category="ELECTRICAL",description="Cable + connectors",  approval_status="PENDING",  project=self.projects[0]),
            dict(user=self.staff,     date=today - timedelta(days=1),  amount=200,  category="MISC",     description="Stationery",          approval_status="PENDING",  project=None),
            dict(user=self.manager,   date=today - timedelta(days=10), amount=8000, category="TRAVEL",   description="Client visit flights", approval_status="APPROVED", project=self.projects[2]),
        ]
        for spec in specs:
            e, created = Expense.objects.get_or_create(
                user=spec["user"], date=spec["date"], amount=spec["amount"],
                defaults=spec,
            )
            if created:
                self.stdout.write(f"  Created expense: ₹{e.amount} by {e.user.name}")

    # ── Reports ───────────────────────────────────────────────────────────
    def _reports(self):
        from reports.models import AMCReport
        from amc.models import AMCProject
        today = date.today()
        amcs = list(AMCProject.objects.all())
        specs = [
            dict(engineer=self.engineer, project=self.projects[0], date=today - timedelta(days=7),
                 work_done="Cleaned all CCTV camera lenses. Tested DVR recording. Replaced faulty cable on floor 2.",
                 issues_found="One camera showing intermittent signal loss on floor 1.",
                 recommendations="Replace Cat6 cable run on floor 1 during next visit.",
                 status="REVIEWED", amc_project=amcs[0] if amcs else None),
            dict(engineer=self.engineer2, project=self.projects[1], date=today - timedelta(days=3),
                 work_done="Inspected all 24 solar panels. Cleaned dust accumulation. Checked inverter logs.",
                 issues_found="",
                 recommendations="Schedule next cleaning in 45 days.",
                 status="SUBMITTED", amc_project=amcs[1] if len(amcs) > 1 else None),
        ]
        for spec in specs:
            r, created = AMCReport.objects.get_or_create(
                engineer=spec["engineer"], project=spec["project"], date=spec["date"],
                defaults=spec,
            )
            if created:
                self.stdout.write(f"  Created report: {r.project.name} by {r.engineer.name}")

    # ── Events ────────────────────────────────────────────────────────────
    def _events(self):
        from notifications.models import NotificationEvent
        from notifications.utils import notify_event
        now = timezone.now()
        specs = [
            dict(title="Weekly Team Standup",         event_type="MEETING",   event_datetime=now + timedelta(days=1, hours=2),   location="Conference Room A", all_users=True),
            dict(title="Site Inspection Review",      event_type="MEETING",   event_datetime=now + timedelta(days=3),            location="Mumbai Site",       all_users=False),
            dict(title="Field Engineer Interview",    event_type="INTERVIEW", event_datetime=now + timedelta(days=5, hours=3),   location="HQ Office",         all_users=False),
            dict(title="AMC Renewal Reminder Q1",     event_type="REMINDER",  event_datetime=now + timedelta(days=7),            location="",                  all_users=True),
        ]
        for spec in specs:
            ev, created = NotificationEvent.objects.get_or_create(
                title=spec["title"],
                defaults={**spec, "created_by": self.admin, "description": f"Details for: {spec['title']}"},
            )
            if created:
                if not ev.all_users:
                    ev.assigned_to.set([self.manager, self.engineer])
                    ev.save()
                notify_event(ev)
                self.stdout.write(f"  Created event: {ev.title}")
