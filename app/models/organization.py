from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Billing & Tier Information
    subscription_tier = Column(String, default="free_trial") # free_trial, pro, enterprise
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    billing_cycle = Column(String, nullable=True) # 2_months
    is_active = Column(Integer, default=1) # 1 = active, 0 = expired/cancelled
