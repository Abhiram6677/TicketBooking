import string

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Venue(models.Model):
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    address = models.CharField(max_length=255, blank=True)
    rows = models.PositiveSmallIntegerField(
        default=8, validators=[MinValueValidator(1), MaxValueValidator(26)],
        help_text="Number of seat rows (A–Z, max 26).",
    )
    seats_per_row = models.PositiveSmallIntegerField(
        default=12, validators=[MinValueValidator(1), MaxValueValidator(40)]
    )

    class Meta:
        ordering = ["city", "name"]
        unique_together = ("name", "city")

    @property
    def capacity(self):
        return self.rows * self.seats_per_row

    def row_labels(self):
        return list(string.ascii_uppercase[: self.rows])

    def all_seat_labels(self):
        return [f"{r}{n}" for r in self.row_labels() for n in range(1, self.seats_per_row + 1)]

    def __str__(self):
        return f"{self.name}, {self.city}"


class Event(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="events")
    description = models.TextField()
    language = models.CharField(max_length=40, default="English")
    duration_minutes = models.PositiveIntegerField(default=120)
    poster_url = models.URLField(blank=True, help_text="Optional image URL for the poster.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "event"
            slug, i = base, 2
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, i = f"{base}-{i}", i + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("event_detail", args=[self.slug])

    def upcoming_shows(self):
        return self.shows.filter(start_time__gt=timezone.now()).select_related("venue")

    def __str__(self):
        return self.title


class Show(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="shows")
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="shows")
    start_time = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2,
                                validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["start_time"]
        constraints = [
            models.UniqueConstraint(fields=["venue", "start_time"], name="unique_show_slot")
        ]

    @property
    def is_upcoming(self):
        return self.start_time > timezone.now()

    def booked_seat_labels(self):
        return set(self.booked_seats.values_list("seat_label", flat=True))

    @property
    def seats_booked(self):
        return self.booked_seats.count()

    @property
    def seats_available(self):
        return self.venue.capacity - self.seats_booked

    @property
    def is_housefull(self):
        return self.seats_available <= 0

    def seat_map(self):
        """Rows of seats for the template: [(row, [{'label','booked'}, ...]), ...]."""
        booked = self.booked_seat_labels()
        return [
            (row, [{"label": f"{row}{n}", "booked": f"{row}{n}" in booked}
                   for n in range(1, self.venue.seats_per_row + 1)])
            for row in self.venue.row_labels()
        ]

    def __str__(self):
        return f"{self.event.title} @ {self.venue} — {timezone.localtime(self.start_time):%d %b %Y %I:%M %p}"
