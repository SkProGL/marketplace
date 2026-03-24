@echo off
for /r %%i in (migrations\*.py) do (
    if not "%%~nxi"=="__init__.py" del "%%i"
)

@REM Remove containers and delete volumes
docker compose down -v

@REM Rebuild images
docker compose build

@REM Create superuser and make migrations
docker compose run ^
  -e DJANGO_SUPERUSER_USERNAME=root ^
  -e DJANGO_SUPERUSER_EMAIL=root@example.com ^
  -e DJANGO_SUPERUSER_PASSWORD=password123 ^
  --rm web sh -c "python manage.py makemigrations && python manage.py migrate && python manage.py createsuperuser --noinput && python manage.py seed_users"

@REM Start the containers
docker compose up
