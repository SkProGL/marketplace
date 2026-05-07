:: Usage:
:: hard_reset_server.bat            # runs imports
:: hard_reset_server.bat --noimport # skips imports
@echo off
for /r %%i in (migrations\*.py) do (
    if not "%%~nxi"=="__init__.py" del "%%i"
)

:: Remove containers and delete volumes
docker compose down -v

:: Rebuild images
docker compose build

:: Build import commands conditionally
set IMPORT_CMDS=^&^& python manage.py import_users ^&^& python manage.py import_products ^&^& python manage.py import_orders
if "%1"=="--noimport" set IMPORT_CMDS=

:: Create superuser and make migrations
docker compose run ^
  -e DJANGO_SUPERUSER_USERNAME=root ^
  -e DJANGO_SUPERUSER_EMAIL=root@example.com ^
  -e DJANGO_SUPERUSER_PASSWORD=Password123 ^
  --rm web sh -c "python manage.py makemigrations && python manage.py migrate && python manage.py createsuperuser --noinput && python manage.py seed_users %IMPORT_CMDS%"

:: Start the containers
docker compose up
