from app.models.user import User
from app.schemas.user import UserCreate
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.service.auth import get_password_hash


class UsersService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, user_create: UserCreate) -> User:
        existing = self.get_user_by_username(user_create.username)
        if existing:
            raise ValueError("Username already exists")

        new_user = User(
            username=user_create.username,
            role=user_create.role,
            password=get_password_hash(user_create.password),
        )
        self.db.add(new_user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Username already exists")
        self.db.refresh(new_user)
        return new_user