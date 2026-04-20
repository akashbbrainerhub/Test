from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.router import user
from app.router import task

app = FastAPI()

app.include_router(user.router)
app.include_router(task.router)


@app.get("/")
def root():
    return RedirectResponse(url="/auth/login", status_code=303)
