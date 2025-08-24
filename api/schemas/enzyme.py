from pydantic import BaseModel, Field
from typing import Optional

class EnzymeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    name_ru: Optional[str] = Field(None, max_length=255)
    uniprot_id: Optional[str] = Field(None, max_length=50)
    ec_number: Optional[str] = Field(None, max_length=50)
    organism: Optional[str] = Field(None, max_length=255)
    organism_type: Optional[str] = Field(None, max_length=100)
    family: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    molecular_weight: Optional[float] = Field(None, gt=0)
    optimal_ph: Optional[float] = Field(None, ge=0, le=14)
    optimal_temperature: Optional[float] = Field(None, ge=-273)
    brenda_id: Optional[str] = Field(None, max_length=50)
    kegg_enzyme_id: Optional[str] = Field(None, max_length=50)
    protein_name: Optional[str] = Field(None, max_length=500)
    gene_name: Optional[str] = Field(None, max_length=100)
    tissue_specificity: Optional[str] = None
    subcellular_location: Optional[str] = Field(None, max_length=255)

class EnzymeCreate(EnzymeBase):
    pass

class EnzymeOut(EnzymeBase):
    id: int
    
    class Config:
        from_attributes = True
