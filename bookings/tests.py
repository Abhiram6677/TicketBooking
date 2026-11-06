from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Category, Event, Show, Venue

from .models import BookedSeat, Booking
from .services import BookingError, create_booking


class BookingFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Category.objects.create(name="Movies")
        venue = Venue.objects.create(name="Test Hall", city="Hyderabad", rows=3, seats_per_row=5)
        event = Event.objects.create(title="Test Movie", category=cat, description="x")
        cls.show = Show.objects.create(
            event=event, venue=venue, price=Decimal("200.00"),
            start_time=timezone.now() + timedelta(days=1),
        )
        cls.user = User.objects.create_user("alice", "a@example.com", "pass12345!")
        cls.other = User.objects.create_user("bob", "b@example.com", "pass12345!")

    def test_home_lists_event(self):
        resp = self.client.get(reverse("home"))
        self.assertContains(resp, "Test Movie")

    def test_seat_page_requires_login(self):
        resp = self.client.get(reverse("select_seats", args=[self.show.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_full_booking_flow(self):
        self.client.login(username="alice", password="pass12345!")
        resp = self.client.post(reverse("select_seats", args=[self.show.id]), {"seats": ["A1", "A2"]})
        self.assertRedirects(resp, reverse("checkout", args=[self.show.id]))
        resp = self.client.post(reverse("checkout", args=[self.show.id]), {"payment_method": "UPI"})
        booking = Booking.objects.get(user=self.user)
        self.assertRedirects(resp, booking.get_absolute_url())
        self.assertEqual(booking.seat_count, 2)
        self.assertEqual(booking.subtotal, Decimal("400.00"))
        self.assertEqual(booking.total_amount, Decimal("420.00"))  # 5% fee
        self.assertEqual(self.show.seats_available, 13)

    def test_double_booking_blocked(self):
        create_booking(self.user, self.show.id, ["B1"], "UPI")
        with self.assertRaises(BookingError):
            create_booking(self.other, self.show.id, ["B1", "B2"], "UPI")
        self.assertEqual(BookedSeat.objects.count(), 1)

    def test_invalid_seat_rejected(self):
        with self.assertRaises(BookingError):
            create_booking(self.user, self.show.id, ["Z99"], "UPI")

    def test_cancel_releases_seats(self):
        booking = create_booking(self.user, self.show.id, ["C1", "C2"], "CARD")
        self.client.login(username="alice", password="pass12345!")
        self.client.post(reverse("cancel_booking", args=[booking.reference]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertEqual(booking.seat_list, ["C1", "C2"])
        self.assertFalse(BookedSeat.objects.filter(show=self.show).exists())

    def test_user_cannot_view_others_booking(self):
        booking = create_booking(self.user, self.show.id, ["A5"], "UPI")
        self.client.login(username="bob", password="pass12345!")
        resp = self.client.get(reverse("booking_detail", args=[booking.reference]))
        self.assertEqual(resp.status_code, 404)

    def test_dashboard_staff_only(self):
        self.client.login(username="alice", password="pass12345!")
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.user.is_staff = True
        self.user.save()
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
