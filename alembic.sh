#!/bin/sh
    
echo "⏳ Waiting for database..."

# wait until postgres is ready
while ! nc -z db 5432; do
  sleep 1
done

echo "✅ Database is ready"

echo "🚀 Running Alembic migrations..."
alembic upgrade head

echo "🎯 Starting FastAPI app..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000