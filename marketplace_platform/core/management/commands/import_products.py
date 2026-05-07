import csv
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import Product, User

def to_decimal(value,default=0):
    return Decimal(value) if value not in ("",None) else Decimal(default)

#CSV:name,category,description,price,unit,availability,seasonStart,seasonEnd,best_before,food_miles,stock,stock_alert_threshold,allergens,organic,surplus,discount_percentage,discount_expiry,discount note,images,producer_id
#MODEL:id, producer, name, category, description, price, unit, availability, seasonStart, seasonEnd, best_before, food_miles, stock, stock_alert_threshold, allergens, organic, surplus, discount_percentage, discount_expiry, discount_note, image
class Command(BaseCommand):
    help="Import products from CSV"
    def handle(self, *args, **kwargs):
        with open("synthetic_data/products.csv",newline='',encoding="utf-8") as file:
            reader=csv.DictReader(file)
            products=[]
            producer_ids=list(User.objects.filter(category="Producer").values_list("id",flat=True))
            for row in reader:
                
                try:
                    name=row.get("name")

                    #MOD:name,category,description,price,unit,availability,seasonStart,seasonEnd,best_before,food_miles,stock,stock_alert_threshold,allergens,organic,surplus,discount_percentage,discount_expiry,discount_note,image,producer
                    #CSV:name,category,description,price,unit,availability,seasonStart,seasonEnd,best_before,food_miles,stock,stock_alert_threshold,allergens,organic,surplus,discount_percentage,discount_expiry,discount note,images,producer_id
                    products.append(Product(
                        producer_id=random.choice(producer_ids),
                        name=name,
                        category=row["category"].capitalize(),
                        description=row["description"],
                        price=Decimal(row["price"]),
                        unit=row["unit"],
                        availability=row["availability"].capitalize(),
                        seasonStart=row["seasonStart"].capitalize(),
                        seasonEnd=row["seasonEnd"].capitalize(),
                        best_before=row["best_before"],
                        stock=int(row["stock"]),
                        stock_alert_threshold=to_decimal(row["stock_alert_threshold"]),
                        allergens=[],
                        organic=row["organic"]=="True",
                        surplus=row["surplus"]=="True",
                        discount_percentage=to_decimal(row["discount_percentage"]),
                        image_url=row["images"]
                    ))
                    print(f"Created: {name}")
                except Exception as e:
                    print(f"Error with row {row}: {e}")
            Product.objects.bulk_create(products)
            print("done")