from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import ProductBatch

SURPLUS_DAYS = {
    'Fruit':     5,
    'Vegetable': 5,
    'Preserve':  5,
    'Dairy':     3,
    'Bakery':    3,
}
DEFAULT_DAYS = 5


class Command(BaseCommand):
    help = 'Auto-mark batches as Discounted when they enter their surplus window.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        candidates = (
            ProductBatch.objects
            .select_related('product')
            .filter(stock__gt=0)
            .exclude(quality_class='Discounted')
        )

        updated = 0
        for batch in candidates:
            days = SURPLUS_DAYS.get(batch.product.category, DEFAULT_DAYS)
            if batch.best_before <= today + timedelta(days=days):
                batch.quality_class = 'Discounted'
                batch.surplus = True
                batch.discount_percentage = batch.surplus_discount_percentage
                batch.save(update_fields=['quality_class', 'surplus', 'discount_percentage'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f'auto_surplus: {updated} batch(es) marked as Discounted.'))
