from pydantic import BaseModel, Field
from typing import Optional

class PathwayBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source: Optional[str] = Field(None, max_length=50)
    ext_id: Optional[str] = Field(None, max_length=50)

class PathwayCreate(PathwayBase):
    pass

class PathwayOut(PathwayBase):
    id: int
    
    class Config:
        from_attributes = True
