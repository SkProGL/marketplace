import csv
import random
from decimal import Decimal
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from core.models import Order, Product, User, OrderProduct, Payment
from core.module.location import get_coordinates, calculate_distance

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
            brfn_lat,brfn_lon=(51.503269,-2.602925)
            for row in reader:
                #CSV:product_ids,total_price,order_date,delivery_date,order_status,special_instructions,recurring,recurrence_type,recurrence_day
                #MOD:id,customers,products,total_price,order_date,delivery_date,order_status,special_instructions,recurring,recurrence_type,recurrence_day
                product_indexes=row["product_ids"].replace('"','').split(",")
                products_for_order=[product_index_map[int(idx.strip())] for idx in product_indexes]
                total_price = sum(p.price for p in products_for_order)
                customer_id=random.choice(customer_ids)
                customer=User.objects.get(id=customer_id)
                order_date=parse_datetime(row["order_date"])
                cus_lat,cus_lon=get_coordinates(customer.postcode)
                order=Order.objects.create(
                    customer_id=customer_id,
                    total_price=total_price,
                    order_date=order_date,
                    delivery_date=parse_datetime(row["delivery_date"]),
                    order_status=row["order_status"],
                    special_instructions=row["special_instructions"]
                )
                order_products=[]
                producer_totals={}
                for p in products_for_order:
                    producer=p.producer
                    prod_lat,prod_lon=get_coordinates(producer.postcode)
                    if None not in (cus_lat,cus_lon,prod_lat,prod_lon):
                        fm_p_to_b=calculate_distance(prod_lat,prod_lon,brfn_lat,brfn_lon)
                        fm_b_to_c=calculate_distance(brfn_lat,brfn_lon,cus_lat,cus_lon)
                        food_miles=fm_p_to_b + fm_b_to_c
                    else:
                        food_miles=0
                    order_products.append(OrderProduct(
                        order=order,
                        product=p,
                        numPurchased=1,
                        food_miles=food_miles,
                        product_price_at_purchase=p.price
                    ))
                if producer.id not in producer_totals:
                    producer_totals[producer.id]=Decimal("0.00")

                producer_totals[producer.id]+=p.price

                OrderProduct.objects.bulk_create(order_products)

                payments=[]
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
        print("All orders done.")