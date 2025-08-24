#!/usr/bin/env python3
"""
Data import script for Metabolome Handbook
Imports sample metabolites data from various sources
"""

import sys
import os
import asyncio
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.database.base import Base, DATABASE_URL
from api.models import Metabolite, Class, Pathway, Enzyme, metabolite_pathway, metabolite_enzyme
from dotenv import load_dotenv

load_dotenv()

def create_tables():
    """Create all database tables"""
    # Use sync engine for table creation
    sync_url = DATABASE_URL
    if sync_url.startswith("sqlite+aiosqlite://"):
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite:///")
    
    engine = create_engine(sync_url, echo=True)
    Base.metadata.create_all(engine)
    return engine

def import_sample_data():
    """Import sample metabolites data"""
    engine = create_tables()
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # Create sample classes
        classes_data = [
            {"name": "Аминокислоты"},
            {"name": "Углеводы"},
            {"name": "Липиды"},
            {"name": "Нуклеотиды"},
            {"name": "Органические кислоты"},
            {"name": "Витамины"},
        ]
        
        classes = {}
        for class_data in classes_data:
            # Check if class already exists
            existing_class = session.query(Class).filter_by(name=class_data["name"]).first()
            if existing_class:
                classes[class_data["name"]] = existing_class
            else:
                class_obj = Class(**class_data)
                session.add(class_obj)
                session.flush()
                classes[class_data["name"]] = class_obj
        
        # Create sample pathways
        pathways_data = [
            {"name": "Гликолиз", "source": "kegg", "ext_id": "map00010"},
            {"name": "Цикл Кребса", "source": "kegg", "ext_id": "map00020"},
            {"name": "Биосинтез жирных кислот", "source": "kegg", "ext_id": "map00061"},
            {"name": "Метаболизм пуринов", "source": "kegg", "ext_id": "map00230"},
            {"name": "Метаболизм аминокислот", "source": "kegg", "ext_id": "map01230"},
        ]
        
        pathways = {}
        for pathway_data in pathways_data:
            # Check if pathway already exists
            existing_pathway = session.query(Pathway).filter_by(name=pathway_data["name"]).first()
            if existing_pathway:
                pathways[pathway_data["name"]] = existing_pathway
            else:
                pathway_obj = Pathway(**pathway_data)
                session.add(pathway_obj)
                session.flush()
                pathways[pathway_data["name"]] = pathway_obj
        
        # Create sample enzymes
        enzymes_data = [
            {"name": "Гексокиназа", "uniprot_id": "P19367"},
            {"name": "Глюкозо-6-фосфат изомераза", "uniprot_id": "P06744"},
            {"name": "Цитрат синтаза", "uniprot_id": "O75390"},
            {"name": "Аконитаза", "uniprot_id": "P21399"},
        ]
        
        enzymes = {}
        for enzyme_data in enzymes_data:
            # Check if enzyme already exists
            existing_enzyme = session.query(Enzyme).filter_by(uniprot_id=enzyme_data["uniprot_id"]).first()
            if existing_enzyme:
                enzymes[enzyme_data["name"]] = existing_enzyme
            else:
                enzyme_obj = Enzyme(**enzyme_data)
                session.add(enzyme_obj)
                session.flush()
                enzymes[enzyme_data["name"]] = enzyme_obj
        
        # Sample metabolites data
        metabolites_data = [
            {
                "name": "Глюкоза",
                "formula": "C6H12O6",
                "exact_mass": 180.063388,
                "hmdb_id": "HMDB0000122",
                "kegg_id": "C00031",
                "chebi_id": "CHEBI:4167",
                "pubchem_cid": "5793",
                "class_name": "Углеводы",
                "pathways": ["Гликолиз"],
                "enzymes": ["Гексокиназа"]
            },
            {
                "name": "Глюкозо-6-фосфат",
                "formula": "C6H13O9P",
                "exact_mass": 260.029724,
                "hmdb_id": "HMDB0001401",
                "kegg_id": "C00092",
                "chebi_id": "CHEBI:4170",
                "pubchem_cid": "5958",
                "class_name": "Углеводы",
                "pathways": ["Гликолиз"],
                "enzymes": ["Глюкозо-6-фосфат изомераза"]
            },
            {
                "name": "Фруктозо-6-фосфат",
                "formula": "C6H13O9P",
                "exact_mass": 260.029724,
                "hmdb_id": "HMDB0000124",
                "kegg_id": "C00085",
                "chebi_id": "CHEBI:17754",
                "pubchem_cid": "439184",
                "class_name": "Углеводы",
                "pathways": ["Гликолиз"],
                "enzymes": []
            },
            {
                "name": "Пируват",
                "formula": "C3H4O3",
                "exact_mass": 88.016044,
                "hmdb_id": "HMDB0000243",
                "kegg_id": "C00022",
                "chebi_id": "CHEBI:15361",
                "pubchem_cid": "1060",
                "class_name": "Органические кислоты",
                "pathways": ["Гликолиз"],
                "enzymes": []
            },
            {
                "name": "Цитрат",
                "formula": "C6H8O7",
                "exact_mass": 192.027009,
                "hmdb_id": "HMDB0000094",
                "kegg_id": "C00158",
                "chebi_id": "CHEBI:30769",
                "pubchem_cid": "311",
                "class_name": "Органические кислоты",
                "pathways": ["Цикл Кребса"],
                "enzymes": ["Цитрат синтаза"]
            },
            {
                "name": "Изоцитрат",
                "formula": "C6H8O7",
                "exact_mass": 192.027009,
                "hmdb_id": "HMDB0000193",
                "kegg_id": "C00311",
                "chebi_id": "CHEBI:30815",
                "pubchem_cid": "1198",
                "class_name": "Органические кислоты",
                "pathways": ["Цикл Кребса"],
                "enzymes": ["Аконитаза"]
            },
            {
                "name": "Альфа-Кетоглутарат",
                "formula": "C5H6O5",
                "exact_mass": 146.021524,
                "hmdb_id": "HMDB0000208",
                "kegg_id": "C00026",
                "chebi_id": "CHEBI:16810",
                "pubchem_cid": "51",
                "class_name": "Органические кислоты",
                "pathways": ["Цикл Кребса"],
                "enzymes": []
            },
            {
                "name": "Аланин",
                "formula": "C3H7NO2",
                "exact_mass": 89.047678,
                "hmdb_id": "HMDB0000161",
                "kegg_id": "C00041",
                "chebi_id": "CHEBI:16977",
                "pubchem_cid": "5950",
                "class_name": "Аминокислоты",
                "pathways": ["Метаболизм аминокислот"],
                "enzymes": []
            },
            {
                "name": "Глицин",
                "formula": "C2H5NO2",
                "exact_mass": 75.032028,
                "hmdb_id": "HMDB0000123",
                "kegg_id": "C00037",
                "chebi_id": "CHEBI:15428",
                "pubchem_cid": "750",
                "class_name": "Аминокислоты",
                "pathways": ["Метаболизм аминокислот"],
                "enzymes": []
            },
            {
                "name": "Аденозинтрифосфат",
                "formula": "C10H16N5O13P3",
                "exact_mass": 507.181744,
                "hmdb_id": "HMDB0000538",
                "kegg_id": "C00002",
                "chebi_id": "CHEBI:15422",
                "pubchem_cid": "5957",
                "class_name": "Нуклеотиды",
                "pathways": ["Гликолиз", "Цикл Кребса"],
                "enzymes": []
            },
            {
                "name": "Аденозиндифосфат",
                "formula": "C10H16N5O10P2",
                "exact_mass": 427.0293,
                "hmdb_id": "HMDB0001341",
                "kegg_id": "C00008",
                "chebi_id": "CHEBI:456216",
                "pubchem_cid": "6022",
                "class_name": "Нуклеотиды",
                "pathways": ["Гликолиз", "Цикл Кребса"],
                "enzymes": []
            },
            {
                "name": "Пальмитиновая кислота",
                "formula": "C16H32O2",
                "exact_mass": 256.240230,
                "hmdb_id": "HMDB0000220",
                "kegg_id": "C00249",
                "chebi_id": "CHEBI:15756",
                "pubchem_cid": "985",
                "class_name": "Липиды",
                "pathways": ["Биосинтез жирных кислот"],
                "enzymes": []
            },
            {
                "name": "Ацетил-КоА",
                "formula": "C23H38N7O17P3S",
                "exact_mass": 809.121924,
                "hmdb_id": "HMDB0001206",
                "kegg_id": "C00024",
                "chebi_id": "CHEBI:15351",
                "pubchem_cid": "444493",
                "class_name": "Органические кислоты",
                "pathways": ["Цикл Кребса", "Биосинтез жирных кислот"],
                "enzymes": []
            },
            {
                "name": "Витамин C",
                "formula": "C6H8O6",
                "exact_mass": 176.032088,
                "hmdb_id": "HMDB0000044",
                "kegg_id": "C00097",
                "chebi_id": "CHEBI:29073",
                "pubchem_cid": "54670067",
                "class_name": "Витамины",
                "pathways": [],
                "enzymes": []
            },
            {
                "name": "Лактат",
                "formula": "C3H6O3",
                "exact_mass": 90.031694,
                "hmdb_id": "HMDB0000190",
                "kegg_id": "C00186",
                "chebi_id": "CHEBI:24996",
                "pubchem_cid": "612",
                "class_name": "Органические кислоты",
                "pathways": ["Гликолиз"],
                "enzymes": []
            }
        ]
        
        # Insert metabolites
        for met_data in metabolites_data:
            # Check if metabolite already exists
            existing_metabolite = session.query(Metabolite).filter_by(name=met_data["name"]).first()
            if existing_metabolite:
                print(f"   Skipping existing metabolite: {met_data['name']}")
                continue
            
            # Get class
            class_obj = classes.get(met_data["class_name"])
            
            # Create metabolite
            metabolite = Metabolite(
                name=met_data["name"],
                formula=met_data["formula"],
                exact_mass=met_data["exact_mass"],
                hmdb_id=met_data["hmdb_id"],
                kegg_id=met_data["kegg_id"],
                chebi_id=met_data["chebi_id"],
                pubchem_cid=met_data["pubchem_cid"],
                class_id=class_obj.id if class_obj else None
            )
            
            session.add(metabolite)
            session.flush()
            
            # Add pathway associations
            for pathway_name in met_data["pathways"]:
                if pathway_name in pathways:
                    metabolite.pathways.append(pathways[pathway_name])
            
            # Add enzyme associations
            for enzyme_name in met_data["enzymes"]:
                if enzyme_name in enzymes:
                    metabolite.enzymes.append(enzymes[enzyme_name])
        
        session.commit()
        print(f"✅ Successfully imported {len(metabolites_data)} metabolites")
        print(f"✅ Created {len(classes_data)} classes")
        print(f"✅ Created {len(pathways_data)} pathways")
        print(f"✅ Created {len(enzymes_data)} enzymes")

def main():
    """Main function"""
    print("🚀 Starting data import...")
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    try:
        import_sample_data()
        print("✅ Data import completed successfully!")
    except Exception as e:
        print(f"❌ Error during import: {e}")
        raise

if __name__ == "__main__":
    main()
