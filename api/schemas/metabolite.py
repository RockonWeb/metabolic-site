from pydantic import BaseModel, Field
from typing import Optional, List

class MetaboliteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    name_ru: Optional[str] = Field(None, max_length=255)
    formula: Optional[str] = Field(None, max_length=100)
    exact_mass: Optional[float] = Field(None, ge=0)
    hmdb_id: Optional[str] = Field(None, max_length=50)
    chebi_id: Optional[str] = Field(None, max_length=50)
    kegg_id: Optional[str] = Field(None, max_length=50)
    pubchem_cid: Optional[str] = Field(None, max_length=50)
    class_id: Optional[int] = None

class MetaboliteCreate(MetaboliteBase):
    pass

class MetaboliteUpdate(MetaboliteBase):
    name: Optional[str] = Field(None, min_length=1, max_length=255)

class MetaboliteOut(MetaboliteBase):
    id: int
    class_name: Optional[str] = None
    pathways: List[str] = []
    enzymes: List[str] = []
    
    class Config:
        from_attributes = True
