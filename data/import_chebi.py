#!/usr/bin/env python3
"""
Скрипт для импорта метаболитов из ChEBI (Chemical Entities of Biological Interest)
Использует локальные дампы данных для быстрого импорта
"""

import sqlite3
import gzip
import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import requests
from urllib.parse import urljoin

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChEBIImporter:
    def __init__(self, db_path: str = "data/metabolome.db", data_dir: str = "data/chebi"):
        self.db_path = db_path
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # URL для загрузки дампов ChEBI
        self.chebi_base_url = "https://ftp.ebi.ac.uk/pub/databases/chebi/"
        self.files_to_download = [
            "chebi_complete.sdf.gz",  # Полный SDF дамп
            "chebi_names.tsv.gz",     # Названия соединений
            "chebi_formula.tsv.gz",   # Химические формулы
            "chebi_mass.tsv.gz"       # Молекулярные массы
        ]
    
    def download_chebi_dumps(self):
        """Загрузка дампов данных ChEBI"""
        logger.info("Загружаем дампы данных ChEBI...")
        
        for filename in self.files_to_download:
            file_path = self.data_dir / filename
            if file_path.exists():
                logger.info(f"Файл {filename} уже существует, пропускаем")
                continue
            
            url = urljoin(self.chebi_base_url, filename)
            logger.info(f"Загружаем {filename}...")
            
            try:
                response = requests.get(url, stream=True, timeout=300)
                response.raise_for_status()
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Файл {filename} загружен успешно")
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке {filename}: {e}")
                continue
    
    def parse_sdf_file(self, sdf_path: Path, limit: int = 5000) -> List[Dict[str, Any]]:
        """Парсинг SDF файла ChEBI"""
        logger.info(f"Парсим SDF файл {sdf_path}...")
        
        metabolites = []
        current_compound = {}
        compound_count = 0
        
        try:
            with gzip.open(sdf_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    if line == "$$$$":  # Конец соединения
                        if current_compound and self._validate_compound(current_compound):
                            metabolites.append(current_compound.copy())
                            compound_count += 1
                            
                            if compound_count >= limit:
                                break
                        
                        current_compound = {}
                        continue
                    
                    if line.startswith("> <"):
                        # Начало поля
                        field_name = line[3:-1]  # Убираем "> <" и ">"
                        current_compound[field_name] = ""
                    elif line and not line.startswith(">") and current_compound:
                        # Значение поля
                        if field_name in current_compound:
                            current_compound[field_name] += line + " "
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге SDF: {e}")
        
        logger.info(f"Извлечено {len(metabolites)} соединений из SDF")
        return metabolites
    
    def _validate_compound(self, compound: Dict[str, Any]) -> bool:
        """Валидация соединения"""
        required_fields = ['CHEBI_ID', 'NAME', 'FORMULA']
        
        for field in required_fields:
            if field not in compound or not compound[field].strip():
                return False
        
        # Проверяем, что есть химическая формула
        formula = compound['FORMULA'].strip()
        if not formula or len(formula) < 2:
            return False
        
        return True
    
    def parse_tsv_files(self) -> Dict[str, Dict[str, Any]]:
        """Парсинг TSV файлов ChEBI для дополнительной информации"""
        logger.info("Парсим TSV файлы ChEBI...")
        
        chebi_data = {}
        
        # Парсим названия
        names_file = self.data_dir / "chebi_names.tsv.gz"
        if names_file.exists():
            try:
                with gzip.open(names_file, 'rt', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter='\t')
                    for row in reader:
                        if len(row) >= 3:
                            chebi_id = row[0]
                            name = row[1]
                            type_name = row[2]
                            
                            if chebi_id not in chebi_data:
                                chebi_data[chebi_id] = {}
                            
                            if type_name == "NAME":
                                chebi_data[chebi_id]['name'] = name
                            elif type_name == "SYNONYM":
                                if 'synonyms' not in chebi_data[chebi_id]:
                                    chebi_data[chebi_id]['synonyms'] = []
                                chebi_data[chebi_id]['synonyms'].append(name)
            except Exception as e:
                logger.error(f"Ошибка при парсинге названий: {e}")
        
        # Парсим формулы
        formula_file = self.data_dir / "chebi_formula.tsv.gz"
        if formula_file.exists():
            try:
                with gzip.open(formula_file, 'rt', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter='\t')
                    for row in reader:
                        if len(row) >= 2:
                            chebi_id = row[0]
                            formula = row[1]
                            
                            if chebi_id not in chebi_data:
                                chebi_data[chebi_id] = {}
                            chebi_data[chebi_id]['formula'] = formula
            except Exception as e:
                logger.error(f"Ошибка при парсинге формул: {e}")
        
        # Парсим массы
        mass_file = self.data_dir / "chebi_mass.tsv.gz"
        if mass_file.exists():
            try:
                with gzip.open(mass_file, 'rt', encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter='\t')
                    for row in reader:
                        if len(row) >= 2:
                            chebi_id = row[0]
                            try:
                                mass = float(row[1])
                                if chebi_id not in chebi_data:
                                    chebi_data[chebi_id] = {}
                                chebi_data[chebi_id]['mass'] = mass
                            except ValueError:
                                continue
            except Exception as e:
                logger.error(f"Ошибка при парсинге масс: {e}")
        
        logger.info(f"Обработано {len(chebi_data)} записей из TSV файлов")
        return chebi_data
    
    def create_database_tables(self):
        """Создание таблиц в базе данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица классов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Таблица путей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pathways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                source TEXT DEFAULT 'chebi',
                ext_id TEXT
            )
        ''')
        
        # Таблица ферментов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enzymes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                uniprot_id TEXT
            )
        ''')
        
        # Таблица метаболитов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metabolites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                formula TEXT,
                exact_mass REAL,
                hmdb_id TEXT,
                chebi_id TEXT UNIQUE,
                kegg_id TEXT,
                pubchem_cid TEXT,
                class_id INTEGER,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            )
        ''')
        
        # Связующие таблицы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metabolite_pathway (
                metabolite_id INTEGER,
                pathway_id INTEGER,
                PRIMARY KEY (metabolite_id, pathway_id),
                FOREIGN KEY (metabolite_id) REFERENCES metabolites (id),
                FOREIGN KEY (pathway_id) REFERENCES pathways (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metabolite_enzyme (
                metabolite_id INTEGER,
                enzyme_id INTEGER,
                PRIMARY KEY (metabolite_id, enzyme_id),
                FOREIGN KEY (metabolite_id) REFERENCES metabolites (id),
                FOREIGN KEY (enzyme_id) REFERENCES enzymes (id)
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metabolites_name ON metabolites(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metabolites_formula ON metabolites(formula)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metabolites_mass ON metabolites(exact_mass)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metabolites_chebi ON metabolites(chebi_id)')
        
        conn.commit()
        conn.close()
        logger.info("Таблицы базы данных созданы")
    
    def determine_class(self, name: str, formula: str) -> str:
        """Определение класса соединения по названию и формуле"""
        name_lower = name.lower()
        formula_lower = formula.lower()
        
        # Ключевые слова для определения классов
        if any(word in name_lower for word in ['acid', 'кислота', 'acidic', 'ate']):
            return 'Органические кислоты'
        elif any(word in name_lower for word in ['glucose', 'fructose', 'sugar', 'сахар', 'углевод', 'ose']):
            return 'Углеводы'
        elif any(word in name_lower for word in ['amino', 'аминокислота', 'protein', 'peptide']):
            return 'Аминокислоты'
        elif any(word in name_lower for word in ['lipid', 'fat', 'жир', 'липид', 'glycerol']):
            return 'Липиды'
        elif any(word in name_lower for word in ['nucleotide', 'nucleic', 'нуклеотид', 'adenine', 'guanine']):
            return 'Нуклеотиды'
        elif any(word in name_lower for word in ['vitamin', 'витамин']):
            return 'Витамины'
        elif 'c' in formula_lower and 'h' in formula_lower and 'o' in formula_lower:
            # Если есть C, H, O - скорее всего органическое соединение
            return 'Органические соединения'
        else:
            return 'Другие соединения'
    
    def import_metabolites(self, limit: int = 5000):
        """Основной метод импорта метаболитов"""
        logger.info("Начинаем импорт метаболитов из ChEBI...")
        
        # Загружаем дампы, если их нет
        self.download_chebi_dumps()
        
        # Создаем таблицы
        self.create_database_tables()
        
        # Парсим SDF файл
        sdf_file = self.data_dir / "chebi_complete.sdf.gz"
        if not sdf_file.exists():
            logger.error("SDF файл не найден")
            return
        
        metabolites = self.parse_sdf_file(sdf_file, limit)
        
        if not metabolites:
            logger.error("Не удалось извлечь метаболиты из SDF")
            return
        
        # Парсим дополнительные TSV файлы
        chebi_data = self.parse_tsv_files()
        
        # Подключаемся к базе
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Словари для кэширования
        classes_cache = {}
        
        imported_count = 0
        skipped_count = 0
        
        for i, metabolite in enumerate(metabolites):
            try:
                # Извлекаем данные
                chebi_id = metabolite.get('CHEBI_ID', '').strip()
                name = metabolite.get('NAME', '').strip()
                formula = metabolite.get('FORMULA', '').strip()
                mass = metabolite.get('MASS', 0.0)
                
                # Дополнительная информация из TSV
                if chebi_id in chebi_data:
                    tsv_data = chebi_data[chebi_id]
                    if 'name' in tsv_data and not name:
                        name = tsv_data['name']
                    if 'formula' in tsv_data and not formula:
                        formula = tsv_data['formula']
                    if 'mass' in tsv_data and not mass:
                        mass = tsv_data['mass']
                
                # Валидация
                if not name or not formula or not chebi_id:
                    skipped_count += 1
                    continue
                
                # Определяем класс
                class_name = self.determine_class(name, formula)
                if class_name not in classes_cache:
                    cursor.execute('INSERT OR IGNORE INTO classes (name) VALUES (?)', (class_name,))
                    cursor.execute('SELECT id FROM classes WHERE name = ?', (class_name,))
                    class_id = cursor.fetchone()[0]
                    classes_cache[class_name] = class_id
                else:
                    class_id = classes_cache[class_name]
                
                # Вставляем метаболит
                cursor.execute('''
                    INSERT OR IGNORE INTO metabolites 
                    (name, formula, exact_mass, chebi_id, class_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, formula, mass, chebi_id, class_id))
                
                if cursor.rowcount > 0:
                    imported_count += 1
                else:
                    skipped_count += 1
                
                # Логируем прогресс
                if (i + 1) % 1000 == 0:
                    logger.info(f"Обработано {i + 1}/{len(metabolites)} метаболитов")
                    conn.commit()  # Периодически сохраняем
                
            except Exception as e:
                logger.error(f"Ошибка при импорте метаболита {i}: {e}")
                skipped_count += 1
                continue
        
        # Финальное сохранение
        conn.commit()
        conn.close()
        
        logger.info(f"Импорт завершен!")
        logger.info(f"Успешно импортировано: {imported_count}")
        logger.info(f"Пропущено: {skipped_count}")
        logger.info(f"Всего обработано: {len(metabolites)}")

def main():
    """Основная функция"""
    importer = ChEBIImporter()
    
    # Импортируем метаболиты (можно изменить лимит)
    importer.import_metabolites(limit=10000)  # Начнем с 10000

if __name__ == "__main__":
    main()
