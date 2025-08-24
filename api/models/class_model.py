from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from api.database.base import Base

class Class(Base):
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    name_ru = Column(String(255), nullable=True, index=True)  # Русское название
    
    # Relationships
    metabolites = relationship("Metabolite", back_populates="class_")
    
    def __repr__(self):
        return f"<Class(id={self.id}, name='{self.name}')>"
