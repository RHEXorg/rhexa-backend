from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_active = Column(Integer, default=1)  # 1 for True, 0 for False (SQLite friendly)
    is_superuser = Column(Integer, default=0)
    is_verified = Column(Integer, default=0) # 0 for False, 1 for True
    verification_code = Column(String, nullable=True)
    auth_provider = Column(String, default="local") # 'local' or 'google'
    avatar_url = Column(String, nullable=True)  # Path to uploaded profile image

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
