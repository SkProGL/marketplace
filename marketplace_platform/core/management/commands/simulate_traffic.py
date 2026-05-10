"""
Generate synthetic ActivityLog rows so the /activity/ dashboard has data.

Writes directly via the ORM rather than making real HTTP requests — that
sidesteps login forms, CSRF, and django-axes lockouts, all of which add
no value for purely synthetic data.

Examples:
    # Seed ~500 events spread across the last 7 days, then exit:
    python manage.py simulate_traffic --backfill 500

    # Seed AND keep streaming new events at ~1/sec:
    python manage.py simulate_traffic --backfill 500 --rate 1

    # Stream only (no backfill):
    python manage.py simulate_traffic --rate 0.5
"""
import random
import time
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import ActivityLog

User = get_user_model()


# Anonymous-only paths (no user attached on the row).
ANON_PATHS = ['/', '/login/', '/signup/', '/terms/', '/community/']

# Authenticated-user paths shared by every category.
COMMON_AUTH_PATHS = ['/', '/community/', '/profile/', '/orders/', '/cart/contents/']

# Per-category extra paths.
CATEGORY_PATHS = {
    'Customer':   ['/cart/contents/', '/orders/recurring/'],
    'Restaurant': ['/cart/contents/', '/orders/recurring/'],
    'Community':  ['/community/'],
    'Producer':   ['/management/', '/finance/', '/inventory_upload/'],
    'Admin':      ['/management/', '/finance/'],
}

# Action mix per session — most events are page views, the rest are actions.
ACTION_MIX = [
    (ActivityLog.Action.PAGE_VIEW,    70),
    (ActivityLog.Action.LOGIN,         6),
    (ActivityLog.Action.LOGIN_FAILED,  2),
    (ActivityLog.Action.LOGOUT,        4),
    (ActivityLog.Action.SIGNUP,        1),
    (ActivityLog.Action.ADD_TO_CART,   8),
    (ActivityLog.Action.CART_UPDATE,   4),
    (ActivityLog.Action.CHECKOUT,      2),
    (ActivityLog.Action.ORDER_PLACED,  2),
    (ActivityLog.Action.REVIEW,        1),
]
_ACTIONS, _WEIGHTS = zip(*ACTION_MIX)

UAS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.4 (Synthetic)',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4) Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (X11; Linux x86_64) Firefox/125.0',
]


class Command(BaseCommand):
    help = 'Generate synthetic ActivityLog rows for the dashboard.'

    def add_arguments(self, parser):
        parser.add_argument('--backfill', type=int, default=0,
                            help='Insert this many historical events (last 7 days) and exit unless --rate is also set.')
        parser.add_argument('--days', type=int, default=7,
                            help='How many days back the backfill should span (default 7).')
        parser.add_argument('--rate', type=float, default=0.0,
                            help='Events per second to stream after backfill (0 = no streaming).')
        parser.add_argument('--anon-ratio', type=float, default=0.35,
                            help='Fraction of events that are anonymous (no user). Default 0.35.')
        parser.add_argument('--max-users', type=int, default=50,
                            help='How many users to sample from the DB.')

    def handle(self, *args, **opts):
        backfill = max(0, opts['backfill'])
        rate = max(0.0, opts['rate'])
        anon_ratio = max(0.0, min(1.0, opts['anon_ratio']))

        users = list(
            User.objects.exclude(email='')
                .only('id', 'email', 'category')
                .order_by('?')[:opts['max_users']]
        )
        if not users:
            self.stdout.write(self.style.WARNING(
                'No users in DB — every row will be anonymous. '
                'Run `python manage.py seed_users` (or import_users) for richer data.'))

        if backfill:
            self._backfill(users, backfill, opts['days'], anon_ratio)

        if rate > 0:
            self._stream(users, rate, anon_ratio)
        elif not backfill:
            self.stdout.write(self.style.WARNING(
                'Nothing to do: pass --backfill N and/or --rate R.'))

    # ── modes ─────────────────────────────────────────────────────────────────

    def _backfill(self, users, count, days, anon_ratio):
        now = timezone.now()
        window = timedelta(days=days)
        rows = []
        for _ in range(count):
            offset = timedelta(seconds=random.uniform(0, window.total_seconds()))
            ts = now - offset
            rows.append(self._build_row(users, anon_ratio, timestamp=ts))
        ActivityLog.objects.bulk_create(rows, batch_size=500)
        self.stdout.write(self.style.SUCCESS(
            f'Backfilled {count} synthetic events across the last {days} days.'))

    def _stream(self, users, rate, anon_ratio):
        sleep_between = 1.0 / rate
        self.stdout.write(self.style.SUCCESS(
            f'Streaming synthetic events at ~{rate}/sec '
            f'({len(users)} users in pool, anon_ratio={anon_ratio:.0%}). Ctrl-C to stop.'))
        try:
            while True:
                row = self._build_row(users, anon_ratio)
                # Save individually so the dashboard updates in near-real-time.
                row.save()
                time.sleep(sleep_between)
        except KeyboardInterrupt:
            self.stdout.write('\nInterrupted, exiting.')

    # ── row builder ───────────────────────────────────────────────────────────

    def _build_row(self, users, anon_ratio, timestamp=None):
        is_anon = (not users) or random.random() < anon_ratio
        if is_anon:
            user = None
            user_category = ''
            path = random.choice(ANON_PATHS)
        else:
            user = random.choice(users)
            user_category = getattr(user, 'category', '') or ''
            paths = COMMON_AUTH_PATHS + CATEGORY_PATHS.get(user_category, [])
            path = random.choice(paths)

        action = random.choices(_ACTIONS, weights=_WEIGHTS, k=1)[0]
        # Most actions are GETs; mutating actions are POSTs.
        method = 'POST' if action in {
            ActivityLog.Action.LOGIN, ActivityLog.Action.LOGIN_FAILED,
            ActivityLog.Action.SIGNUP, ActivityLog.Action.ADD_TO_CART,
            ActivityLog.Action.CART_UPDATE, ActivityLog.Action.CHECKOUT,
            ActivityLog.Action.REVIEW,
        } else 'GET'
        status = 200 if action != ActivityLog.Action.LOGIN_FAILED else 200

        return ActivityLog(
            timestamp=timestamp or timezone.now(),
            user=user,
            user_category=user_category,
            session_key='',
            method=method,
            path=path,
            status_code=status,
            duration_ms=random.randint(8, 320),
            action=action,
            ip_address=f'10.0.{random.randint(0, 255)}.{random.randint(1, 254)}',
            user_agent=random.choice(UAS),
            is_synthetic=True,
        )
