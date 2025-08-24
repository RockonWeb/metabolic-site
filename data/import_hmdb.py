#!/usr/bin/env python3
"""
Скрипт для импорта метаболитов из HMDB (Human Metabolome Database)
Загружает полную базу метаболитов с химическими формулами, массами и ссылками
"""

import requests
import pandas as pd
import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HMDBImporter:
    def __init__(self, db_path: str = "data/metabolome.db"):
        self.db_path = db_path
        self.base_url = "https://hmdb.ca"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_hmdb_metabolites(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получение списка метаболитов из HMDB API"""
        logger.info(f"Загружаем до {limit} метаболитов из HMDB...")
        
        metabolites = []
        offset = 0
        batch_size = 100
        
        while len(metabolites) < limit:
            try:
                url = f"{self.base_url}/api/metabolites"
                params = {
                    'offset': offset,
                    'limit': min(batch_size, limit - len(metabolites))
                }
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if not data or 'metabolites' not in data:
                    break
                    
                batch = data['metabolites']
                if not batch:
                    break
                    
                metabolites.extend(batch)
                offset += len(batch)
                
                logger.info(f"Загружено {len(metabolites)} метаболитов...")
                
                # Пауза между запросами
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке метаболитов: {e}")
                break
                
        logger.info(f"Всего загружено {len(metabolites)} метаболитов")
        return metabolites[:limit]
    
    def get_metabolite_details(self, hmdb_id: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о метаболите"""
        try:
            url = f"{self.base_url}/api/metabolites/{hmdb_id}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.warning(f"Не удалось загрузить детали для {hmdb_id}: {e}")
            return None
    
    def parse_metabolite_data(self, metabolite: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг данных метаболита в нужный формат"""
        try:
            # Основная информация
            parsed = {
                'name': metabolite.get('name', ''),
                'formula': metabolite.get('chemical_formula', ''),
                'exact_mass': self._parse_mass(metabolite.get('monisotopic_molecular_weight', '')),
                'hmdb_id': metabolite.get('accession', ''),
                'kegg_id': metabolite.get('kegg_id', ''),
                'chebi_id': metabolite.get('chebi_id', ''),
                'pubchem_cid': metabolite.get('pubchem_compound_id', ''),
                'class_name': self._determine_class(metabolite),
                'pathways': self._extract_pathways(metabolite),
                'enzymes': self._extract_enzymes(metabolite)
            }
            
            # Валидация данных
            if not parsed['name'] or not parsed['formula']:
                return None
                
            return parsed
            
        except Exception as e:
            logger.warning(f"Ошибка парсинга метаболита {metabolite.get('accession', 'unknown')}: {e}")
            return None
    
    def _parse_mass(self, mass_str: str) -> Optional[float]:
        """Парсинг массы из строки"""
        try:
            if mass_str and mass_str.strip():
                return float(mass_str.strip())
        except (ValueError, TypeError):
            pass
        return None
    
    def _determine_class(self, metabolite: Dict[str, Any]) -> str:
        """Определение класса соединения"""
        # Анализируем название и описание для определения класса
        name = metabolite.get('name', '').lower()
        description = metabolite.get('description', '').lower()
        
        # Ключевые слова для определения классов
        if any(word in name for word in ['acid', 'кислота', 'acidic']):
            return 'Органические кислоты'
        elif any(word in name for word in ['glucose', 'fructose', 'sugar', 'сахар', 'углевод']):
            return 'Углеводы'
        elif any(word in name for word in ['amino', 'аминокислота', 'protein']):
            return 'Аминокислоты'
        elif any(word in name for word in ['lipid', 'fat', 'жир', 'липид']):
            return 'Липиды'
        elif any(word in name for word in ['nucleotide', 'nucleic', 'нуклеотид']):
            return 'Нуклеотиды'
        elif any(word in name for word in ['vitamin', 'витамин']):
            return 'Витамины'
        else:
            return 'Другие соединения'
    
    def _extract_pathways(self, metabolite: Dict[str, Any]) -> List[str]:
        """Извлечение биохимических путей"""
        pathways = []
        
        # Из биологических свойств
        biological_properties = metabolite.get('biological_properties', {})
        if biological_properties:
            pathway_info = biological_properties.get('pathway', [])
            if isinstance(pathway_info, list):
                for pathway in pathway_info:
                    if isinstance(pathway, dict) and 'name' in pathway:
                        pathways.append(pathway['name'])
                    elif isinstance(pathway, str):
                        pathways.append(pathway)
        
        # Из описания
        description = metabolite.get('description', '')
        if description:
            # Простой поиск по ключевым словам
            pathway_keywords = ['гликолиз', 'цикл кребса', 'глюконеогенез', 'β-окисление']
            for keyword in pathway_keywords:
                if keyword.lower() in description.lower():
                    pathways.append(keyword.title())
        
        return list(set(pathways))[:5]  # Максимум 5 путей
    
    def _extract_enzymes(self, metabolite: Dict[str, Any]) -> List[str]:
        """Извлечение связанных ферментов"""
        enzymes = []
        
        # Из биологических свойств
        biological_properties = metabolite.get('biological_properties', {})
        if biological_properties:
            enzyme_info = biological_properties.get('enzyme', [])
            if isinstance(enzyme_info, list):
                for enzyme in enzyme_info:
                    if isinstance(enzyme, dict) and 'name' in enzyme:
                        enzymes.append(enzyme['name'])
                    elif isinstance(enzyme, str):
                        enzymes.append(enzyme)
        
        return list(set(enzymes))[:3]  # Максимум 3 фермента
    
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
                source TEXT DEFAULT 'hmdb',
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
                hmdb_id TEXT UNIQUE,
                chebi_id TEXT,
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metabolites_hmdb ON metabolites(hmdb_id)')
        
        conn.commit()
        conn.close()
        logger.info("Таблицы базы данных созданы")
    
    def import_metabolites(self, limit: int = 1000):
        """Основной метод импорта метаболитов"""
        logger.info("Начинаем импорт метаболитов из HMDB...")
        
        # Создаем таблицы
        self.create_database_tables()
        
        # Получаем список метаболитов
        metabolites = self.get_hmdb_metabolites(limit)
        
        if not metabolites:
            logger.error("Не удалось загрузить метаболиты")
            return
        
        # Подключаемся к базе
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Словари для кэширования
        classes_cache = {}
        pathways_cache = {}
        enzymes_cache = {}
        
        imported_count = 0
        skipped_count = 0
        
        for i, metabolite in enumerate(metabolites):
            try:
                # Парсим данные
                parsed = self.parse_metabolite_data(metabolite)
                if not parsed:
                    skipped_count += 1
                    continue
                
                # Обрабатываем класс
                class_name = parsed['class_name']
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
                    (name, formula, exact_mass, hmdb_id, chebi_id, kegg_id, pubchem_cid, class_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    parsed['name'], parsed['formula'], parsed['exact_mass'],
                    parsed['hmdb_id'], parsed['chebi_id'], parsed['kegg_id'],
                    parsed['pubchem_cid'], class_id
                ))
                
                if cursor.rowcount > 0:
                    metabolite_id = cursor.lastrowid
                    
                    # Обрабатываем пути
                    for pathway_name in parsed['pathways']:
                        if pathway_name not in pathways_cache:
                            cursor.execute('INSERT OR IGNORE INTO pathways (name) VALUES (?)', (pathway_name,))
                            cursor.execute('SELECT id FROM pathways WHERE name = ?', (pathway_name,))
                            pathway_id = cursor.fetchone()[0]
                            pathways_cache[pathway_name] = pathway_id
                        else:
                            pathway_id = pathways_cache[pathway_name]
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO metabolite_pathway (metabolite_id, pathway_id)
                            VALUES (?, ?)
                        ''', (metabolite_id, pathway_id))
                    
                    # Обрабатываем ферменты
                    for enzyme_name in parsed['enzymes']:
                        if enzyme_name not in enzymes_cache:
                            cursor.execute('INSERT OR IGNORE INTO enzymes (name) VALUES (?)', (enzyme_name,))
                            cursor.execute('SELECT id FROM enzymes WHERE name = ?', (enzyme_name,))
                            enzyme_id = cursor.fetchone()[0]
                            enzymes_cache[enzyme_name] = enzyme_id
                        else:
                            enzyme_id = enzymes_cache[enzyme_name]
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO metabolite_enzyme (metabolite_id, enzyme_id)
                            VALUES (?, ?)
                        ''', (metabolite_id, enzyme_id))
                    
                    imported_count += 1
                else:
                    skipped_count += 1
                
                # Логируем прогресс
                if (i + 1) % 100 == 0:
                    logger.info(f"Обработано {i + 1}/{len(metabolites)} метаболитов")
                    conn.commit()  # Периодически сохраняем
                
            except Exception as e:
                logger.error(f"Ошибка при импорте метаболита {metabolite.get('accession', 'unknown')}: {e}")
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
    importer = HMDBImporter()
    
    # Импортируем метаболиты (можно изменить лимит)
    importer.import_metabolites(limit=2000)  # Начнем с 2000, можно увеличить

if __name__ == "__main__":
    main()
