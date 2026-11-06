# TicketHub — Ticket Booking Management System (Django)

A full-stack ticket booking web app built with **Python + Django**, server-rendered templates,
Bootstrap 5 and a little vanilla JavaScript. Users browse events, pick a show, choose seats
on an interactive seat map, pay (simulated), and get an e-ticket. Staff manage everything
from the Django admin and a sales dashboard.

## Features

**Customers**
- Sign up, log in / log out, edit profile, change password
- Browse and search events; filter by category and city
- Event page with shows grouped by date, price and seats left
- Interactive seat map (booked seats greyed out, max 10 per booking, live total)
- Checkout with 5% convenience fee and payment-method choice (simulated payment)
- E-ticket page with booking reference (printable)
- My bookings: upcoming / past / cancelled tabs
- Cancel a booking up to 2 hours before the show (seats are released)

**Admin / staff**
- Django admin for categories, venues (rows × seats), events, shows, bookings
- Bulk-cancel bookings from admin
- Dashboard: revenue, tickets sold, cancellations, top events, occupancy of upcoming shows, recent bookings

**Under the hood**
- Double-booking is impossible: a database unique constraint on (show, seat) plus a
  transaction with `select_for_update` around checkout
- Booking logic lives in `bookings/services.py`, covered by tests in `bookings/tests.py`

## Project structure

```
django_ticket_booking/
├── manage.py
├── requirements.txt
├── ticketbooking/          # project config (settings, root urls, wsgi/asgi)
├── accounts/               # signup + profile (uses Django's built-in User)
├── events/                 # Category, Venue, Event, Show + listing/detail views
│   └── management/commands/seed_data.py   # demo data loader
├── bookings/               # Booking, BookedSeat, seat selection, checkout, dashboard
│   ├── services.py         # booking business rules
│   └── tests.py
├── templates/              # base layout + page templates per app
└── static/                 # css/style.css, js/seats.js
```

## Setup (Windows / macOS / Linux)

Requires Python 3.10+.

```bash
cd django_ticket_booking
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

python manage.py makemigrations accounts events bookings
python manage.py migrate
python manage.py seed_data          # demo events, shows, and users
python manage.py runserver
```

Open http://127.0.0.1:8000/

| Account | Username | Password |
|---|---|---|
| Admin (staff) | `admin` | `admin123` |
| Customer | `demo` | `demo12345` |

Admin panel: http://127.0.0.1:8000/admin/ · Dashboard: http://127.0.0.1:8000/bookings/dashboard/

Run tests:

```bash
python manage.py test
```

## Main URLs

| URL | Page |
|---|---|
| `/` | Event listing + search |
| `/events/<slug>/` | Event detail & shows |
| `/bookings/show/<id>/seats/` | Seat selection |
| `/bookings/show/<id>/checkout/` | Review & pay |
| `/bookings/my/` | My bookings |
| `/bookings/<reference>/` | E-ticket |
| `/bookings/dashboard/` | Staff dashboard |
| `/accounts/signup/`, `/accounts/login/`, `/accounts/profile/` | Accounts |
| `/admin/` | Django admin |

## Configuration

Settings in `ticketbooking/settings.py`:

- `MAX_SEATS_PER_BOOKING` (default 10)
- `CANCELLATION_CUTOFF_HOURS` (default 2)
- `CONVENIENCE_FEE_PERCENT` (default 5)

Environment variables for deployment: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
`DJANGO_ALLOWED_HOSTS=yourdomain.com`. For production, switch `DATABASES` to PostgreSQL and run
`python manage.py collectstatic`.

## Ideas to extend

- Real payment gateway (Razorpay / Stripe)
- Email ticket with QR code on booking
- Seat hold timer (reserve seats for 10 minutes during checkout)
- Seat categories (Silver / Gold / Recliner) with different prices
- REST API with Django REST Framework for a mobile app
