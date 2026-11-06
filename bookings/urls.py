from django.urls import path

from . import views

urlpatterns = [
    path("show/<int:show_id>/seats/", views.select_seats, name="select_seats"),
    path("show/<int:show_id>/checkout/", views.checkout, name="checkout"),
    path("my/", views.my_bookings, name="my_bookings"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("<str:reference>/", views.booking_detail, name="booking_detail"),
    path("<str:reference>/cancel/", views.cancel_booking, name="cancel_booking"),
]
