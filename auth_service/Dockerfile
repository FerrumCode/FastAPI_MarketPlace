FROM python:3.13.5-bookworm

WORKDIR /auth_service

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

# CMD ["sh", "-c", "alembic upgrade head && python -m app.models.seed && uvicorn app.main:app --host 0.0.0.0 --port 3000"]

CMD ["python", "app/main.py"]