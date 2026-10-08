# Build from repo root:  docker build -f backend/Dockerfile .
FROM python:3.11-slim
WORKDIR /srv
ENV PYTHONPATH=/srv PYTHONUNBUFFERED=1
COPY ml/requirements.txt ml/requirements.txt
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY ml ml
COPY backend backend
WORKDIR /srv/backend
ENV AUTO_CREATE_TABLES=0
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
