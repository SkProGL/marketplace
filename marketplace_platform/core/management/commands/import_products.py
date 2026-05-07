import csv
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import Product, ProductBatch, User

def to_decimal(value, default=0):
    return Decimal(value) if value not in ("", None) else Decimal(default)

#CSV:name,category,description,price,unit,availability,seasonStart,seasonEnd,best_before,food_miles,stock,stock_alert_threshold,allergens,organic,surplus,discount_percentage,discount_expiry,discount note,images,producer_id
class Command(BaseCommand):
    help = "Import products and producer batches from CSV"

    def handle(self, *args, **kwargs):
        with open("synthetic_data/products.csv", newline='', encoding="utf-8") as file:
            reader = csv.DictReader(file)
            producer_ids = list(User.objects.filter(category="Producer").values_list("id", flat=True))
            for row in reader:
                try:
                    name = row.get("name")
                    producer_id = random.choice(producer_ids)
                    print("RAW IMAGE FIELD")
                    print("images:",row.get("images"))
                    print("images:",row.get("img_path"))
                    # One Product per unique name; price is the Class A base price
                    product, _ = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'producer_id': producer_id,
                            'category': row["category"].capitalize(),
                            'description': row["description"],
                            'price': Decimal(row["price"]),
                            'unit': row["unit"],
                            'stock_alert_threshold': int(row["stock_alert_threshold"] or 0),
                            'allergens': [],
                            'organic': row["organic"] == "True",
                            "image": f"item_images/{row['img_path']}",
                            "image_url": row["images"],
                        }
                    )
                    print("SAVED PRODUCT IMAGE FIELDS:")
                    print("image:", product.image)
                    print("image name:", product.image.name if product.image else None)
                    print("image url:", getattr(product.image, "url", None))
                    print("image_url:", product.image_url)
                    # Each CSV row creates a Class A batch (price derived from product)
                    ProductBatch.objects.create(
                        product=product,
                        quality_class='A',
                        stock=int(row["stock"]),
                        availability=row["availability"].capitalize(),
                        seasonStart=row["seasonStart"].capitalize(),
                        seasonEnd=row["seasonEnd"].capitalize(),
                        best_before=row["best_before"],
                        surplus=row["surplus"] == "True",
                        discount_percentage=to_decimal(row["discount_percentage"]),
                        image=f"item_images/{row['img_path']}"
                    )
                    print(f"Batch created for: {name}")
                except Exception as e:
                    print(f"Error with row {row}: {e}")
        print("done")
