FROM python:3.11-slim

# prevents python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# ensures stdout/stderr are flushed immediately
ENV PYTHONUNBUFFERED=1

# install system dependencies
RUN apt-get update && apt-get install -y \
    curl

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# set working directory
WORKDIR /app

# old
# # copy python requirements to container
# COPY marketplace_platform/requirements.txt .
#
# # install dependencies using system python (without virtual environments)
# RUN uv pip install -r requirements.txt --system

ARG REQUIREMENTS_FILE=requirements.txt
COPY marketplace_platform/${REQUIREMENTS_FILE} .
RUN uv pip install -r ${REQUIREMENTS_FILE} --system

# now copy all files
COPY marketplace_platform/ .

# expose django port
EXPOSE 8000

# default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
