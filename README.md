# FastAPI Task Project

This project provides:

- FastAPI backend for auth and task CRUD
- PostgreSQL persistence via SQLAlchemy + Alembic
- Built-in Jinja dashboard
- Streamlit frontend at `streamlit_app.py` for a production-grade operator UI

## Features

- User registration and login
- JWT token authentication
- Task create, read, update, delete
- Status filter, sort, pagination, deadline filters
- Role-based task visibility (admin vs user)

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure environment variables in `.env`.
4. Run FastAPI.
5. Run Streamlit.

Example commands:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In a second terminal:

```bash
source venv/bin/activate
streamlit run streamlit_app.py --server.port 8501
```

Open:

- FastAPI docs: `http://127.0.0.1:8000/docs`
- Streamlit app: `http://127.0.0.1:8501`

## Streamlit Configuration

The Streamlit frontend uses these environment variables:

- `FASTAPI_BASE_URL` (default: `http://127.0.0.1:8000`)
- `STREAMLIT_API_TIMEOUT` (default: `15` seconds)

Example:

```bash
FASTAPI_BASE_URL=http://127.0.0.1:8000 streamlit run streamlit_app.py
```

## Docker

The existing Docker setup runs FastAPI + PostgreSQL.

```bash
docker compose up --build
```

If you want Streamlit in Docker too, add a second service in `docker-compose.yml` that runs:

```bash
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```
