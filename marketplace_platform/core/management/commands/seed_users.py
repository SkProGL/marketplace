# DEV - seed different user types on command for testing
# python manage.py seed_users
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

SEED_USERS = [
    {'email': 'producer@example.com',   'category': 'Producer'},
    {'email': 'restaurant@example.com', 'category': 'Restaurant'},
    {'email': 'community@example.com',  'category': 'Community group'},
    {'email': 'customer@example.com',   'category': 'Customer'},
]

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for users in SEED_USERS:
            user, created = User.objects.get_or_create(email=users['email'], defaults={'category': users['category']})
            user.set_password('Password123')
            user.save()
            self.stdout.write(f"[core/management/commands/seed_users.py] Created: {users['email']}")