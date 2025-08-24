from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from api.models import Metabolite, Class, Pathway, Enzyme
from api.schemas import MetaboliteOut

class MetaboliteService:
    
    @staticmethod
    async def search_metabolites(
        db: AsyncSession,
        q: Optional[str] = None,
        mass: Optional[float] = None,
        tol_ppm: float = 10.0,
        page: int = 1,
        page_size: int = 50
    ) -> List[Metabolite]:
        """Search metabolites by name, formula, or mass"""
        
        stmt = select(Metabolite).join(Class, isouter=True)
        
        conditions = []
        
        # Text search
        if q:
            text_conditions = [
                Metabolite.name.ilike(f"%{q}%"),
                Metabolite.formula == q,
                Metabolite.hmdb_id.ilike(f"%{q}%"),
                Metabolite.kegg_id.ilike(f"%{q}%"),
                Metabolite.chebi_id.ilike(f"%{q}%")
            ]
            conditions.append(or_(*text_conditions))
        
        # Mass search with tolerance
        if mass is not None:
            delta = mass * tol_ppm / 1e6
            low, high = mass - delta, mass + delta
            conditions.append(Metabolite.exact_mass.between(low, high))
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_metabolite_by_id(db: AsyncSession, metabolite_id: int) -> Optional[Metabolite]:
        """Get metabolite by ID with relationships"""
        stmt = (
            select(Metabolite)
            .where(Metabolite.id == metabolite_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def count_search_results(
        db: AsyncSession,
        q: Optional[str] = None,
        mass: Optional[float] = None,
        tol_ppm: float = 10.0
    ) -> int:
        """Count total search results"""
        
        stmt = select(func.count(Metabolite.id))
        
        conditions = []
        
        if q:
            text_conditions = [
                Metabolite.name.ilike(f"%{q}%"),
                Metabolite.formula == q,
                Metabolite.hmdb_id.ilike(f"%{q}%"),
                Metabolite.kegg_id.ilike(f"%{q}%"),
                Metabolite.chebi_id.ilike(f"%{q}%")
            ]
            conditions.append(or_(*text_conditions))
        
        if mass is not None:
            delta = mass * tol_ppm / 1e6
            low, high = mass - delta, mass + delta
            conditions.append(Metabolite.exact_mass.between(low, high))
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        result = await db.execute(stmt)
        return result.scalar()
    
    @staticmethod
    async def convert_to_schema(db: AsyncSession, metabolite: Metabolite) -> MetaboliteOut:
        """Convert SQLAlchemy model to Pydantic schema with relationships"""
        
        # Get class name
        class_name = None
        if metabolite.class_id:
            class_stmt = select(Class.name).where(Class.id == metabolite.class_id)
            class_result = await db.execute(class_stmt)
            class_name = class_result.scalar()
        
        # Get pathways
        pathway_stmt = (
            select(Pathway.name)
            .join(Metabolite.pathways)
            .where(Metabolite.id == metabolite.id)
        )
        pathway_result = await db.execute(pathway_stmt)
        pathways = [row[0] for row in pathway_result.fetchall()]
        
        # Get enzymes
        enzyme_stmt = (
            select(Enzyme.name)
            .join(Metabolite.enzymes)
            .where(Metabolite.id == metabolite.id)
        )
        enzyme_result = await db.execute(enzyme_stmt)
        enzymes = [row[0] for row in enzyme_result.fetchall()]
        
        return MetaboliteOut(
            id=metabolite.id,
            name=metabolite.name,
            formula=metabolite.formula,
            exact_mass=metabolite.exact_mass,
            hmdb_id=metabolite.hmdb_id,
            chebi_id=metabolite.chebi_id,
            kegg_id=metabolite.kegg_id,
            pubchem_cid=metabolite.pubchem_cid,
            class_id=metabolite.class_id,
            class_name=class_name,
            pathways=pathways,
            enzymes=enzymes
        )
