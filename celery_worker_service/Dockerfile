FROM python:3.13.5-bookworm

WORKDIR /app

RUN pip install --upgrade pip wheel "poetry==2.1.4"
RUN poetry config virtualenvs.create false

# Копируем только файлы зависимостей
COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-root --no-interaction

COPY . .

# По-умолчанию оставим команду для воркера, но в docker-compose у нас
# отдельные команды для worker/beat/bridge.
CMD ["celery", "-A", "app.celery_app:celery_app", "worker", "--loglevel=INFO", "--pool=solo", "-Q", "default", "-n", "worker@%h"]
