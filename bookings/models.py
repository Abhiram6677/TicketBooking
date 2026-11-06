import secrets
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from events.models import Show


def generate_reference():
    return "TKT" + secrets.token_hex(4).upper()


def price_breakdown(unit_price, seat_count):
    """Return (subtotal, fee, total) as Decimals rounded to 2 places."""
    subtotal = (Decimal(unit_price) * seat_count).quantize(Decimal("0.01"))
    fee = (subtotal * Decimal(settings.CONVENIENCE_FEE_PERCENT) / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return subtotal, fee, subtotal + fee


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    class PaymentMethod(models.TextChoices):
        UPI = "UPI", "UPI"
        CARD = "CARD", "Credit / Debit card"
        NETBANKING = "NETBANKING", "Net banking"

    reference = models.CharField(max_length=20, unique=True, default=generate_reference, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    show = models.ForeignKey(Show, on_delete=models.PROTECT, related_name="bookings")
    seat_count = models.PositiveSmallIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    convenience_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.UPI)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CONFIRMED)
    seat_labels = models.CharField(max_length=500, help_text="Comma-separated seat labels (kept after cancellation).")
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        return reverse("booking_detail", args=[self.reference])

    @property
    def seat_list(self):
        return [s for s in self.seat_labels.split(",") if s]

    @property
    def can_cancel(self):
        cutoff = self.show.start_time - timedelta(hours=settings.CANCELLATION_CUTOFF_HOURS)
        return self.status == self.Status.CONFIRMED and timezone.now() < cutoff

    def cancel(self):
        """Release the seats and mark the booking cancelled."""
        self.booked_seats.all().delete()
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.save(update_fields=["status", "cancelled_at"])

    def __str__(self):
        return f"{self.reference} — {self.user} — {self.show.event.title}"


class BookedSeat(models.Model):
    """One row per occupied seat. The unique constraint blocks double booking."""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="booked_seats")
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="booked_seats")
    seat_label = models.CharField(max_length=5)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["show", "seat_label"], name="unique_seat_per_show")
        ]
        ordering = ["seat_label"]

    def __str__(self):
        return f"{self.seat_label} ({self.show})"
