from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "TicketHub Administration"
admin.site.site_title = "TicketHub Admin"
admin.site.index_title = "Manage events, shows and bookings"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("bookings/", include("bookings.urls")),
    path("", include("events.urls")),
]
