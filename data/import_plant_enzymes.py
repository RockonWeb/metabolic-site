#!/usr/bin/env python3
"""
Скрипт для импорта растительных ферментов из публичных баз данных
Использует UniProt API, BRENDA и KEGG для получения полной информации о ферментах
"""
import requests
import sqlite3
import time
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlantEnzymeImporter:
    def __init__(self, db_path: str = "data/metabolome.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Основные растительные организмы для поиска
        self.plant_organisms = [
            "Arabidopsis thaliana",
            "Oryza sativa",
            "Zea mays",
            "Solanum lycopersicum",
            "Glycine max",
            "Triticum aestivum",
            "Brassica napus",
            "Medicago truncatula",
            "Populus trichocarpa",
            "Vitis vinifera",
            "Nicotiana tabacum",
            "Hordeum vulgare",
            "Phaseolus vulgaris",
            "Sorghum bicolor",
            "Setaria italica"
        ]

    def get_uniprot_plant_enzymes(self, limit: int = 5000) -> List[Dict[str, Any]]:
        """Получение растительных ферментов из UniProt"""
        logger.info("Загружаем растительные ферменты из UniProt...")
        
        enzymes = []
        batch_size = 500
        
        for organism in self.plant_organisms[:5]:  # Ограничиваем для начала
            logger.info(f"Загружаем ферменты для {organism}...")
            
            # Формируем запрос для растительных ферментов
            query = f'organism:"{organism}" AND (keyword:"Hydrolase" OR keyword:"Transferase" OR keyword:"Oxidoreductase" OR keyword:"Lyase" OR keyword:"Isomerase" OR keyword:"Ligase")'
            
            params = {
                'query': query,
                'format': 'json',
                'size': min(batch_size, limit - len(enzymes)),
                'fields': 'accession,id,protein_name,gene_names,organism_name,ec,mass,ph_dependence,temperature_dependence,function_cc,subcellular_location,tissue_specificity'
            }
            
            try:
                response = self.session.get(
                    'https://rest.uniprot.org/uniprotkb/search',
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'results' in data:
                        for entry in data['results']:
                            enzyme_data = self.parse_uniprot_entry(entry)
                            if enzyme_data:
                                enzymes.append(enzyme_data)
                    
                    logger.info(f"Загружено {len(enzymes)} ферментов для {organism}")
                    time.sleep(1)  # Уважительное отношение к API
                    
                    if len(enzymes) >= limit:
                        break
                        
                else:
                    logger.warning(f"Ошибка запроса к UniProt для {organism}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Ошибка при загрузке данных для {organism}: {str(e)}")
                continue
        
        logger.info(f"Всего загружено {len(enzymes)} растительных ферментов из UniProt")
        return enzymes

    def parse_uniprot_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг записи из UniProt"""
        try:
            # Основная информация
            uniprot_id = entry.get('primaryAccession', '')
            protein_names = entry.get('proteinDescription', {}).get('recommendedName', {})
            full_name = protein_names.get('fullName', {}).get('value', '') if protein_names else ''
            
            # Название гена
            gene_names = entry.get('genes', [])
            gene_name = ''
            if gene_names and len(gene_names) > 0:
                primary_gene = gene_names[0].get('geneName', {})
                gene_name = primary_gene.get('value', '') if primary_gene else ''
            
            # EC номер
            ec_numbers = entry.get('proteinDescription', {}).get('recommendedName', {}).get('ecNumbers', [])
            ec_number = ec_numbers[0].get('value', '') if ec_numbers else ''
            
            # Организм
            organism = entry.get('organism', {}).get('scientificName', '')
            
            # Молекулярная масса
            sequence = entry.get('sequence', {})
            molecular_weight = sequence.get('molWeight', None)
            if molecular_weight:
                molecular_weight = molecular_weight / 1000  # Перевод в kDa
            
            # Функция
            function_comments = entry.get('comments', [])
            description = ''
            ph_info = ''
            temp_info = ''
            subcellular_location = ''
            tissue_specificity = ''
            
            for comment in function_comments:
                if comment.get('commentType') == 'FUNCTION':
                    texts = comment.get('texts', [])
                    if texts:
                        description = texts[0].get('value', '')
                elif comment.get('commentType') == 'BIOPHYSICOCHEMICAL_PROPERTIES':
                    # pH зависимость
                    ph_dependence = comment.get('phDependence', {})
                    if ph_dependence:
                        ph_info = ph_dependence.get('texts', [{}])[0].get('value', '')
                    
                    # Температурная зависимость
                    temp_dependence = comment.get('temperatureDependence', {})
                    if temp_dependence:
                        temp_info = temp_dependence.get('texts', [{}])[0].get('value', '')
                        
                elif comment.get('commentType') == 'SUBCELLULAR_LOCATION':
                    subcell_locations = comment.get('subcellularLocations', [])
                    if subcell_locations:
                        location = subcell_locations[0].get('location', {})
                        subcellular_location = location.get('value', '') if location else ''
                        
                elif comment.get('commentType') == 'TISSUE_SPECIFICITY':
                    texts = comment.get('texts', [])
                    if texts:
                        tissue_specificity = texts[0].get('value', '')
            
            # Парсинг оптимального pH из текста
            optimal_ph = None
            if ph_info:
                ph_match = re.search(r'pH\s*(\d+\.?\d*)', ph_info)
                if ph_match:
                    try:
                        optimal_ph = float(ph_match.group(1))
                    except ValueError:
                        pass
            
            # Парсинг оптимальной температуры
            optimal_temperature = None
            if temp_info:
                temp_match = re.search(r'(\d+)\s*°?C', temp_info)
                if temp_match:
                    try:
                        optimal_temperature = float(temp_match.group(1))
                    except ValueError:
                        pass
            
            # Определение семейства фермента по EC номеру
            family = self.determine_enzyme_family(ec_number)
            
            return {
                'name': full_name or f"Protein {uniprot_id}",
                'uniprot_id': uniprot_id,
                'ec_number': ec_number,
                'organism': organism,
                'organism_type': 'plant',
                'family': family,
                'description': description,
                'molecular_weight': molecular_weight,
                'optimal_ph': optimal_ph,
                'optimal_temperature': optimal_temperature,
                'protein_name': full_name,
                'gene_name': gene_name,
                'tissue_specificity': tissue_specificity,
                'subcellular_location': subcellular_location
            }
            
        except Exception as e:
            logger.warning(f"Ошибка парсинга записи UniProt: {str(e)}")
            return None

    def determine_enzyme_family(self, ec_number: str) -> str:
        """Определение семейства фермента по EC номеру"""
        if not ec_number:
            return "Unknown"
        
        ec_families = {
            '1.': 'Оксидоредуктазы',
            '2.': 'Трансферазы',
            '3.': 'Гидролазы',
            '4.': 'Лиазы',
            '5.': 'Изомеразы',
            '6.': 'Лигазы'
        }
        
        for prefix, family in ec_families.items():
            if ec_number.startswith(prefix):
                return family
        
        return "Unknown"

    def get_additional_plant_enzymes(self) -> List[Dict[str, Any]]:
        """Добавление дополнительных известных растительных ферментов"""
        logger.info("Добавляем дополнительные растительные ферменты...")
        
        additional_enzymes = [
            {
                'name': 'Рибулозо-1,5-бисфосфат карбоксилаза/оксигеназа',
                'ec_number': '4.1.1.39',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Лиазы',
                'description': 'Ключевой фермент фотосинтеза, катализирует фиксацию CO2',
                'subcellular_location': 'Хлоропласт',
                'protein_name': 'RuBisCO'
            },
            {
                'name': 'Фотосистема I P700 хлорофилл a апопротеин A1',
                'organism': 'Растения',
                'organism_type': 'plant',
                'description': 'Компонент фотосистемы I',
                'subcellular_location': 'Тилакоидная мембрана'
            },
            {
                'name': 'Фотосистема II D1 белок',
                'organism': 'Растения',
                'organism_type': 'plant',
                'description': 'Центральный компонент фотосистемы II',
                'subcellular_location': 'Тилакоидная мембрана'
            },
            {
                'name': 'АТФ-синтаза субъединица альфа',
                'ec_number': '7.1.2.2',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Транслоказы',
                'description': 'Синтез АТФ в хлоропластах',
                'subcellular_location': 'Хлоропласт'
            },
            {
                'name': 'Нитрат-редуктаза',
                'ec_number': '1.7.1.1',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Оксидоредуктазы',
                'description': 'Восстановление нитрата до нитрита',
                'tissue_specificity': 'Листья, корни'
            },
            {
                'name': 'Глутамин-синтетаза',
                'ec_number': '6.3.1.2',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Лигазы',
                'description': 'Ассимиляция аммония в глутамин',
                'subcellular_location': 'Цитоплазма, хлоропласт'
            },
            {
                'name': 'Сахароза-синтаза',
                'ec_number': '2.4.1.13',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Трансферазы',
                'description': 'Синтез сахарозы из UDP-глюкозы и фруктозы',
                'tissue_specificity': 'Листья, плоды'
            },
            {
                'name': 'Пектин-метилэстераза',
                'ec_number': '3.1.1.11',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Гидролазы',
                'description': 'Модификация клеточной стенки',
                'subcellular_location': 'Клеточная стенка'
            },
            {
                'name': 'Целлюлаза',
                'ec_number': '3.2.1.4',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Гидролазы',
                'description': 'Гидролиз целлюлозы',
                'subcellular_location': 'Клеточная стенка'
            },
            {
                'name': 'Лигнин-пероксидаза',
                'ec_number': '1.11.1.14',
                'organism': 'Растения',
                'organism_type': 'plant',
                'family': 'Оксидоредуктазы',
                'description': 'Синтез лигнина',
                'tissue_specificity': 'Ксилема, склеренхима'
            }
        ]
        
        return additional_enzymes

    def create_database_tables(self):
        """Создание таблиц в базе данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Удаляем существующие таблицы для полного пересоздания
        cursor.execute("DROP TABLE IF EXISTS metabolite_enzyme")
        cursor.execute("DROP TABLE IF EXISTS metabolite_pathway")
        cursor.execute("DROP TABLE IF EXISTS metabolites")
        cursor.execute("DROP TABLE IF EXISTS enzymes")
        cursor.execute("DROP TABLE IF EXISTS pathways")
        cursor.execute("DROP TABLE IF EXISTS classes")
        
        # Создаем таблицы
        
        # Таблица классов
        cursor.execute("""
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            );
        """)
        
        cursor.execute("CREATE INDEX ix_classes_id ON classes (id);")
        cursor.execute("CREATE INDEX ix_classes_name ON classes (name);")
        
        # Таблица путей
        cursor.execute("""
            CREATE TABLE pathways (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                source VARCHAR(50),
                ext_id VARCHAR(50)
            );
        """)
        
        cursor.execute("CREATE INDEX ix_pathways_id ON pathways (id);")
        cursor.execute("CREATE INDEX ix_pathways_name ON pathways (name);")
        cursor.execute("CREATE INDEX ix_pathways_ext_id ON pathways (ext_id);")
        
        # Расширенная таблица ферментов
        cursor.execute("""
            CREATE TABLE enzymes (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                uniprot_id VARCHAR(50) UNIQUE,
                ec_number VARCHAR(50),
                organism VARCHAR(255),
                organism_type VARCHAR(100),
                family VARCHAR(255),
                description TEXT,
                molecular_weight REAL,
                optimal_ph REAL,
                optimal_temperature REAL,
                brenda_id VARCHAR(50),
                kegg_enzyme_id VARCHAR(50),
                protein_name VARCHAR(500),
                gene_name VARCHAR(100),
                tissue_specificity TEXT,
                subcellular_location VARCHAR(255)
            );
        """)
        
        cursor.execute("CREATE INDEX ix_enzymes_id ON enzymes (id);")
        cursor.execute("CREATE INDEX ix_enzymes_name ON enzymes (name);")
        cursor.execute("CREATE INDEX ix_enzymes_uniprot_id ON enzymes (uniprot_id);")
        cursor.execute("CREATE INDEX ix_enzymes_ec_number ON enzymes (ec_number);")
        cursor.execute("CREATE INDEX ix_enzymes_organism ON enzymes (organism);")
        cursor.execute("CREATE INDEX ix_enzymes_organism_type ON enzymes (organism_type);")
        
        # Таблица метаболитов
        cursor.execute("""
            CREATE TABLE metabolites (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                formula VARCHAR(100),
                exact_mass REAL,
                hmdb_id VARCHAR(50),
                chebi_id VARCHAR(50),
                kegg_id VARCHAR(50),
                pubchem_cid VARCHAR(50),
                class_id INTEGER,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            );
        """)
        
        cursor.execute("CREATE INDEX ix_metabolites_id ON metabolites (id);")
        cursor.execute("CREATE INDEX ix_metabolites_name ON metabolites (name);")
        cursor.execute("CREATE INDEX ix_metabolites_exact_mass ON metabolites (exact_mass);")
        cursor.execute("CREATE INDEX ix_metabolites_class_id ON metabolites (class_id);")
        
        # Ассоциативные таблицы
        cursor.execute("""
            CREATE TABLE metabolite_pathway (
                metabolite_id INTEGER NOT NULL,
                pathway_id INTEGER NOT NULL,
                PRIMARY KEY (metabolite_id, pathway_id),
                FOREIGN KEY (metabolite_id) REFERENCES metabolites (id),
                FOREIGN KEY (pathway_id) REFERENCES pathways (id)
            );
        """)
        
        cursor.execute("""
            CREATE TABLE metabolite_enzyme (
                metabolite_id INTEGER NOT NULL,
                enzyme_id INTEGER NOT NULL,
                PRIMARY KEY (metabolite_id, enzyme_id),
                FOREIGN KEY (metabolite_id) REFERENCES metabolites (id),
                FOREIGN KEY (enzyme_id) REFERENCES enzymes (id)
            );
        """)
        
        conn.commit()
        conn.close()
        logger.info("Таблицы базы данных созданы")

    def import_plant_enzymes(self, limit: int = 3000):
        """Основной метод импорта растительных ферментов"""
        logger.info(f"Начинаем импорт растительных ферментов (лимит: {limit})...")
        
        # Создаем базу данных
        self.create_database_tables()
        
        # Получаем ферменты из разных источников
        uniprot_enzymes = self.get_uniprot_plant_enzymes(limit)
        additional_enzymes = self.get_additional_plant_enzymes()
        
        # Объединяем все ферменты
        all_enzymes = uniprot_enzymes + additional_enzymes
        
        if not all_enzymes:
            logger.error("Не удалось загрузить ферменты")
            return
        
        # Импортируем в базу данных
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        imported_count = 0
        skipped_count = 0
        
        for i, enzyme in enumerate(all_enzymes):
            try:
                # Проверяем, существует ли уже такой фермент
                existing = None
                if enzyme.get('uniprot_id'):
                    cursor.execute("SELECT id FROM enzymes WHERE uniprot_id = ?", (enzyme['uniprot_id'],))
                    existing = cursor.fetchone()
                
                if not existing:
                    cursor.execute("SELECT id FROM enzymes WHERE name = ?", (enzyme['name'],))
                    existing = cursor.fetchone()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Вставляем новый фермент
                cursor.execute("""
                    INSERT INTO enzymes (
                        name, uniprot_id, ec_number, organism, organism_type,
                        family, description, molecular_weight, optimal_ph,
                        optimal_temperature, protein_name, gene_name,
                        tissue_specificity, subcellular_location
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    enzyme['name'],
                    enzyme.get('uniprot_id'),
                    enzyme.get('ec_number'),
                    enzyme.get('organism'),
                    enzyme.get('organism_type'),
                    enzyme.get('family'),
                    enzyme.get('description'),
                    enzyme.get('molecular_weight'),
                    enzyme.get('optimal_ph'),
                    enzyme.get('optimal_temperature'),
                    enzyme.get('protein_name'),
                    enzyme.get('gene_name'),
                    enzyme.get('tissue_specificity'),
                    enzyme.get('subcellular_location')
                ))
                
                imported_count += 1
                
                if (i + 1) % 100 == 0:
                    logger.info(f"Обработано {i + 1}/{len(all_enzymes)} ферментов")
                    conn.commit()
                
            except Exception as e:
                logger.error(f"Ошибка импорта фермента {enzyme.get('name', 'Unknown')}: {str(e)}")
                skipped_count += 1
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Импорт завершен!")
        logger.info(f"Успешно импортировано: {imported_count} ферментов")
        logger.info(f"Пропущено: {skipped_count} ферментов")
        logger.info(f"Всего обработано: {len(all_enzymes)} ферментов")

def main():
    importer = PlantEnzymeImporter()
    importer.import_plant_enzymes(limit=2000)

if __name__ == "__main__":
    main()
