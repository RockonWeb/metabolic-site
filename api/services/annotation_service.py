from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import pandas as pd
import io
from api.models import Metabolite
from api.schemas import AnnotationResponse, AnnotationItem, AnnotationCandidate, MetaboliteOut
from api.services.metabolite_service import MetaboliteService

class AnnotationService:
    
    @staticmethod
    async def annotate_mz_list(
        db: AsyncSession,
        mz_values: List[float],
        tol_ppm: float = 10.0,
        max_candidates: int = 10
    ) -> AnnotationResponse:
        """Annotate a list of m/z values"""
        
        items = []
        annotated_count = 0
        
        for mz in mz_values:
            candidates = await AnnotationService._find_candidates(
                db, mz, tol_ppm, max_candidates
            )
            
            best_match = None
            if candidates:
                best_match = candidates[0].metabolite
                annotated_count += 1
            
            items.append(AnnotationItem(
                mz=mz,
                candidates=candidates,
                best_match=best_match
            ))
        
        return AnnotationResponse(
            items=items,
            total_peaks=len(mz_values),
            annotated_peaks=annotated_count
        )
    
    @staticmethod
    async def annotate_csv_data(
        db: AsyncSession,
        csv_content: bytes,
        mz_column: str = "mz",
        tol_ppm: float = 10.0,
        max_candidates: int = 10
    ) -> AnnotationResponse:
        """Annotate CSV data with m/z values"""
        
        # Read CSV
        df = pd.read_csv(io.BytesIO(csv_content))
        
        if mz_column not in df.columns:
            raise ValueError(f"Column '{mz_column}' not found in CSV")
        
        # Extract m/z values
        mz_values = df[mz_column].astype(float).tolist()
        
        return await AnnotationService.annotate_mz_list(
            db, mz_values, tol_ppm, max_candidates
        )
    
    @staticmethod
    async def _find_candidates(
        db: AsyncSession,
        mz: float,
        tol_ppm: float,
        max_candidates: int
    ) -> List[AnnotationCandidate]:
        """Find metabolite candidates for a given m/z value"""
        
        delta = mz * tol_ppm / 1e6
        low, high = mz - delta, mz + delta
        
        # Find metabolites within mass tolerance
        stmt = (
            select(Metabolite)
            .where(Metabolite.exact_mass.between(low, high))
            .order_by(func.abs(Metabolite.exact_mass - mz))
            .limit(max_candidates)
        )
        
        result = await db.execute(stmt)
        metabolites = result.scalars().all()
        
        candidates = []
        for metabolite in metabolites:
            if metabolite.exact_mass is not None:
                mass_error_da = abs(metabolite.exact_mass - mz)
                mass_error_ppm = (mass_error_da / mz) * 1e6
                
                metabolite_out = await MetaboliteService.convert_to_schema(db, metabolite)
                
                candidates.append(AnnotationCandidate(
                    metabolite=metabolite_out,
                    mass_error_ppm=mass_error_ppm,
                    mass_error_da=mass_error_da
                ))
        
        return candidates
    
    @staticmethod
    def export_annotation_results(
        annotation_response: AnnotationResponse,
        format: str = "csv"
    ) -> bytes:
        """Export annotation results to CSV or Excel"""
        
        # Prepare data for export
        rows = []
        for item in annotation_response.items:
            if item.best_match:
                rows.append({
                    "mz": item.mz,
                    "best_match_name": item.best_match.name,
                    "best_match_id": item.best_match.id,
                    "formula": item.best_match.formula,
                    "exact_mass": item.best_match.exact_mass,
                    "mass_error_ppm": item.candidates[0].mass_error_ppm if item.candidates else None,
                    "mass_error_da": item.candidates[0].mass_error_da if item.candidates else None,
                    "hmdb_id": item.best_match.hmdb_id,
                    "kegg_id": item.best_match.kegg_id,
                    "chebi_id": item.best_match.chebi_id,
                    "pubchem_cid": item.best_match.pubchem_cid,
                    "num_candidates": len(item.candidates)
                })
            else:
                rows.append({
                    "mz": item.mz,
                    "best_match_name": "No match found",
                    "best_match_id": None,
                    "formula": None,
                    "exact_mass": None,
                    "mass_error_ppm": None,
                    "mass_error_da": None,
                    "hmdb_id": None,
                    "kegg_id": None,
                    "chebi_id": None,
                    "pubchem_cid": None,
                    "num_candidates": 0
                })
        
        df = pd.DataFrame(rows)
        
        if format.lower() == "csv":
            return df.to_csv(index=False).encode('utf-8')
        elif format.lower() == "excel":
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)
            return buffer.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
