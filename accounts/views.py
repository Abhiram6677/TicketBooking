from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm, SignUpForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}! Your account is ready.")
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    stats = {
        "total": request.user.bookings.count(),
        "confirmed": request.user.bookings.filter(status="CONFIRMED").count(),
        "cancelled": request.user.bookings.filter(status="CANCELLED").count(),
    }
    return render(request, "accounts/profile.html", {"form": form, "stats": stats})
