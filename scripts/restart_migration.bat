@echo off

REM hard reset
REM docker compose down -v
REM docker compose up -d --build

for /r %%i in (migrations\*.py) do (
    if not "%%~nxi"=="__init__.py" del "%%i"
)

docker compoose up
docker exec django_app python manage.py makemigrations
docker exec django_app python manage.py migrate
