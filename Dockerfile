FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

ENV DATABASE_URL=postgresql+psycopg2://inventory:inventory@db:5432/inventory

EXPOSE 8000

CMD ["sh", "-c", "python -m scripts.init_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
