from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database.connection import get_db
from app.schemas.user import Token, UserCreate, UserRegister, UserResponse
from app.service.UsersService import UsersService
from app.service.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"request": request})


@router.post("/register", response_model=UserResponse)
async def register_user(user: UserRegister, db: Session = Depends(get_db)):
    users_service = UsersService(db)

    def create():
        return users_service.create_user(UserCreate(username=user.username, password=user.password))

    try:
        return await run_in_threadpool(create)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/register/form")
async def register_user_from_form(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    users_service = UsersService(db)

    try:
        validated = UserRegister(username=username.strip(), password=password)
    except ValidationError:
        return RedirectResponse(url="/auth/register?error=invalid_input", status_code=303)

    try:
        await run_in_threadpool(
            lambda: users_service.create_user(
                UserCreate(
                    username=validated.username,
                    password=validated.password,
                )
            )
        )
    except ValueError as exc:
        if "already exists" in str(exc).lower():
            return RedirectResponse(url="/auth/register?error=username_taken", status_code=303)
        return RedirectResponse(url="/auth/register?error=invalid_input", status_code=303)

    return RedirectResponse(url="/auth/login?registered=1", status_code=303)


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = await run_in_threadpool(
        lambda: authenticate_user(db, form_data.username, form_data.password)
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login")
async def login_from_form(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = await run_in_threadpool(lambda: authenticate_user(db, username, password))
    if not user:
        return RedirectResponse(url="/auth/login?error=invalid_credentials", status_code=303)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.id}, expires_delta=access_token_expires)

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


@router.post("/logout")
async def logout_user():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user
