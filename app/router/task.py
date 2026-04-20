from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database.connection import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskStatus, TaskUpdate
from app.service.TaskService import TaskService
from app.service.auth import get_current_user, get_current_user_from_cookie

router = APIRouter(tags=["tasks"])
templates = Jinja2Templates(directory="app/templates")


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None

    cleaned_status = status.strip()
    if not cleaned_status:
        return None

    allowed_status = {item.value for item in TaskStatus}
    if cleaned_status not in allowed_status:
        raise HTTPException(status_code=422, detail="Invalid status filter")

    return cleaned_status


def _parse_deadline(value: str) -> datetime:
    return datetime.fromisoformat(value)


@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(
    status: str | None = Query(default=None),
    deadline_from: datetime | None = Query(default=None),
    deadline_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    normalized_status = _normalize_status(status)

    task_service = TaskService(db)
    payload = await run_in_threadpool(
        lambda: task_service.get_tasks(
            current_user=current_user,
            status=normalized_status,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )
    return payload


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_by_id(task_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    task_service = TaskService(db)
    task = await run_in_threadpool(lambda: task_service.get_task_by_id(task_id, current_user))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    task_service = TaskService(db)
    return await run_in_threadpool(lambda: task_service.create_task(task, current_user))


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task_service = TaskService(db)
    task = await run_in_threadpool(lambda: task_service.update_task(task_id, task_update, current_user))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    task_service = TaskService(db)
    deleted = await run_in_threadpool(lambda: task_service.delete_task(task_id, current_user))
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


@router.get("/dashboard")
async def dashboard(
    request: Request,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    normalized_status = _normalize_status(status)

    try:
        current_user = await run_in_threadpool(lambda: get_current_user_from_cookie(request, db))
    except HTTPException:
        return RedirectResponse(url="/auth/login", status_code=303)

    task_service = TaskService(db)
    payload = await run_in_threadpool(
        lambda: task_service.get_tasks(
            current_user=current_user,
            status=normalized_status,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "tasks": payload["items"],
            "total": payload["total"],
            "page": payload["page"],
            "size": payload["size"],
            "status_filter": normalized_status or "",
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    )


@router.post("/dashboard/tasks")
async def create_task_from_dashboard(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    deadline: str = Form(...),
    status: TaskStatus = Form(default=TaskStatus.PENDING),
    db: Session = Depends(get_db),
):
    try:
        current_user = await run_in_threadpool(lambda: get_current_user_from_cookie(request, db))
    except HTTPException:
        return RedirectResponse(url="/auth/login", status_code=303)

    task_service = TaskService(db)
    await run_in_threadpool(
        lambda: task_service.create_task(
            TaskCreate(
                title=title,
                description=description,
                status=status,
                deadline=_parse_deadline(deadline),
            ),
            current_user,
        )
    )
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/dashboard/tasks/{task_id}/update")
async def update_task_from_dashboard(
    task_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    deadline: str = Form(...),
    status: TaskStatus = Form(...),
    db: Session = Depends(get_db),
):
    try:
        current_user = await run_in_threadpool(lambda: get_current_user_from_cookie(request, db))
    except HTTPException:
        return RedirectResponse(url="/auth/login", status_code=303)

    task_service = TaskService(db)
    await run_in_threadpool(
        lambda: task_service.update_task(
            task_id,
            TaskUpdate(
                title=title,
                description=description,
                status=status,
                deadline=_parse_deadline(deadline),
            ),
            current_user,
        )
    )
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/dashboard/tasks/{task_id}/delete")
async def delete_task_from_dashboard(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        current_user = await run_in_threadpool(lambda: get_current_user_from_cookie(request, db))
    except HTTPException:
        return RedirectResponse(url="/auth/login", status_code=303)

    task_service = TaskService(db)
    await run_in_threadpool(lambda: task_service.delete_task(task_id, current_user))
    return RedirectResponse(url="/dashboard", status_code=303)
