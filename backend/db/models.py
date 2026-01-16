from sqlalchemy import Column, String, Text
from db.base import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    api_key = Column(Text, nullable=False)

