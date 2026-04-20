FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y netcat-openbsd
COPY . .
RUN chmod +x /app/alembic.sh
EXPOSE 8000
CMD ["/app/alembic.sh"]