"""Booking business logic, kept out of views so it is easy to test."""
from django.conf import settings
from django.db import IntegrityError, transaction

from events.models import Show

from .models import BookedSeat, Booking, price_breakdown


class BookingError(Exception):
    pass


def validate_seats(show, seats):
    """Clean and validate a list of seat labels for a show. Returns sorted unique labels."""
    seats = sorted({s.strip().upper() for s in seats if s and s.strip()},
                   key=lambda s: (s[0], int(s[1:]) if s[1:].isdigit() else 0))
    if not seats:
        raise BookingError("Please select at least one seat.")
    if len(seats) > settings.MAX_SEATS_PER_BOOKING:
        raise BookingError(f"You can book at most {settings.MAX_SEATS_PER_BOOKING} seats at once.")
    if not show.is_upcoming:
        raise BookingError("This show has already started.")
    valid = set(show.venue.all_seat_labels())
    invalid = [s for s in seats if s not in valid]
    if invalid:
        raise BookingError(f"Invalid seat(s): {', '.join(invalid)}")
    taken = show.booked_seat_labels().intersection(seats)
    if taken:
        raise BookingError(f"Sorry, already booked: {', '.join(sorted(taken))}. Please choose again.")
    return seats


def create_booking(user, show_id, seats, payment_method):
    """Atomically create a booking. Raises BookingError if any seat is taken."""
    try:
        with transaction.atomic():
            # Lock the show row so two checkouts for the same show are serialised
            # (on databases that support SELECT ... FOR UPDATE).
            show = Show.objects.select_for_update().select_related("venue", "event").get(pk=show_id)
            seats = validate_seats(show, seats)
            subtotal, fee, total = price_breakdown(show.price, len(seats))
            booking = Booking.objects.create(
                user=user, show=show, seat_count=len(seats),
                subtotal=subtotal, convenience_fee=fee, total_amount=total,
                payment_method=payment_method, seat_labels=",".join(seats),
            )
            BookedSeat.objects.bulk_create(
                [BookedSeat(booking=booking, show=show, seat_label=s) for s in seats]
            )
            return booking
    except IntegrityError:
        # The unique constraint caught a race with another buyer.
        raise BookingError("One or more seats were just booked by someone else. Please choose again.")
