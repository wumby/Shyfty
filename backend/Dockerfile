FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8001

CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8001} --workers ${WEB_CONCURRENCY:-2} --access-logfile - --error-logfile -"]
