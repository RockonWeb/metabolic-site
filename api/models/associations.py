from sqlalchemy import Table, Column, Integer, ForeignKey
from api.database.base import Base

# Association tables for many-to-many relationships
metabolite_pathway = Table(
    'metabolite_pathway',
    Base.metadata,
    Column('metabolite_id', Integer, ForeignKey('metabolites.id'), primary_key=True),
    Column('pathway_id', Integer, ForeignKey('pathways.id'), primary_key=True)
)

metabolite_enzyme = Table(
    'metabolite_enzyme',
    Base.metadata,
    Column('metabolite_id', Integer, ForeignKey('metabolites.id'), primary_key=True),
    Column('enzyme_id', Integer, ForeignKey('enzymes.id'), primary_key=True)
)
