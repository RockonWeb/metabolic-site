from pydantic import BaseModel, Field
from typing import List, Optional
from .metabolite import MetaboliteOut

class SearchResponse(BaseModel):
    metabolites: List[MetaboliteOut]
    total: int
    page: int = 1
    page_size: int = 50

class AnnotationCandidate(BaseModel):
    metabolite: MetaboliteOut
    mass_error_ppm: float
    mass_error_da: float

class AnnotationItem(BaseModel):
    mz: float
    candidates: List[AnnotationCandidate]
    best_match: Optional[MetaboliteOut] = None

class AnnotationResponse(BaseModel):
    items: List[AnnotationItem]
    total_peaks: int
    annotated_peaks: int
