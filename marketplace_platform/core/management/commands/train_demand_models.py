"""
Trigger the ai-service to (re)train per-product demand-forecast models.

Pulls order history out of the Django DB, groups it per product per day,
and ships the full series in the POST body. The ai-service stays DB-free.

Usage:
    python manage.py train_demand_models                # default 180 days history
    python manage.py train_demand_models --days 90      # shorter window
    python manage.py train_demand_models --url http://ai-service:8000
"""
import os
from collections import defaultdict
from datetime import timedelta

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import OrderProduct, Product


DEFAULT_URL = os.environ.get("AI_SERVICE_URL", "http://ai-service:8000")


def _build_history(days_back):
    """Return [{'id', 'name', 'history': [{'date', 'units'}]}, ...] over the last N days."""
    cutoff = timezone.now() - timedelta(days=days_back)
    rows = (OrderProduct.objects
            .filter(order__order_date__gte=cutoff)
            .values_list('batch__product_id', 'order__order_date', 'numPurchased'))

    # product_id -> {date_str: units}
    bucket = defaultdict(lambda: defaultdict(float))
    for product_id, order_date, units in rows:
        bucket[str(product_id)][order_date.date().isoformat()] += float(units)

    products = []
    for p in Product.objects.all().order_by('name'):
        series = bucket.get(str(p.id), {})
        history = [{'date': d, 'units': u} for d, u in sorted(series.items())]
        products.append({
            'id': str(p.id),
            'name': p.name,
            'history': history,
        })
    return products


class Command(BaseCommand):
    help = "Tell ai-service to train demand-forecast models for every product."

    def add_arguments(self, parser):
        parser.add_argument('--url', default=DEFAULT_URL,
                            help=f'ai-service base URL (default {DEFAULT_URL}).')
        parser.add_argument('--days', type=int, default=180,
                            help='Days of order history to train on (default 180).')

    def handle(self, *args, **opts):
        url = opts['url'].rstrip('/') + '/forecast/train'
        days = opts['days']
        products = _build_history(days)
        total_rows = sum(len(p['history']) for p in products)
        self.stdout.write(
            f'POST {url}  ({len(products)} products, {total_rows} daily rows, days_back={days})')

        try:
            r = requests.post(url, json={"days_back": days, "products": products}, timeout=600)
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Request failed: {e}'))
            return

        if r.status_code != 200:
            self.stderr.write(self.style.ERROR(
                f'Training failed ({r.status_code}): {r.text[:500]}'))
            return

        data = r.json()
        self.stdout.write(self.style.SUCCESS(
            f'Trained {data["trained_count"]} models, skipped {data["skipped_count"]}.'))

        for s in data.get("trained", [])[:10]:
            self.stdout.write(
                f'  ✓ {s["name"]:<35} rows={s["training_rows"]:>4} '
                f'in-sample MAE={s["in_sample_mae"]:.2f}')
        if len(data.get("trained", [])) > 10:
            self.stdout.write(f'  …and {len(data["trained"]) - 10} more.')

        for s in data.get("skipped", [])[:10]:
            self.stdout.write(self.style.WARNING(
                f'  ✗ {s["name"]:<35} {s["reason"]}'))
