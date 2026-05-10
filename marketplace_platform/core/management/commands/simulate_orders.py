"""
Generate synthetic Order / OrderProduct / ProducerOrder / Payment rows
with deliberately-injected patterns so the analytics dashboard has
something meaningful to detect.

Patterns injected:
  * time-of-day peaks at lunch (12-13) and evening (18-20)
  * weekend bias (Sat/Sun ~1.5x weekday volume)
  * popular-product Pareto: ~10 items receive most of the demand
  * seasonal category trending (winter favours bakery/preserve,
    summer favours fruit/vegetable)

Synthetic orders are tagged via `special_instructions` starting with
"[SYN]" so they can be filtered or wiped without affecting real orders.

Usage:
    python manage.py simulate_orders                       # 3000 orders / 90 days
    python manage.py simulate_orders --count 1000 --days 60
    python manage.py simulate_orders --clear               # delete synthetic orders, then exit
    python manage.py simulate_orders --clear --count 500   # wipe + reseed
"""
import random
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    Order, OrderProduct, Payment, ProducerOrder, ProductBatch,
)

User = get_user_model()

SYN_TAG = "[SYN]"  # marker placed at start of special_instructions

# Hour-of-day weights — higher = more orders at that hour.
HOUR_WEIGHTS = [
    0.3, 0.2, 0.2, 0.2, 0.3, 0.4,  # 0-5  (overnight)
    0.6, 0.8, 1.0, 1.0, 1.2, 1.4,  # 6-11 (morning ramp)
    2.5, 2.2,                       # 12-13 LUNCH PEAK
    1.4, 1.2, 1.2, 1.3,             # 14-17 (afternoon)
    2.4, 2.5, 2.0,                  # 18-20 EVENING PEAK
    1.4, 1.0, 0.6,                  # 21-23 (wind down)
]

# Weekday → weight (Mon=0 ... Sun=6).
DAY_WEIGHTS = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.7, 6: 1.6}

# Category boost by month: month -> {category: weight} (defaults to 1.0).
SEASONAL_BOOST = {
    # Winter — bakery + preserves.
    12: {'Bakery': 2.0, 'Preserve': 1.6},
    1:  {'Bakery': 2.0, 'Preserve': 1.7},
    2:  {'Bakery': 1.8, 'Preserve': 1.5},
    # Spring — easing back to baseline.
    3:  {'Vegetable': 1.2, 'Dairy': 1.1},
    4:  {'Vegetable': 1.3, 'Fruit': 1.2},
    5:  {'Fruit': 1.4, 'Vegetable': 1.3},
    # Summer — fruit + veg dominate.
    6:  {'Fruit': 2.0, 'Vegetable': 1.6},
    7:  {'Fruit': 2.2, 'Vegetable': 1.6},
    8:  {'Fruit': 2.0, 'Vegetable': 1.4},
    # Autumn — drift back.
    9:  {'Vegetable': 1.3, 'Bakery': 1.2},
    10: {'Bakery': 1.4, 'Preserve': 1.2},
    11: {'Bakery': 1.6, 'Preserve': 1.4},
}

STATUS_MIX = [
    (Order.Status.DELIVERED, 70),
    (Order.Status.READY,     10),
    (Order.Status.CONFIRMED, 12),
    (Order.Status.PENDING,    5),
    (Order.Status.CANCELLED,  3),
]
_STATUSES, _STATUS_W = zip(*STATUS_MIX)


