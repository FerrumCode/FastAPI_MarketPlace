FROM python:3.13.5-bookworm

WORKDIR /app

RUN mkdir -p /tmp/celery_prometheus_multiproc

RUN pip install --upgrade pip wheel "poetry==2.1.4"
RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --no-interaction

COPY . .

CMD ["celery", "-A", "app.celery_app:celery_app", "worker", "-B", "-l", "info"]
