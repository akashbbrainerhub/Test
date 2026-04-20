from datetime import datetime

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.user import User, UserRole


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(self, task_create, current_user: User) -> Task:
        new_task = Task(
            title=task_create.title,
            description=task_create.description,
            status=task_create.status,
            deadline=task_create.deadline,
            user_id=current_user.id,
        )
        self.db.add(new_task)
        self.db.commit()
        self.db.refresh(new_task)
        return new_task

    def get_tasks(
        self,
        current_user: User,
        status: str | None = None,
        deadline_from: datetime | None = None,
        deadline_to: datetime | None = None,
        page: int = 1,
        size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        query = self.db.query(Task)

        if current_user.role != UserRole.ADMIN:
            query = query.filter(Task.user_id == current_user.id)

        if status:
            query = query.filter(Task.status == status)
        if deadline_from:
            query = query.filter(Task.deadline >= deadline_from)
        if deadline_to:
            query = query.filter(Task.deadline <= deadline_to)

        sort_mapping = {
            "created_at": Task.created_at,
            "deadline": Task.deadline,
            "title": Task.title,
            "status": Task.status,
        }
        sort_column = sort_mapping.get(sort_by, Task.created_at)
        sort_expr = asc(sort_column) if sort_order == "asc" else desc(sort_column)

        query = query.order_by(sort_expr)

        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()

        return {"items": items, "total": total, "page": page, "size": size}

    def get_task_by_id(self, task_id: str, current_user: User) -> Task | None:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
            return None
        return task

    def delete_task(self, task_id: str, current_user: User) -> bool:
        task = self.get_task_by_id(task_id, current_user)
        if not task:
            return False

        self.db.delete(task)
        self.db.commit()
        return True

    def update_task(self, task_id: str, task_update, current_user: User) -> Task | None:
        task = self.get_task_by_id(task_id, current_user)
        if not task:
            return None

        if task_update.title is not None:
            task.title = task_update.title
        if task_update.description is not None:
            task.description = task_update.description
        if task_update.status is not None:
            task.status = task_update.status
        if task_update.deadline is not None:
            task.deadline = task_update.deadline

        self.db.commit()
        self.db.refresh(task)
        return task
