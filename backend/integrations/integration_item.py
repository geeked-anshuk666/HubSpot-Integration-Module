from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class IntegrationItem(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    directory: bool = False
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None # Keeping as str to match current data extraction in hubspot.py
    updated_at: Optional[str] = None # Keeping as str to match current data extraction in hubspot.py
    owner: Optional[str] = None
    status: Optional[str] = None
    # Fields that were in the custom __init__ and should be part of the Pydantic model
    parent_path_or_name: Optional[str] = None
    parent_id: Optional[str] = None
    children: Optional[List[str]] = None
    mime_type: Optional[str] = None
    delta: Optional[str] = None
    drive_id: Optional[str] = None
    visibility: Optional[bool] = True
