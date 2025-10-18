FROM python:3.13.5-bookworm

WORKDIR /app

RUN pip install --upgrade pip wheel "poetry==2.1.4"
RUN poetry config virtualenvs.create false

# Копируем только файлы зависимостей
COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --no-interaction

COPY . .

# Запускаем сервис
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]