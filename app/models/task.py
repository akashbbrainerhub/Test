from sqlalchemy import Column, DateTime, String, Enum
from enum import Enum as PyEnum
from datetime import datetime
from app.database.connection import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import uuid


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=False)
    status = Column(Enum("pending", "in_progress", "completed", name="task_status"), default="pending")
    deadline = Column(DateTime, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="tasks") 