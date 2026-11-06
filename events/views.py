from collections import OrderedDict

from django.db.models import Min, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Category, Event, Venue


def home(request):
    now = timezone.now()
    events = (
        Event.objects.filter(is_active=True, shows__start_time__gt=now)
        .select_related("category")
        .annotate(next_show=Min("shows__start_time"), min_price=Min("shows__price"))
        .distinct()
    )

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    city = request.GET.get("city", "").strip()

    if q:
        events = events.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        events = events.filter(category__slug=category)
    if city:
        events = events.filter(shows__venue__city__iexact=city, shows__start_time__gt=now)

    context = {
        "events": events.order_by("next_show"),
        "categories": Category.objects.all(),
        "cities": Venue.objects.values_list("city", flat=True).distinct().order_by("city"),
        "q": q,
        "selected_category": category,
        "selected_city": city,
    }
    return render(request, "events/home.html", context)


def event_detail(request, slug):
    event = get_object_or_404(Event.objects.select_related("category"), slug=slug, is_active=True)
    shows_by_date = OrderedDict()
    for show in event.upcoming_shows().order_by("start_time"):
        day = timezone.localtime(show.start_time).date()
        shows_by_date.setdefault(day, []).append(show)
    return render(request, "events/event_detail.html",
                  {"event": event, "shows_by_date": shows_by_date})
