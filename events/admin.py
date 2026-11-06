from django.contrib import admin

from .models import Category, Event, Show, Venue


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "rows", "seats_per_row", "capacity")
    list_filter = ("city",)
    search_fields = ("name", "city")


class ShowInline(admin.TabularInline):
    model = Show
    extra = 1


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "language", "duration_minutes", "is_active")
    list_filter = ("category", "language", "is_active")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ShowInline]


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ("event", "venue", "start_time", "price", "seats_booked", "seats_available")
    list_filter = ("venue__city", "venue", "event__category")
    search_fields = ("event__title", "venue__name")
    date_hierarchy = "start_time"
    autocomplete_fields = ("event", "venue")