class Command(BaseCommand):
    help = "Generate synthetic orders with injected time/popularity/seasonal patterns."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=3000,
                            help='Number of orders to generate (default 3000).')
        parser.add_argument('--days', type=int, default=90,
                            help='Spread orders across the last N days (default 90).')
        parser.add_argument('--popular-count', type=int, default=10,
                            help='How many products are pre-designated "popular" (default 10).')
        parser.add_argument('--popular-share', type=float, default=0.55,
                            help='Probability a given pick comes from the popular pool (default 0.55).')
        parser.add_argument('--clear', action='store_true',
                            help='Delete existing synthetic orders before generating. Use alone to wipe only.')

    def handle(self, *args, **opts):
        if opts['clear']:
            self._clear()
            if opts['count'] == 0:
                return

        customers = list(User.objects.filter(category='Customer'))
        batches = list(
            ProductBatch.objects.select_related('product', 'product__producer')
        )
        if not customers:
            self.stderr.write(self.style.ERROR(
                'No Customer users found. Run import_users / seed_users first.'))
            return
        if not batches:
            self.stderr.write(self.style.ERROR(
                'No ProductBatches found. Run import_products first.'))
            return

        # Designate the "popular" pool — these batches will appear in many orders.
        popular_n = min(opts['popular_count'], len(batches))
        popular = random.sample(batches, popular_n)
        popular_share = max(0.0, min(1.0, opts['popular_share']))

        # Group batches by category for the seasonal-boost picker.
        by_category = defaultdict(list)
        for b in batches:
            by_category[b.product.category].append(b)

        self.stdout.write(self.style.SUCCESS(
            f'Generating {opts["count"]} orders across the last {opts["days"]} days '
            f'({len(customers)} customers, {len(batches)} batches, '
            f'{popular_n} popular @ {popular_share:.0%})'))

        now = timezone.now()
        created = 0
        with transaction.atomic():
            for _ in range(opts['count']):
                self._make_order(
                    now=now, days=opts['days'],
                    customers=customers, batches=batches,
                    popular=popular, popular_share=popular_share,
                    by_category=by_category,
                )
                created += 1
                if created % 500 == 0:
                    self.stdout.write(f'  …{created} orders inserted')

        self.stdout.write(self.style.SUCCESS(f'Done — {created} synthetic orders created.'))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _clear(self):
        """Delete only orders we created (tagged via special_instructions)."""
        qs = Order.objects.filter(special_instructions__startswith=SYN_TAG)
        n = qs.count()
        qs.delete()
        self.stdout.write(self.style.WARNING(f'Cleared {n} synthetic orders.'))

    def _random_timestamp(self, now, days):
        # Pick a day with weekend bias.
        day_offsets = list(range(days))
        weights = [DAY_WEIGHTS[(now - timedelta(days=d)).weekday()] for d in day_offsets]
        day_offset = random.choices(day_offsets, weights=weights)[0]
        base_date = (now - timedelta(days=day_offset)).date()
        # Pick an hour with peak bias.
        hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        naive = datetime.combine(base_date, time(hour, minute, second))
        return timezone.make_aware(naive)

    def _pick_batch(self, popular, batches, popular_share, by_category, month):
        """Pick a batch with popularity + seasonal weighting."""
        if random.random() < popular_share:
            return random.choice(popular)
        # Apply seasonal category boost.
        boosts = SEASONAL_BOOST.get(month, {})
        if boosts and random.random() < 0.6:
            # Build a weighted list of categories present in the catalogue.
            cats = list(by_category.keys())
            cat_weights = [boosts.get(c, 1.0) for c in cats]
            chosen_cat = random.choices(cats, weights=cat_weights)[0]
            return random.choice(by_category[chosen_cat])
        return random.choice(batches)

    def _make_order(self, *, now, days, customers, batches,
                    popular, popular_share, by_category):
        order_dt = self._random_timestamp(now, days)
        delivery_dt = order_dt + timedelta(hours=random.choice([12, 18, 24, 36, 48]))

        n_items = random.choices([1, 2, 3, 4, 5, 6, 7, 8],
                                 weights=[8, 14, 18, 18, 16, 12, 8, 6])[0]
        picks = [
            self._pick_batch(popular, batches, popular_share, by_category, order_dt.month)
            for _ in range(n_items)
        ]

        # Aggregate duplicate picks → quantity per batch.
        qty_by_batch = defaultdict(int)
        for b in picks:
            qty_by_batch[b] += 1

        line_total = sum(b.price * qty for b, qty in qty_by_batch.items())
        status = random.choices(_STATUSES, weights=_STATUS_W)[0]
        customer = random.choice(customers)

        order = Order.objects.create(
            customer=customer,
            total_price=line_total.quantize(Decimal('0.01')),
            order_date=order_dt,
            delivery_date=delivery_dt,
            order_status=status,
            special_instructions=f"{SYN_TAG} synthetic test order",
            food_miles=round(random.uniform(2.0, 80.0), 2),
            delivery_address=customer.address or '',
            delivery_postcode=customer.postcode or '',
        )

        # Group lines by producer so we can build ProducerOrders.
        by_producer = defaultdict(list)
        for batch, qty in qty_by_batch.items():
            by_producer[batch.product.producer].append((batch, qty))

        for producer, lines in by_producer.items():
            po = ProducerOrder(order=order, producer=producer, order_status=status,
                               delivery_date=delivery_dt)
            # Skip the auto-syncing save() override to avoid recomputing
            # status from sibling rows that don't exist yet.
            super(ProducerOrder, po).save()

            OrderProduct.objects.bulk_create([
                OrderProduct(order=order, producer_order=po, batch=batch,
                             numPurchased=qty, price_at_purchase=batch.price)
                for batch, qty in lines
            ])

            producer_total = sum(b.price * q for b, q in lines)
            Payment.objects.create(
                producer=producer,
                order=order,
                amount=producer_total.quantize(Decimal('0.01')),
                status=Payment.Status.PROCESSED if status == Order.Status.DELIVERED
                       else Payment.Status.PENDING,
                created_at=order_dt,
                processed_at=order_dt + timedelta(hours=1)
                             if status == Order.Status.DELIVERED else None,
            )

        # Final sync now that all ProducerOrders are in place.
        order.sync_status()
