from sqlalchemy import Boolean, Column, String, Enum, DateTime
from datetime import datetime
from enum import Enum as PyEnum
import uuid
from app.database.connection import Base
from sqlalchemy.orm import relationship


class UserRole(str, PyEnum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(Enum(UserRole), index=True, default=UserRole.USER)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tasks = relationship("Task", back_populates="user")
    