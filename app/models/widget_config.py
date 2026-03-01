# app/models/widget_config.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import uuid

class WidgetConfig(Base):
    __tablename__ = "widget_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Default Widget")
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    # Widget Key for Authentication
    widget_key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Customization Settings
    is_enabled = Column(Boolean, default=True)
    theme_color = Column(String, default="#991b1b")  # Primary color
    bubble_icon = Column(String, default="MessageSquare")
    welcome_message = Column(String, default="Hi! How can I help you today?")
    bot_name = Column(String, default="RheXa AI")
    position = Column(String, default="bottom-right")  # bottom-right, bottom-left
    show_branding = Column(Boolean, default=True)
    default_theme = Column(String, default="light")  # light or dark
    logo_url = Column(String, nullable=True)  # URL to custom logo
    
    # Advanced customization (JSON for future proofing)
    custom_css = Column(Text, nullable=True)
    allowed_domains = Column(JSON, default=list) # List of allowed domains for CORS
    selected_sources = Column(JSON, default=dict) # {"documents": [], "databases": []}
    
    organization = relationship("Organization")

    def __repr__(self):
        return f"<WidgetConfig(org_id={self.organization_id}, key='{self.widget_key}')>"
