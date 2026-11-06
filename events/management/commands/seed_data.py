from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Category, Event, Show, Venue

CATEGORIES = ["Movies", "Concerts", "Comedy", "Sports", "Theatre"]

VENUES = [
    ("PVR Phoenix", "Hyderabad", "Phoenix Mall, Hitech City", 10, 14),
    ("Shilpakala Vedika", "Hyderabad", "Madhapur", 8, 16),
    ("INOX Forum", "Bengaluru", "Forum Mall, Koramangala", 9, 12),
    ("NSCI Dome", "Mumbai", "Worli", 12, 20),
]

EVENTS = [
    ("Interstellar Odyssey", "Movies", "English", 165,
     "A crew of astronauts travels through a wormhole in search of a new home for humanity.", "450.00"),
    ("Monsoon Melodies Live", "Concerts", "Hindi", 150,
     "An evening of Bollywood classics and indie hits performed by a live orchestra.", "1499.00"),
    ("Stand-Up Saturday", "Comedy", "English", 90,
     "Four of the country's sharpest comics, one hilarious night.", "699.00"),
    ("Kabaddi League Final", "Sports", "Telugu", 120,
     "Watch the season's top two teams battle it out for the championship.", "350.00"),
    ("The Last Act", "Theatre", "English", 110,
     "A gripping stage drama about an ageing actor's final performance.", "800.00"),
    ("Pushpa Returns", "Movies", "Telugu", 170,
     "The action-packed sequel everyone has been waiting for.", "300.00"),
]

SHOW_TIMES = [time(11, 0), time(15, 30), time(19, 45)]


class Command(BaseCommand):
    help = "Load demo categories, venues, events, shows and an admin + demo user."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="Days of shows to create.")

    def handle(self, *args, **opts):
        cats = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}

        venues = []
        for name, city, address, rows, per_row in VENUES:
            v, _ = Venue.objects.get_or_create(
                name=name, city=city,
                defaults={"address": address, "rows": rows, "seats_per_row": per_row},
            )
            venues.append(v)

        events = []
        for title, cat, lang, dur, desc, price in EVENTS:
            e, _ = Event.objects.get_or_create(
                title=title,
                defaults={"category": cats[cat], "language": lang,
                          "duration_minutes": dur, "description": desc},
            )
            events.append((e, Decimal(price)))

        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        created = 0
        for day in range(opts["days"]):
            date = today + timedelta(days=day)
            for i, (event, price) in enumerate(events):
                venue = venues[(i + day) % len(venues)]
                slot = SHOW_TIMES[(i + day) % len(SHOW_TIMES)]
                start = timezone.make_aware(datetime.combine(date, slot), tz)
                if start <= timezone.now():
                    start += timedelta(days=opts["days"])  # push past slots into the future
                _, was_created = Show.objects.get_or_create(
                    venue=venue, start_time=start, defaults={"event": event, "price": price},
                )
                created += was_created

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin123")
            self.stdout.write("Created superuser  admin / admin123")
        if not User.objects.filter(username="demo").exists():
            User.objects.create_user("demo", "demo@example.com", "demo12345", first_name="Demo")
            self.stdout.write("Created user       demo / demo12345")

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {len(cats)} categories, {len(venues)} venues, "
            f"{len(events)} events, {created} new shows."
        ))
