"""
Create starter data for demos and marking: service categories, one account
per role and a device key per simulated sensor.

The command is idempotent - running it twice never duplicates rows. Device
keys are only shown once at creation time because the database stores a hash.
"""

import os
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.requests.models import Category, ServiceRequest
from apps.telemetry.models import DeviceKey

DEMO_CATEGORIES = [
    "IT Support",
    "Facilities",
    "Safety",
    "Equipment",
    "Cleaning",
    "Security",
]

# name, device type used by the telemetry endpoints
DEMO_DEVICES = [
    ("network-monitor-01", DeviceKey.DeviceType.NETWORK),
    ("water-leak-01", DeviceKey.DeviceType.WATER),
    ("fire-smoke-01", DeviceKey.DeviceType.FIRE),
]


class Command(BaseCommand):
    help = "Seed categories, demo accounts and IoT device keys."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv("CSRMS_DEMO_PASSWORD", "Campus#2026")

        for name in DEMO_CATEGORIES:
            Category.objects.get_or_create(name=name)
        self.stdout.write(f"Categories ready ({len(DEMO_CATEGORIES)}).")

        accounts = [
            ("admin", User.Role.ADMIN, "Thabo", "Ndlovu"),
            ("lerato", User.Role.STAFF, "Lerato", "Mokoena"),
            ("naledi", User.Role.STUDENT, "Naledi", "Khumalo"),
        ]
        for username, role, first, last in accounts:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@spu.ac.za",
                    "role": role,
                },
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created {role.lower()} account: {username}"))
            else:
                self.stdout.write(f"Account exists: {username}")

        for name, device_type in DEMO_DEVICES:
            if DeviceKey.objects.filter(name=name).exists():
                self.stdout.write(f"Device key exists: {name} (raw key not shown again)")
                continue
            _, raw = DeviceKey.issue(name=name, device_type=device_type)
            self.stdout.write(self.style.WARNING(f"Device key for {name}: {raw}"))

        self._seed_requests()
        self._seed_telemetry()

        self.stdout.write(self.style.SUCCESS("Demo data seeded. Share the printed keys with the Wokwi sketches."))

    def _seed_requests(self):
        """
        A handful of tickets at different workflow stages so the dashboards,
        filters and charts have something to show on a fresh install. Uses the
        same service layer as the API so history and notifications look real.
        """
        from apps.requests.models import Category, RequestHistory
        from apps.requests.services import apply_status, assign_request, log_entry

        admin = User.objects.get(username="admin")
        staff = User.objects.get(username="lerato")
        student = User.objects.get(username="naledi")

        demo_tickets = [
            # title, category, location, priority, final status
            ("Projector will not display in Lab 2", "Equipment",
             "Academic Lab 2", "MEDIUM", ServiceRequest.Status.RESOLVED),
            ("WiFi drops out every evening in Residence A", "IT Support",
             "Residence A common room", "HIGH", ServiceRequest.Status.IN_PROGRESS),
            ("Broken window pane in lecture hall B", "Facilities",
             "Lecture hall B", "LOW", ServiceRequest.Status.PENDING),
        ]
        for title, category_name, location, priority, final_status in demo_tickets:
            if ServiceRequest.objects.filter(title=title).exists():
                continue
            ticket = ServiceRequest.objects.create(
                title=title,
                description=f"Reported via the campus portal. Please inspect {location}.",
                category=Category.objects.get(name=category_name),
                location=location,
                priority=priority,
                created_by=student,
            )
            log_entry(ticket, RequestHistory.EntryType.CREATED, changed_by=student,
                      comment="Request captured from the student portal.")
            if final_status != ServiceRequest.Status.PENDING:
                assign_request(ticket, staff, actor=admin)
            if final_status in (ServiceRequest.Status.IN_PROGRESS, ServiceRequest.Status.RESOLVED):
                apply_status(ticket, ServiceRequest.Status.IN_PROGRESS, actor=staff,
                             comment="Investigating now.")
            if final_status == ServiceRequest.Status.RESOLVED:
                apply_status(ticket, ServiceRequest.Status.RESOLVED, actor=staff,
                             comment="Fixed and confirmed with the reporter.")
        self.stdout.write("Demo requests ready (3).")

    def _seed_telemetry(self):
        """
        Backdate twelve hours of plausible readings so the sensor charts have
        shape on first load: steady network with one dip, moisture creeping up
        past the leak threshold, and calm fire/smoke numbers.
        """
        from apps.telemetry.models import TelemetryReading

        if TelemetryReading.objects.exists():
            self.stdout.write("Telemetry readings exist; leaving chart history alone.")
            return

        now = timezone.now()
        plans = {
            # sensor_type: (device_id, location, value_fn(hours_ago), secondary_fn)
            "network": ("net-01", "Campus core switch",
                        lambda h: 12 if 9 <= h <= 10 else random.uniform(8, 40), None),
            "water": ("water-01", "Residence C · geyser room",
                      lambda h: 30 + (12 - h) * 2.5, None),
            "fire": ("fire-01", "ICT building · server room",
                     lambda h: random.uniform(4, 12), lambda h: 21 + random.uniform(-1, 1.5)),
        }
        made = 0
        for hours_ago in range(12, -1, -2):  # every two hours, oldest first
            for sensor_type, (device_id, location, value_fn, secondary_fn) in plans.items():
                TelemetryReading.objects.create(
                    sensor_type=sensor_type,
                    recorded_at=now - timedelta(hours=hours_ago),
                    value=round(value_fn(hours_ago), 1),
                    secondary_value=round(secondary_fn(hours_ago), 1) if secondary_fn else None,
                    reachable=sensor_type == "network" and not 9 <= hours_ago <= 10,
                    location=location,
                    device_id=device_id,
                )
                made += 1
        self.stdout.write(f"Telemetry chart history ready ({made} readings).")
