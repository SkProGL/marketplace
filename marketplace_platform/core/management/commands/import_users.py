import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()
# CSV: id,category,email,phone,address,postcode,password_hash,first_name,last_name
# MODEL: username,first_name,last_name,password,email,phone,address,postcode,category,organisation_name


class Command(BaseCommand):
    help = "Import users from CSV"

    def handle(self, *args, **kwargs):
        with open("synthetic_data/users.csv", newline='', encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    name = row.get("name")
                    category_map = {
                        "customer": "Customer",
                        "producer": "Producer",
                        "restaurant": "Restaurant",
                        "community group": "Community Group"
                    }
                    raw_category=row.get("category","").lower()
                    category=category_map.get(raw_category,"Customer")

    
                    if User.objects.filter(full_name=name).first():
                        continue

                    user = User.objects.create_user(
                        password=row.get("password_hash"),
                        full_name=row.get("name"),
                        email=row.get("email", ""),
                        category=category,
                        phone=row.get("phone", ""),
                        address=row.get("address", ""),
                        postcode=row.get("postcode", ""),
                        organisation_name=row.get("organisation_name", "")
                    )
<<<<<<< Updated upstream
                    # print(f"Created: {name}")
=======
                    print(f"Created: {name}")
>>>>>>> Stashed changes
                except Exception as e:
                    print(f"Error with row {row}: {e}")
            print("done")

