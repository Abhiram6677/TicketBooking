from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from events.models import Event, Show

from .models import Booking, price_breakdown
from .services import BookingError, create_booking, validate_seats

SESSION_KEY = "pending_booking"


@login_required
def select_seats(request, show_id):
    show = get_object_or_404(Show.objects.select_related("event", "venue"), pk=show_id)
    if not show.is_upcoming:
        messages.error(request, "This show is no longer available for booking.")
        return redirect(show.event.get_absolute_url())

    if request.method == "POST":
        try:
            seats = validate_seats(show, request.POST.getlist("seats"))
        except BookingError as e:
            messages.error(request, str(e))
            return redirect("select_seats", show_id=show.id)
        request.session[SESSION_KEY] = {"show_id": show.id, "seats": seats}
        return redirect("checkout", show_id=show.id)

    return render(request, "bookings/select_seats.html", {
        "show": show,
        "seat_map": show.seat_map(),
        "max_seats": settings.MAX_SEATS_PER_BOOKING,
        "fee_percent": settings.CONVENIENCE_FEE_PERCENT,
    })


@login_required
def checkout(request, show_id):
    show = get_object_or_404(Show.objects.select_related("event", "venue"), pk=show_id)
    pending = request.session.get(SESSION_KEY)
    if not pending or pending.get("show_id") != show.id:
        messages.info(request, "Please select your seats first.")
        return redirect("select_seats", show_id=show.id)

    seats = pending["seats"]
    subtotal, fee, total = price_breakdown(show.price, len(seats))

    if request.method == "POST":
        method = request.POST.get("payment_method", Booking.PaymentMethod.UPI)
        if method not in Booking.PaymentMethod.values:
            method = Booking.PaymentMethod.UPI
        try:
            booking = create_booking(request.user, show.id, seats, method)
        except BookingError as e:
            request.session.pop(SESSION_KEY, None)
            messages.error(request, str(e))
            return redirect("select_seats", show_id=show.id)
        request.session.pop(SESSION_KEY, None)
        messages.success(request, f"Booking confirmed! Your reference is {booking.reference}.")
        return redirect(booking.get_absolute_url())

    return render(request, "bookings/checkout.html", {
        "show": show, "seats": seats, "subtotal": subtotal, "fee": fee, "total": total,
        "fee_percent": settings.CONVENIENCE_FEE_PERCENT,
        "payment_methods": Booking.PaymentMethod.choices,
    })


@login_required
def my_bookings(request):
    bookings = request.user.bookings.select_related("show__event", "show__venue")
    now = timezone.now()
    return render(request, "bookings/my_bookings.html", {
        "upcoming": bookings.filter(status=Booking.Status.CONFIRMED, show__start_time__gt=now),
        "past": bookings.filter(status=Booking.Status.CONFIRMED, show__start_time__lte=now),
        "cancelled": bookings.filter(status=Booking.Status.CANCELLED),
    })


@login_required
def booking_detail(request, reference):
    qs = Booking.objects.select_related("show__event", "show__venue", "user")
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    booking = get_object_or_404(qs, reference=reference)
    return render(request, "bookings/booking_detail.html", {
        "booking": booking, "cutoff_hours": settings.CANCELLATION_CUTOFF_HOURS,
    })


@login_required
@require_POST
def cancel_booking(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if not booking.can_cancel:
        messages.error(request, f"This booking can't be cancelled (cancellations close "
                                f"{settings.CANCELLATION_CUTOFF_HOURS} hours before the show).")
    else:
        with transaction.atomic():
            booking.cancel()
        messages.success(request, f"Booking {booking.reference} cancelled. "
                                  f"₹{booking.total_amount} will be refunded to your original payment method.")
    return redirect(booking.get_absolute_url())


@staff_member_required
def dashboard(request):
    now = timezone.now()
    confirmed = Booking.objects.filter(status=Booking.Status.CONFIRMED)
    today_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "revenue": confirmed.aggregate(s=Sum("total_amount"))["s"] or 0,
        "tickets": confirmed.aggregate(s=Sum("seat_count"))["s"] or 0,
        "bookings": confirmed.count(),
        "cancelled": Booking.objects.filter(status=Booking.Status.CANCELLED).count(),
        "today_bookings": confirmed.filter(created_at__gte=today_start).count(),
        "upcoming_shows": Show.objects.filter(start_time__gt=now).count(),
        "active_events": Event.objects.filter(is_active=True).count(),
    }

    top_events = (
        Event.objects.annotate(
            revenue=Sum("shows__bookings__total_amount",
                        filter=Q(shows__bookings__status=Booking.Status.CONFIRMED)),
            tickets=Sum("shows__bookings__seat_count",
                        filter=Q(shows__bookings__status=Booking.Status.CONFIRMED)),
        )
        .filter(revenue__isnull=False)
        .order_by("-revenue")[:5]
    )

    upcoming = (
        Show.objects.filter(start_time__gt=now, start_time__lte=now + timedelta(days=3))
        .select_related("event", "venue")
        .annotate(sold=Count("booked_seats"))
        .order_by("start_time")[:10]
    )
    for s in upcoming:
        s.occupancy = round(100 * s.sold / s.venue.capacity) if s.venue.capacity else 0

    recent = Booking.objects.select_related("user", "show__event").order_by("-created_at")[:10]

    return render(request, "bookings/dashboard.html", {
        "stats": stats, "top_events": top_events, "upcoming": upcoming, "recent": recent,
    })
