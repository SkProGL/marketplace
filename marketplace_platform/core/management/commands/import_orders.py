import csv
import random
from decimal import Decimal
from django.utils import timezone
from datetime import datetime
from django.core.management.base import BaseCommand
from core.models import Order, ProductBatch, User, OrderProduct

def to_decimal(value, default=0):
    return Decimal(value) if value not in ("", None) else Decimal(default)

def parse_datetime(s):
    naive = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return timezone.make_aware(naive)

class Command(BaseCommand):
    help = "Import orders from CSV"

    def handle(self, *args, **kwargs):
        all_batches = list(ProductBatch.objects.select_related('product').order_by('product__id', 'created_at'))
        batch_index_map = {i + 1: b for i, b in enumerate(all_batches)}

        with open("synthetic_data/orders.csv", newline='', encoding="utf-8") as file:
            reader = csv.DictReader(file)
            customer_ids = list(User.objects.filter(category="Customer").values_list("id", flat=True))
            for row in reader:
                try:
                    indexes = row["product_ids"].replace('"', '').split(",")
                    batches_for_order = [batch_index_map[int(idx.strip())] for idx in indexes]
                    total_price = sum(b.price for b in batches_for_order)

                    order = Order.objects.create(
                        customer_id=random.choice(customer_ids),
                        total_price=total_price,
                        order_date=parse_datetime(row["order_date"]),
                        delivery_date=parse_datetime(row["delivery_date"]),
                        order_status=row["order_status"],
                        special_instructions=row["special_instructions"]
                    )

                    order_products = [
                        OrderProduct(
                            order=order,
                            batch=b,
                            numPurchased=1,
                            product_price_at_purchase=b.price,
                            price_at_purchase=b.price,
                        )
                        for b in batches_for_order
                    ]
                    OrderProduct.objects.bulk_create(order_products, ignore_conflicts=True)
                except Exception as e:
                    print(f"Error with row {row}: {e}")
        print("All orders done.")
