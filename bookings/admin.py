from django.contrib import admin

from .models import BookedSeat, Booking


class BookedSeatInline(admin.TabularInline):
    model = BookedSeat
    extra = 0
    readonly_fields = ("seat_label", "show")
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "show", "seat_count", "total_amount", "status", "created_at")
    list_filter = ("status", "payment_method", "show__event", "created_at")
    search_fields = ("reference", "user__username", "user__email", "show__event__title")
    readonly_fields = ("reference", "created_at", "cancelled_at")
    inlines = [BookedSeatInline]
    actions = ["cancel_selected"]

    @admin.action(description="Cancel selected bookings and release seats")
    def cancel_selected(self, request, queryset):
        count = 0
        for booking in queryset.filter(status=Booking.Status.CONFIRMED):
            booking.cancel()
            count += 1
        self.message_user(request, f"Cancelled {count} booking(s).")


@admin.register(BookedSeat)
class BookedSeatAdmin(admin.ModelAdmin):
    list_display = ("seat_label", "show", "booking")
    list_filter = ("show",)
