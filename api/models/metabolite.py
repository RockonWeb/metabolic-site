from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from api.database.base import Base
from .associations import metabolite_pathway, metabolite_enzyme

class Metabolite(Base):
    __tablename__ = "metabolites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    name_ru = Column(String(255), nullable=True, index=True)  # Русское название
    formula = Column(String(100), index=True)
    exact_mass = Column(Float, index=True)
    
    # External IDs
    hmdb_id = Column(String(50), unique=True, index=True)
    chebi_id = Column(String(50), unique=True, index=True)
    kegg_id = Column(String(50), unique=True, index=True)
    pubchem_cid = Column(String(50), unique=True, index=True)
    
    # Foreign Keys
    class_id = Column(Integer, ForeignKey("classes.id"))
    
    # Relationships
    class_ = relationship("Class", back_populates="metabolites")
    pathways = relationship(
        "Pathway", 
        secondary=metabolite_pathway, 
        back_populates="metabolites"
    )
    enzymes = relationship(
        "Enzyme", 
        secondary=metabolite_enzyme, 
        back_populates="metabolites"
    )
    
    # Additional indexes for performance
    __table_args__ = (
        Index('idx_metabolite_mass', 'exact_mass'),
        Index('idx_metabolite_name_formula', 'name', 'formula'),
    )
    
    def __repr__(self):
        return f"<Metabolite(id={self.id}, name='{self.name}', formula='{self.formula}', mass={self.exact_mass})>"
