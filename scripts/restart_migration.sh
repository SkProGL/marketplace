#!/bin/bash

# hard reset
# docker compose down -v
# docker compose up -d --build
docker compose up 
find "$(dirname "$0")/../marketplace_platform" -path "*/migrations/*.py" ! -name "__init__.py" -delete

docker exec django_app python manage.py makemigrations
docker exec django_app python manage.py migrate
