"""
Seed script — populates database with sample data for development.
Run: python manage.py shell < seed_data.py
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "baantask.settings")
django.setup()

from datetime import date  # noqa: E402

from tasks.models import Task  # noqa: E402
from workers.models import Employer, Worker  # noqa: E402

# Clear existing data
Task.objects.all().delete()
Worker.objects.all().delete()
Employer.objects.all().delete()

print("Creating employers...")

employers_data = [
    {
        "first_name": "John",
        "last_name": "Smith",
        "email": "john@example.com",
        "phone": "+66812345678",
        "preferred_language": "en",
        "plan": "home",
    },
    {
        "first_name": "Анна",
        "last_name": "Петрова",
        "email": "anna@example.com",
        "phone": "+66898765432",
        "preferred_language": "ru",
        "plan": "management",
    },
    {
        "first_name": "Takeshi",
        "last_name": "Yamamoto",
        "email": "takeshi@example.com",
        "phone": "+66876543210",
        "preferred_language": "ja",
        "plan": "free",
    },
]

employers = []
for data in employers_data:
    emp = Employer.objects.create(**data)
    employers.append(emp)
    print(f"  Created: {emp}")

print("\nCreating workers...")

workers_data = [
    {
        "first_name": "Somchai",
        "last_name": "Jaidee",
        "nickname": "Chai",
        "phone": "+66891111111",
        "role": "maid",
        "employer": employers[0],
        "salary": 18000,
        "start_date": date(2025, 6, 1),
    },
    {
        "first_name": "Niran",
        "last_name": "Saetang",
        "nickname": "Nong",
        "phone": "+66892222222",
        "role": "driver",
        "employer": employers[0],
        "salary": 20000,
        "start_date": date(2025, 8, 15),
    },
    {
        "first_name": "Malai",
        "last_name": "Kaewkla",
        "nickname": "Mai",
        "phone": "+66893333333",
        "role": "nanny",
        "employer": employers[1],
        "salary": 22000,
        "start_date": date(2025, 3, 1),
    },
    {
        "first_name": "Prasert",
        "last_name": "Wongsawat",
        "nickname": "Sert",
        "phone": "+66894444444",
        "role": "gardener",
        "employer": employers[1],
        "salary": 15000,
        "start_date": date(2025, 9, 1),
    },
    {
        "first_name": "Kannika",
        "last_name": "Thongdee",
        "nickname": "Kan",
        "phone": "+66895555555",
        "role": "cook",
        "employer": employers[1],
        "salary": 25000,
        "start_date": date(2025, 1, 15),
    },
]

workers = []
for data in workers_data:
    w = Worker.objects.create(**data)
    workers.append(w)
    print(f"  Created: {w}")

print("\nCreating tasks...")

tasks_data = [
    {
        "title": "Clean living room and kitchen",
        "description": "Deep cleaning including windows and floor mopping",
        "employer": employers[0],
        "worker": workers[0],
        "status": "completed",
        "priority": "medium",
    },
    {
        "title": "Pick up kids from school",
        "description": "International School Bangkok, gate 3, at 15:30",
        "employer": employers[0],
        "worker": workers[1],
        "status": "assigned",
        "priority": "high",
    },
    {
        "title": "Подготовить ужин на 6 человек",
        "description": "Гости приходят в 19:00, тайская кухня, без острого",
        "employer": employers[1],
        "worker": workers[4],
        "status": "in_progress",
        "priority": "urgent",
    },
    {
        "title": "Постричь газон и полить цветы",
        "description": "Включая задний двор и зону у бассейна",  # noqa: RUF001
        "employer": employers[1],
        "worker": workers[3],
        "status": "created",
        "priority": "low",
    },
    {
        "title": "Забрать вещи из химчистки",
        "description": "Квитанция #4521, магазин на Soi 23",
        "employer": employers[1],
        "worker": workers[2],
        "status": "verified",
        "priority": "medium",
    },
    {
        "title": "Weekly grocery shopping",
        "description": "List in the kitchen. Tops Market on Sukhumvit.",
        "employer": employers[0],
        "worker": workers[0],
        "status": "created",
        "priority": "medium",
    },
]

for data in tasks_data:
    t = Task.objects.create(**data)
    print(f"  Created: {t}")

print(
    f"\nDone! Created {Employer.objects.count()} employers, "
    f"{Worker.objects.count()} workers, {Task.objects.count()} tasks."
)
