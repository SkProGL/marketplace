#!/bin/bash

# Delete all old migrations
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Remove containers and delete volumes
docker compose down -v

# Rebuild images
docker compose build

# Make migrations and create superuser
echo "Running migrations and creating superuser..."
docker compose run \
  -e DJANGO_SUPERUSER_USERNAME=root \
  -e DJANGO_SUPERUSER_EMAIL=root@example.com \
  -e DJANGO_SUPERUSER_PASSWORD=password123 \
  --rm web sh -c "python manage.py makemigrations && \
                  python manage.py migrate && \
                  python manage.py createsuperuser --noinput && \
                  python manage.py seed_users"

# Start the containers
docker compose up