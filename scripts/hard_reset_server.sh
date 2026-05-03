#!/bin/bash
# Usage:
# hard_reset_server.bat            # runs imports
# hard_reset_server.bat --noimport # skips imports
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete

# Remove containers and delete volumes
docker compose down -v

# Rebuild images
docker compose build

# Build import commands conditionally
if [[ "$1" == "--noimport" ]]; then
  IMPORT_CMDS=""
else
  IMPORT_CMDS="&& python manage.py import_users \
               && python manage.py import_products \
               && python manage.py import_orders"
fi


# Make migrations and create superuser
echo "Running migrations and creating superuser..."
docker compose run \
  -e DJANGO_SUPERUSER_USERNAME=root \
  -e DJANGO_SUPERUSER_EMAIL=root@example.com \
  -e DJANGO_SUPERUSER_PASSWORD=password123 \
  --rm web sh -c "python manage.py makemigrations && \
                  python manage.py migrate && \
                  python manage.py createsuperuser --noinput && \
                  python manage.py seed_users \
                  $IMPORT_CMDS"
                  

# Start the containers
docker compose up