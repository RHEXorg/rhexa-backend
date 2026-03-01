from pydantic import BaseModel
from typing import List, Optional

class DashboardGenerateRequest(BaseModel):
    database_ids: Optional[List[int]] = None
    document_ids: Optional[List[int]] = None
