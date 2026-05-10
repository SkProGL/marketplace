:: Usage:
:: hard_reset_server.bat            # runs imports
:: hard_reset_server.bat --noimport # skips imports
@echo off

for /r %%i in (migrations\*.py) do (
    if not "%%~nxi"=="__init__.py" del "%%i"
)
for /r %%i in (migrations\*.pyc) do del "%%i"

docker compose down -v
docker compose build

echo Running migrations and creating superuser...

if "%1"=="--noimport" (
  docker compose run ^
    -e DJANGO_SUPERUSER_USERNAME=root ^
    -e DJANGO_SUPERUSER_EMAIL=root@example.com ^
    -e DJANGO_SUPERUSER_PASSWORD=Password123 ^
    --rm web sh -c "python manage.py makemigrations && python manage.py migrate && python manage.py createsuperuser --noinput && python manage.py seed_users"
) else (
  docker compose run ^
    -e DJANGO_SUPERUSER_USERNAME=root ^
    -e DJANGO_SUPERUSER_EMAIL=root@example.com ^
    -e DJANGO_SUPERUSER_PASSWORD=Password123 ^
    --rm web sh -c "python manage.py makemigrations && python manage.py migrate && python manage.py createsuperuser --noinput && python manage.py import_users && python manage.py import_products && python manage.py import_orders && python manage.py seed_users"
)

docker compose up

