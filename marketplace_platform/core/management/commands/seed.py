import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Product
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help="Import products using Panda"
    def add_arguments(self, parser):
        parser.add_argument("file",type=str)
    def handle(self, *args, **kwargs):
        file_path=kwargs["file"]
        df=pd.read_csv(file_path)
        producer=User.objects.filter(category="Producer")
        if not producer:
            self.stdout.write(self.style.ERROR("No producer found"))
            return
        if not producer:
            self.stdout.write(self.style.ERROR("No producer"))
            return
        for _,row in df.iterrows():
            try:
                if User.objects.filter(username=row["username"]).exists():
                    continue
                
                User.objects.create_user(
                    username=row["name"],
                    password=row["password_hash"],
                    email=row["email"],
                    category=row.get("category","Customer")
                )
            except Exception as e:
                print(f"Error with row {row.to_dict()}: {e}")