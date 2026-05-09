import csv
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import Product, ProductBatch, User

def to_decimal(value, default=0):
    return Decimal(value) if value not in ("", None) else Decimal(default)


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

                    # Clear old batches so re-imports don't stack
                    product.batches.all().delete()

                    is_surplus = row["surplus"] == "True"
                    ProductBatch.objects.create(
                        product=product,
                        quality_class=row["quality_class"],
                        stock=int(row["stock"]),
                        availability=row["availability"].title(),
                        seasonStart=row["seasonStart"].capitalize(),
                        seasonEnd=row["seasonEnd"].capitalize(),
                        best_before=row["best_before"],
                        surplus=is_surplus,
                        discount_percentage=to_decimal(row["discount_percentage"]),
                        image=f"item_images/{row['img_path']}",
                    )

                    print(f"Batches created for: {name}")
                except Exception as e:
                    print(f"Error with row {row}: {e}")
        print("done")
