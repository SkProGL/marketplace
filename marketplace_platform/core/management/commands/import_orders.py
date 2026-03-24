import csv
import random
from decimal import Decimal
from django.utils import timezone
from datetime import datetime
from django.core.management.base import BaseCommand
from core.models import Order, Product, User, OrderProduct

def to_decimal(value,default=0):
    return Decimal(value) if value not in ("",None) else Decimal(default)

def parse_datetime(str):
    naive=datetime.strptime(str,"%Y-%m-%d %H:%M:%S")
    return timezone.make_aware(naive)

class Command(BaseCommand):
    help="Import orders and order-product relationships from CSV"
    def handle(self, *args, **kwargs):
        all_products=list(Product.objects.order_by("id"))
        product_index_map={i+1: p for i, p in enumerate(all_products)}
        with open("synthetic_data/orders.csv",newline='',encoding="utf-8") as file:
            reader=csv.DictReader(file)
            customer_ids=list(User.objects.filter(category="Customer").values_list("id",flat=True))
            for row in reader:
                #CSV:product_ids,total_price,order_date,delivery_date,order_status,special_instructions,recurring,recurrence_type,recurrence_day
                #MOD:id,customers,products,total_price,order_date,delivery_date,order_status,special_instructions,recurring,recurrence_type,recurrence_day
                product_indexes=row["product_ids"].replace('"','').split(",")
                products_for_order=[product_index_map[int(idx.strip())] for idx in product_indexes]
                total_price = sum(p.price for p in products_for_order)

                order=Order.objects.create(
                    customer_id=random.choice(customer_ids),
                    total_price=total_price,
                    order_date=parse_datetime(row["order_date"]),
                    delivery_date=parse_datetime(row["delivery_date"]),
                    order_status=row["order_status"],
                    special_instructions=row["special_instructions"]
                )

                order_products=[]
                for p in products_for_order:
                    order_products.append(OrderProduct(
                        order=order,
                        product=p,
                        numPurchased=1,
                        product_price_at_purchase=p.price
                    ))
                OrderProduct.objects.bulk_create(order_products)
        print("All orders done.")