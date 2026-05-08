import csv
import random
from decimal import Decimal
from collections import defaultdict
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand

from core.models import Order, ProductBatch, User, OrderProduct, Payment
from core.utils import (
    get_coordinates,
    calculate_distance,
    BRFN_LAT,
    BRFN_LON,
)


def to_decimal(value, default=0):
    return Decimal(value) if value not in ("", None) else Decimal(default)


def parse_datetime(s):
    naive = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return timezone.make_aware(naive)


class Command(BaseCommand):
    help = "Import orders from CSV"

    def handle(self, *args, **kwargs):

        all_batches = list(
            ProductBatch.objects.select_related("product")
            .order_by("product__id", "created_at")
        )
        batch_index_map = {i + 1: b for i, b in enumerate(all_batches)}

        customers = {
            u.id: u for u in User.objects.filter(category="Customer")
        }
        customer_ids = list(customers.keys())

        postcode_cache = {}

        def get_cached_coords(pc):
            if pc not in postcode_cache:
                postcode_cache[pc] = get_coordinates(pc)
            return postcode_cache[pc]
        with open("synthetic_data/orders.csv", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            brfn_lat, brfn_lon = (51.503269, -2.602925)
            limit = 20
            # for row in reader:
            for (i, row) in enumerate(reader):
                # if i>=limit:
                #     break
                try:
                    indexes = row["product_ids"].replace('"', "").split(",")
                    batches_for_order = [
                        batch_index_map[int(i.strip())]
                        for i in indexes
                    ]

                    total_price = sum(b.price for b in batches_for_order)

                    customer = customers[random.choice(customer_ids)]
                    cus_lat, cus_lon = get_cached_coords(customer.postcode)

                    order_date = parse_datetime(row["order_date"])
                    total_food_miles = 0
                    producer_totals = defaultdict(Decimal)
                    producer_distance_cache = {}
                    producer_batches = defaultdict(list)

                    for batch in batches_for_order:
                        producer_batches[batch.product.producer].append(batch)

                    for producer, batches in producer_batches.items():

                        producer_totals[producer.id] += sum(
                            b.price for b in batches
                        )

                        if producer.id not in producer_distance_cache:
                            prod_lat, prod_lon = get_cached_coords(
                                producer.postcode
                            )
                            producer_distance_cache[producer.id] = calculate_distance(
                                prod_lat,
                                prod_lon,
                                BRFN_LAT,
                                BRFN_LON,
                            )

                        to_hub = producer_distance_cache[producer.id]

                        from_hub_to_customer = calculate_distance(
                            BRFN_LAT,
                            BRFN_LON,
                            cus_lat,
                            cus_lon,
                        )
                        total_food_miles += (
                            to_hub + from_hub_to_customer
                        ) * len(batches)
                    order = Order.objects.create(
                        customer_id=customer.id,
                        total_price=total_price,
                        order_date=order_date,
                        delivery_date=parse_datetime(row["delivery_date"]),
                        order_status=row["order_status"],
                        special_instructions=row["special_instructions"],
                        food_miles=round(total_food_miles, 2),
                    )
                    order_products = [
                        OrderProduct(
                            order=order,
                            batch=b,
                            numPurchased=1,
                            price_at_purchase=b.price,
                        )
                        for b in batches_for_order
                    ]

                    OrderProduct.objects.bulk_create(
                        order_products,
                        ignore_conflicts=True
                    )

                    payments = [
                        Payment(
                            producer_id=producer_id,
                            order=order,
                            amount=amount,
                            status=Payment.Status.PROCESSED,
                            created_at=order_date,
                            processed_at=order_date + timedelta(hours=1),
                        )
                        for producer_id, amount in producer_totals.items()
                    ]

                    Payment.objects.bulk_create(payments)

                    self.stdout.write(f"Created order {order.id}")

                except Exception as e:
                    self.stderr.write(f"Error with row {row}: {e}")

        self.stdout.write("All orders done.")

