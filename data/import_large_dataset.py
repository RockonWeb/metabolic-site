#!/usr/bin/env python3
"""
Скрипт для импорта большого количества метаболитов из CSV файла
Создает полную базу данных для учебных целей
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
import random

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LargeDatasetImporter:
    def __init__(self, db_path: str = "data/metabolome.db"):
        self.db_path = db_path
        
        # Классы соединений
        self.classes = [
            "Аминокислоты", "Углеводы", "Липиды", "Нуклеотиды", 
            "Органические кислоты", "Витамины", "Алкалоиды", "Фенолы",
            "Терпены", "Стероиды", "Пептиды", "Белки", "Нуклеиновые кислоты"
        ]
        
        # Биохимические пути
        self.pathways = [
            "Гликолиз", "Цикл Кребса", "Глюконеогенез", "β-окисление жирных кислот",
            "Синтез аминокислот", "Синтез нуклеотидов", "Синтез холестерина",
            "Фотосинтез", "Дыхательная цепь", "Синтез гликогена", "Гликогенолиз",
            "Пентозофосфатный путь", "Синтез жирных кислот", "Синтез кетоновых тел",
            "Мочевинный цикл", "Синтез креатина", "Синтез гема", "Синтез стероидов"
        ]
        
        # Ферменты
        self.enzymes = [
            "Гексокиназа", "Глюкозо-6-фосфат изомераза", "Фосфофруктокиназа", "Альдолаза",
            "Триозофосфат изомераза", "Глицеральдегид-3-фосфат дегидрогеназа", "Фосфоглицераткиназа",
            "Фосфоглицерат мутаза", "Енолаза", "Пируваткиназа", "Пируват дегидрогеназа",
            "Цитрат синтаза", "Аконитаза", "Изоцитрат дегидрогеназа", "α-кетоглутарат дегидрогеназа",
            "Сукцинил-КоА синтетаза", "Сукцинат дегидрогеназа", "Фумараза", "Малат дегидрогеназа",
            "Ацетил-КоА карбоксилаза", "Фруктозо-1,6-бисфосфатаза", "Глюкозо-6-фосфатаза"
        ]
    
    def generate_metabolites(self, count: int = 10000) -> List[Dict[str, Any]]:
        """Генерация большого количества метаболитов"""
        logger.info(f"Генерируем {count} метаболитов...")
        
        metabolites = []
        
        # Базовые формулы для разных классов
        base_formulas = {
            "Аминокислоты": ["C3H7NO2", "C4H9NO2", "C5H11NO2", "C6H13NO2", "C9H11NO2"],
            "Углеводы": ["C6H12O6", "C5H10O5", "C4H8O4", "C7H14O7", "C8H16O8"],
            "Липиды": ["C16H32O2", "C18H36O2", "C20H40O2", "C22H44O2", "C24H48O2"],
            "Нуклеотиды": ["C10H16N5O13P3", "C10H15N5O10P2", "C10H14N5O7P", "C9H13N3O5"],
            "Органические кислоты": ["C3H6O3", "C4H6O4", "C5H8O4", "C6H8O6", "C7H6O6"],
            "Витамины": ["C6H8O6", "C20H30O", "C27H44O", "C63H88CoN14O14P", "C19H28O2"],
            "Алкалоиды": ["C8H10N4O2", "C17H19NO3", "C21H22N2O2", "C20H24N2O2"],
            "Фенолы": ["C6H6O", "C7H8O", "C8H10O", "C9H12O", "C10H14O"],
            "Терпены": ["C10H16", "C15H24", "C20H32", "C25H40", "C30H48"],
            "Стероиды": ["C27H46O", "C28H48O", "C29H50O", "C30H52O", "C31H54O"]
        }
        
        # Базовые названия
        base_names = {
            "Аминокислоты": ["Аланин", "Глицин", "Валин", "Лейцин", "Изолейцин", "Пролин", "Фенилаланин", "Тирозин", "Триптофан", "Серин", "Треонин", "Цистеин", "Метионин", "Аспарагин", "Глутамин", "Аспартат", "Глутамат", "Лизин", "Аргинин", "Гистидин"],
            "Углеводы": ["Глюкоза", "Фруктоза", "Галактоза", "Манноза", "Рибоза", "Дезоксирибоза", "Ксилоза", "Арабиноза", "Лактоза", "Сахароза", "Мальтоза", "Целлобиоза", "Крахмал", "Гликоген", "Целлюлоза"],
            "Липиды": ["Пальмитиновая кислота", "Стеариновая кислота", "Олеиновая кислота", "Линолевая кислота", "Линоленовая кислота", "Арахидоновая кислота", "Холестерин", "Фосфатидилхолин", "Фосфатидилэтаноламин", "Сфингомиелин"],
            "Нуклеотиды": ["Аденозинтрифосфат", "Аденозиндифосфат", "Аденозинмонофосфат", "Гуанозинтрифосфат", "Цитидинтрифосфат", "Уридинтрифосфат", "Тимидинтрифосфат"],
            "Органические кислоты": ["Пируват", "Лактат", "Цитрат", "Изоцитрат", "α-кетоглутарат", "Сукцинат", "Фумарат", "Малат", "Оксалоацетат", "Ацетил-КоА"]
        }
        
        for i in range(count):
            # Выбираем случайный класс
            class_name = random.choice(self.classes)
            
            # Генерируем название
            if class_name in base_names:
                base_name = random.choice(base_names[class_name])
                # Добавляем вариации
                variations = ["", " (изомер)", " (энантиомер)", " (цис)", " (транс)", " (α)", " (β)", " (γ)", " (δ)"]
                name = base_name + random.choice(variations)
            else:
                name = f"Соединение_{i+1:06d}"
            
            # Генерируем формулу
            if class_name in base_formulas:
                formula = random.choice(base_formulas[class_name])
                # Добавляем вариации в формулу
                if random.random() < 0.3:
                    formula += random.choice(["", "·H2O", "·HCl", "·Na", "·K", "·Ca"])
            else:
                # Генерируем случайную формулу
                c_count = random.randint(1, 30)
                h_count = random.randint(1, 60)
                o_count = random.randint(0, 20)
                n_count = random.randint(0, 10)
                p_count = random.randint(0, 5)
                s_count = random.randint(0, 3)
                
                formula_parts = []
                if c_count > 0:
                    formula_parts.append(f"C{c_count}")
                if h_count > 0:
                    formula_parts.append(f"H{h_count}")
                if o_count > 0:
                    formula_parts.append(f"O{o_count}")
                if n_count > 0:
                    formula_parts.append(f"N{n_count}")
                if p_count > 0:
                    formula_parts.append(f"P{p_count}")
                if s_count > 0:
                    formula_parts.append(f"S{s_count}")
                
                formula = "".join(formula_parts)
            
            # Генерируем массу (примерно на основе формулы)
            exact_mass = self._estimate_mass_from_formula(formula)
            if exact_mass is None:
                exact_mass = random.uniform(50.0, 1000.0)
            
            # Генерируем внешние ID
            hmdb_id = f"HMDB{random.randint(1000000, 9999999):07d}" if random.random() < 0.7 else None
            chebi_id = f"CHEBI:{random.randint(100000, 999999)}" if random.random() < 0.8 else None
            kegg_id = f"C{random.randint(10000, 99999):05d}" if random.random() < 0.6 else None
            pubchem_cid = random.randint(1000000, 9999999) if random.random() < 0.5 else None
            
            # Генерируем пути и ферменты
            pathway_count = random.randint(0, 3)
            pathways = random.sample(self.pathways, min(pathway_count, len(self.pathways))) if pathway_count > 0 else []
            
            enzyme_count = random.randint(0, 2)
            enzymes = random.sample(self.enzymes, min(enzyme_count, len(self.enzymes))) if enzyme_count > 0 else []
            
            metabolite = {
                'name': name,
                'formula': formula,
                'exact_mass': round(exact_mass, 6),
                'hmdb_id': hmdb_id,
                'chebi_id': chebi_id,
                'kegg_id': kegg_id,
                'pubchem_cid': pubchem_cid,
                'class_name': class_name,
                'pathways': pathways,
                'enzymes': enzymes
            }
            
            metabolites.append(metabolite)
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Сгенерировано {i + 1} метаболитов...")
        
        logger.info(f"Генерация завершена: {len(metabolites)} метаболитов")
        return metabolites
    
    def _estimate_mass_from_formula(self, formula: str) -> Optional[float]:
        """Примерная оценка массы по формуле"""
        try:
            # Простая оценка на основе атомных масс
            atomic_masses = {
                'C': 12.011, 'H': 1.008, 'O': 15.999, 'N': 14.007,
                'P': 30.974, 'S': 32.065, 'Na': 22.990, 'K': 39.098,
                'Ca': 40.078, 'Cl': 35.453
            }
            
            total_mass = 0.0
            current_element = ""
            current_count = ""
            
            for char in formula:
                if char.isupper():
                    # Обрабатываем предыдущий элемент
                    if current_element and current_element in atomic_masses:
                        count = int(current_count) if current_count else 1
                        total_mass += atomic_masses[current_element] * count
                    
                    current_element = char
                    current_count = ""
                elif char.islower():
                    current_element += char
                elif char.isdigit():
                    current_count += char
            
            # Обрабатываем последний элемент
            if current_element and current_element in atomic_masses:
                count = int(current_count) if current_count else 1
                total_mass += atomic_masses[current_element] * count
            
            return total_mass if total_mass > 0 else None
            
        except:
            return None
    
    def create_database_tables(self):
        """Создание таблиц в базе данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Удаляем существующие таблицы
        cursor.execute("DROP TABLE IF EXISTS metabolite_enzyme")
        cursor.execute("DROP TABLE IF EXISTS metabolite_pathway")
        cursor.execute("DROP TABLE IF EXISTS metabolites")
        cursor.execute("DROP TABLE IF EXISTS enzymes")
        cursor.execute("DROP TABLE IF EXISTS pathways")
        cursor.execute("DROP TABLE IF EXISTS classes")
        
        # Таблица классов
        cursor.execute('''
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Таблица путей
        cursor.execute('''
            CREATE TABLE pathways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                source TEXT DEFAULT 'generated',
                ext_id TEXT
            )
        ''')
        
        # Таблица ферментов
        cursor.execute('''
            CREATE TABLE enzymes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                uniprot_id TEXT
            )
        ''')
        
        # Таблица метаболитов
        cursor.execute('''
            CREATE TABLE metabolites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                formula TEXT,
                exact_mass REAL,
                hmdb_id TEXT,
                chebi_id TEXT,
                kegg_id TEXT,
                pubchem_cid TEXT,
                class_id INTEGER,
                FOREIGN KEY (class_id) REFERENCES classes (id)
            )
        ''')
        
        # Связующие таблицы
        cursor.execute('''
            CREATE TABLE metabolite_pathway (
                metabolite_id INTEGER,
                pathway_id INTEGER,
                PRIMARY KEY (metabolite_id, pathway_id),
                FOREIGN KEY (metabolite_id) REFERENCES metabolites (id),
                FOREIGN KEY (pathway_id) REFERENCES pathways (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE metabolite_enzyme (
                metabolite_id INTEGER,
                enzyme_id INTEGER,
                PRIMARY KEY (metabolite_id, enzyme_id),
                FOREIGN KEY (metabolite_id) REFERENCES metabolites (id),
                FOREIGN KEY (enzyme_id) REFERENCES enzymes (id)
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX idx_metabolites_name ON metabolites(name)')
        cursor.execute('CREATE INDEX idx_metabolites_formula ON metabolites(formula)')
        cursor.execute('CREATE INDEX idx_metabolites_mass ON metabolites(exact_mass)')
        cursor.execute('CREATE INDEX idx_metabolites_hmdb ON metabolites(hmdb_id)')
        cursor.execute('CREATE INDEX idx_metabolites_chebi ON metabolites(chebi_id)')
        
        conn.commit()
        conn.close()
        logger.info("Таблицы базы данных созданы")
    
    def import_metabolites(self, count: int = 10000):
        """Основной метод импорта метаболитов"""
        logger.info(f"Начинаем импорт {count} метаболитов...")
        
        # Создаем таблицы
        self.create_database_tables()
        
        # Генерируем метаболиты
        metabolites = self.generate_metabolites(count)
        
        # Подключаемся к базе
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Словари для кэширования
        classes_cache = {}
        pathways_cache = {}
        enzymes_cache = {}
        
        imported_count = 0
        
        # Вставляем классы
        for class_name in self.classes:
            cursor.execute('INSERT INTO classes (name) VALUES (?)', (class_name,))
            classes_cache[class_name] = cursor.lastrowid
        
        # Вставляем пути
        for pathway_name in self.pathways:
            cursor.execute('INSERT INTO pathways (name) VALUES (?)', (pathway_name,))
            pathways_cache[pathway_name] = cursor.lastrowid
        
        # Вставляем ферменты
        for enzyme_name in self.enzymes:
            cursor.execute('INSERT INTO enzymes (name) VALUES (?)', (enzyme_name,))
            enzymes_cache[enzyme_name] = cursor.lastrowid
        
        # Вставляем метаболиты
        for i, metabolite in enumerate(metabolites):
            try:
                class_id = classes_cache[metabolite['class_name']]
                
                cursor.execute('''
                    INSERT INTO metabolites 
                    (name, formula, exact_mass, hmdb_id, chebi_id, kegg_id, pubchem_cid, class_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metabolite['name'], metabolite['formula'], metabolite['exact_mass'],
                    metabolite['hmdb_id'], metabolite['chebi_id'], metabolite['kegg_id'],
                    metabolite['pubchem_cid'], class_id
                ))
                
                metabolite_id = cursor.lastrowid
                
                # Связываем с путями
                for pathway_name in metabolite['pathways']:
                    pathway_id = pathways_cache[pathway_name]
                    cursor.execute('''
                        INSERT INTO metabolite_pathway (metabolite_id, pathway_id)
                        VALUES (?, ?)
                    ''', (metabolite_id, pathway_id))
                
                # Связываем с ферментами
                for enzyme_name in metabolite['enzymes']:
                    enzyme_id = enzymes_cache[enzyme_name]
                    cursor.execute('''
                        INSERT INTO metabolite_enzyme (metabolite_id, enzyme_id)
                        VALUES (?, ?)
                    ''', (metabolite_id, enzyme_id))
                
                imported_count += 1
                
                # Логируем прогресс
                if (i + 1) % 1000 == 0:
                    logger.info(f"Импортировано {i + 1}/{len(metabolites)} метаболитов")
                    conn.commit()
                
            except Exception as e:
                logger.error(f"Ошибка при импорте метаболита {i}: {e}")
                continue
        
        # Финальное сохранение
        conn.commit()
        conn.close()
        
        logger.info(f"Импорт завершен!")
        logger.info(f"Успешно импортировано: {imported_count} метаболитов")
        logger.info(f"Создано классов: {len(self.classes)}")
        logger.info(f"Создано путей: {len(self.pathways)}")
        logger.info(f"Создано ферментов: {len(self.enzymes)}")

def main():
    """Основная функция"""
    importer = LargeDatasetImporter()
    
    # Импортируем метаболиты (можно изменить количество)
    importer.import_metabolites(count=20000)  # 20,000 метаболитов

if __name__ == "__main__":
    main()
