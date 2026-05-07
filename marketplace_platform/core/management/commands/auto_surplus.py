from django.core.management.base import BaseCommand
from core.models import ProductBatch
from core.utils import apply_surplus_if_due


class Command(BaseCommand):
    help = 'Auto-mark batches as Discounted when they enter their surplus window.'

    def handle(self, *args, **kwargs):
        candidates = (
            ProductBatch.objects
            .select_related('product')
            .filter(stock__gt=0)
            .exclude(quality_class='Discounted')
        )
        updated = sum(1 for batch in candidates if apply_surplus_if_due(batch))
        self.stdout.write(self.style.SUCCESS(f'auto_surplus: {updated} batch(es) marked as Discounted.'))
