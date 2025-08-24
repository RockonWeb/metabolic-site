from sqlalchemy import Column, Integer, String, Text, Float
from sqlalchemy.orm import relationship
from api.database.base import Base
from .associations import metabolite_enzyme

class Enzyme(Base):
    __tablename__ = "enzymes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    name_ru = Column(String(255), nullable=True, index=True)  # Русское название
    uniprot_id = Column(String(50), unique=True, index=True)
    
    # Расширенная информация для растительных ферментов
    ec_number = Column(String(50), index=True, nullable=True)  # EC номер
    organism = Column(String(255), index=True, nullable=True)  # Организм
    organism_type = Column(String(100), index=True, nullable=True)  # Тип организма (plant, animal, bacteria, etc.)
    family = Column(String(255), nullable=True)  # Семейство фермента
    description = Column(Text, nullable=True)  # Описание функции
    molecular_weight = Column(Float, nullable=True)  # Молекулярная масса (kDa)
    optimal_ph = Column(Float, nullable=True)  # Оптимальный pH
    optimal_temperature = Column(Float, nullable=True)  # Оптимальная температура (°C)
    brenda_id = Column(String(50), nullable=True)  # ID в BRENDA
    kegg_enzyme_id = Column(String(50), nullable=True)  # ID в KEGG
    protein_name = Column(String(500), nullable=True)  # Полное название белка
    gene_name = Column(String(100), nullable=True)  # Название гена
    tissue_specificity = Column(Text, nullable=True)  # Тканевая специфичность
    subcellular_location = Column(String(255), nullable=True)  # Субклеточная локализация
    
    # Relationships
    metabolites = relationship(
        "Metabolite", 
        secondary=metabolite_enzyme, 
        back_populates="enzymes"
    )
    
    def __repr__(self):
        return f"<Enzyme(id={self.id}, name='{self.name}', ec={self.ec_number}, organism='{self.organism}')>"
