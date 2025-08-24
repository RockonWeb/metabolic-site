from pydantic import BaseModel, Field

class ClassBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class ClassCreate(ClassBase):
    pass

class ClassOut(ClassBase):
    id: int
    
    class Config:
        from_attributes = True
