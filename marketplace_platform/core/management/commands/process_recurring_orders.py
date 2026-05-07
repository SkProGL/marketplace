# Cron: 0 6 * * * cd /app && python manage.py process_recurring_orders
from collections import defaultdict
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.models import Order, OrderProduct, OrderStatusHistory, ProductBatch, ProducerOrder
from core.utils import get_next_occurrence


class Command(BaseCommand):
    
    help = "Place new orders for recurring orders due today."

    # docker exec -it django_app python manage.py process_recurring_orders --force
    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help="Process all active recurring orders regardless of their due date (demo / testing)."
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        due = (
            Order.objects
            .exclude(recurrence_type='None')
            .exclude(paused=True)
            .prefetch_related('orderproduct_set__batch__product__producer')
            .select_related('customer')
        )
        for template in due:
            if template.last_generated == today and not options['force']:
                self.stdout.write(f"Skipping {str(template.id)[:8]}: already processed today.")
                continue
            if options['force'] or get_next_occurrence(template) == today:
                self._fulfil(template, today)

    def _fulfil(self, template, today):
        items = list(template.orderproduct_set.select_related('batch__product__producer').all())

        with transaction.atomic():
            locked = {
                str(b.pk): b
                for b in ProductBatch.objects.select_for_update().filter(
                    pk__in=[str(i.batch_id) for i in items]
                )
            }

            fulfillable, skipped_by_producer = [], defaultdict(list)
            for item in items:
                batch = locked[str(item.batch_id)]
                if batch.stock >= item.numPurchased:
                    fulfillable.append((batch, item.numPurchased))
                else:
                    skipped_by_producer[batch.product.producer].append(
                        f"{batch.product.name} (wanted {item.numPurchased}, stock: {batch.stock})"
                    )

            if not fulfillable:
                self.stderr.write(self.style.ERROR(
                    f"Recurring order {str(template.id)[:8]} for {template.customer.email}: "
                    f"all items out of stock — no order created."
                ))
                # Still notify each affected producer via their existing orders' ProducerOrders
                for producer, skipped_names in skipped_by_producer.items():
                    existing_po = (ProducerOrder.objects
                                   .filter(producer=producer, order__customer=template.customer)
                                   .order_by('-order__order_date')
                                   .first())
                    if existing_po:
                        OrderStatusHistory.objects.create(
                            producer_order=existing_po,
                            from_status=existing_po.order_status,
                            to_status=existing_po.order_status,
                            changed_by=None,
                            note=(
                                f"Recurring order could not be auto-placed — all items out of stock: "
                                f"{'; '.join(skipped_names)}."
                            ),
                        )
                return

            delivery_dt = timezone.make_aware(
                datetime.combine(today + timedelta(days=2), datetime.min.time())
            )
            new_order = Order.objects.create(
                customer=template.customer,
                total_price=round(sum(b.price * qty for b, qty in fulfillable), 2),
                delivery_date=delivery_dt,
                delivery_address=template.delivery_address,
                delivery_postcode=template.delivery_postcode,
                special_instructions=template.special_instructions,
                order_status='PENDING',
                recurrence_type='None',
            )

            # Create one ProducerOrder per producer, with a note if they had skipped items
            by_producer = defaultdict(list)
            for batch, qty in fulfillable:
                by_producer[batch.product.producer].append((batch, qty))

            all_producers = set(by_producer) | set(skipped_by_producer)
            for producer in all_producers:
                po = ProducerOrder.objects.create(
                    order=new_order,
                    producer=producer,
                    order_status='PENDING',
                    delivery_date=delivery_dt,
                )
                for batch, qty in by_producer.get(producer, []):
                    OrderProduct.objects.create(
                        order=new_order,
                        producer_order=po,
                        batch=batch,
                        numPurchased=qty,
                        price_at_purchase=batch.price,
                    )
                    ProductBatch.objects.filter(pk=batch.pk).update(stock=F('stock') - qty)

                # Notify producer of out-of-stock items they couldn't fulfil
                if producer in skipped_by_producer:
                    skipped_str = "; ".join(skipped_by_producer[producer])
                    OrderStatusHistory.objects.create(
                        producer_order=po,
                        from_status='PENDING',
                        to_status='PENDING',
                        changed_by=None,
                        note=(
                            f"Recurring order auto-placed. The following items had insufficient "
                            f"stock and were not included: {skipped_str}."
                        ),
                    )

        template.last_generated = today
        template.save(update_fields=['last_generated'])

        all_skipped = [s for names in skipped_by_producer.values() for s in names]
        self.stdout.write(
            f"Order {str(new_order.id)[:8]} for {template.customer.email}"
            + (f" — skipped: {', '.join(all_skipped)}" if all_skipped else "")
        )
