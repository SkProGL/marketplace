import csv
import random
from decimal import Decimal
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from core.models import Order, ProductBatch, User, OrderProduct, Payment
from core.utils import get_coordinates, calculate_distance, BRFN_LAT, BRFN_LON


def to_decimal(value, default=0):
    return Decimal(value) if value not in ("", None) else Decimal(default)


def parse_datetime(s):
    naive = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return timezone.make_aware(naive)


class Command(BaseCommand):
    help = "Import orders from CSV"

    def handle(self, *args, **kwargs):
        all_batches = list(ProductBatch.objects.select_related(
            'product').order_by('product__id', 'created_at'))
        batch_index_map = {i + 1: b for i, b in enumerate(all_batches)}
        customers = {
            u.id: u
            for u in User.objects.filter(category="Customer")
        }

        customer_ids = list(customers.keys())
        postcode_cache = {}

        def get_cached_coords(pc):
            if pc not in postcode_cache:
                postcode_cache[pc] = get_coordinates(pc)
            return postcode_cache[pc]

        with open("synthetic_data/orders.csv", newline='', encoding="utf-8") as file:
            reader = csv.DictReader(file)
<<<<<<< Updated upstream
            limit = 20

            brfn_lat, brfn_lon = (51.503269, -2.602925)
            for (i, row) in enumerate(reader):
                if i>=limit:
                    break
=======
            for row in reader:
>>>>>>> Stashed changes
                try:
                    indexes = row["product_ids"].replace('"', '').split(",")
                    batches_for_order = [
                        batch_index_map[int(idx.strip())] for idx in indexes]
                    total_price = sum(b.price for b in batches_for_order)
                    customer_id = random.choice(customer_ids)
                    customer = customers[customer_id]
                    cus_lat, cus_lon = get_coordinates(customer.postcode)
                    order_date = parse_datetime(row["order_date"])
                    total_food_miles = 0

                    producer_totals = {}
                    for batch in batches_for_order:
                        producer = batch.product.producer
                        producer_totals.setdefault(
                            producer.id, Decimal("0.00"))
                        producer_totals[producer.id] += batch.price

<<<<<<< Updated upstream
                        producer_postcode = producer.postcode
                        prod_lat, prod_lon = get_cached_coords(
                            producer_postcode)

                        distance1 = calculate_distance(
                            prod_lat, prod_lon, brfn_lat, brfn_lon)
                        distance2 = calculate_distance(
                            brfn_lat, brfn_lon, cus_lat, cus_lon)
                        total_food_miles += (distance1+distance2)
=======
                        producer_postcode=producer.postcode
                        prod_lat, prod_lon = get_cached_coords(producer_postcode)
                        distance1 = calculate_distance(prod_lat,prod_lon,BRFN_LAT,BRFN_LON)
                        distance2 = calculate_distance(BRFN_LAT,BRFN_LON,cus_lat,cus_lon)
                        total_food_miles+=(distance1+distance2)
>>>>>>> Stashed changes

                    order = Order.objects.create(
                        customer_id=customer_id,
                        total_price=total_price,
                        order_date=order_date,
                        delivery_date=parse_datetime(row["delivery_date"]),
                        order_status=row["order_status"],
                        special_instructions=row["special_instructions"],
                        food_miles=round(total_food_miles, 2)
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
                        order_products, ignore_conflicts=True)

                    payments = []
                    for producer_id, amount in producer_totals.items():
                        payments.append(
                            Payment(
                                producer_id=producer_id,
                                order=order,
                                amount=amount,
                                status=Payment.Status.PROCESSED,
                                created_at=order_date,
                                processed_at=order_date+timedelta(hours=1)
                            )
                        )
                    Payment.objects.bulk_create(payments)
                    print(f"Created order {order.id}")

                except Exception as e:
                    print(f"Error with row {row}: {e}")
        print("All orders done.")
