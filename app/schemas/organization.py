from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None

class OrganizationResponse(OrganizationBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
