from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from api.database.base import Base
from .associations import metabolite_pathway

class Pathway(Base):
    __tablename__ = "pathways"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    name_ru = Column(String(255), nullable=True, index=True)  # Русское название
    source = Column(String(50))  # kegg|reactome|hmdb
    ext_id = Column(String(50), index=True)  # external ID in source
    
    # Relationships
    metabolites = relationship(
        "Metabolite", 
        secondary=metabolite_pathway, 
        back_populates="pathways"
    )
    
    def __repr__(self):
        return f"<Pathway(id={self.id}, name='{self.name}', source='{self.source}')>"
