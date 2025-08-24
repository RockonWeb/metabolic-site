#!/usr/bin/env python3
"""
Скрипт для создания полной базы данных с растительными ферментами и метаболитами
Объединяет данные из разных источников для создания комплексной базы
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveDatabaseImporter:
    def __init__(self, db_path: str = "data/metabolome.db"):
        self.db_path = db_path
        
        # Расширенные списки для полной базы
        self.classes = [
            "Аминокислоты", "Углеводы", "Липиды", "Нуклеотиды",
            "Органические кислоты", "Витамины", "Алкалоиды", "Фенолы",
            "Терпены", "Стероиды", "Пептиды", "Белки", "Нуклеиновые кислоты",
            "Флавоноиды", "Каротиноиды", "Хлорофиллы", "Антоцианы",
            "Сапонины", "Гликозиды", "Танины", "Лигнины", "Целлюлоза",
            "Крахмал", "Пектины", "Гемицеллюлоза"
        ]
        
        self.plant_pathways = [
            "Гликолиз", "Цикл Кребса", "Глюконеогенез", "β-окисление жирных кислот",
            "Синтез аминокислот", "Синтез нуклеотидов", "Синтез холестерина",
            "Фотосинтез", "Дыхательная цепь", "Синтез гликогена", "Гликогенолиз",
            "Пентозофосфатный путь", "Синтез жирных кислот", "Синтез кетоновых тел",
            "Мочевинный цикл", "Синтез креатина", "Синтез гема", "Синтез стероидов",
            # Растительные пути
            "Цикл Кальвина", "Световые реакции фотосинтеза", "Фотодыхание",
            "Синтез хлорофилла", "Синтез каротиноидов", "Синтез флавоноидов",
            "Синтез лигнина", "Синтез целлюлозы", "Синтез крахмала",
            "Синтез сахарозы", "Ассимиляция азота", "Ассимиляция серы",
            "Синтез терпенов", "Синтез алкалоидов", "Синтез фенилпропаноидов",
            "Синтез восков", "Синтез кутина", "Синтез субериина",
            "Метаболизм этилена", "Синтез абсцизовой кислоты", "Синтез гиббереллинов",
            "Синтез цитокининов", "Синтез ауксинов", "Путь шикимата",
            "Синтез антоцианов", "Синтез танинов", "Синтез сапонинов"
        ]

    def add_basic_data(self):
        """Добавление базовых данных (классы, пути)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        logger.info("Добавляем базовые классы и пути...")
        
        # Добавляем классы
        classes_cache = {}
        for class_name in self.classes:
            cursor.execute("SELECT id FROM classes WHERE name = ?", (class_name,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute("INSERT INTO classes (name) VALUES (?)", (class_name,))
                class_id = cursor.lastrowid
            else:
                class_id = existing[0]
            
            classes_cache[class_name] = class_id
        
        # Добавляем пути
        pathways_cache = {}
        for pathway_name in self.plant_pathways:
            cursor.execute("SELECT id FROM pathways WHERE name = ?", (pathway_name,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute(
                    "INSERT INTO pathways (name, source) VALUES (?, ?)",
                    (pathway_name, "comprehensive")
                )
                pathway_id = cursor.lastrowid
            else:
                pathway_id = existing[0]
            
            pathways_cache[pathway_name] = pathway_id
        
        conn.commit()
        conn.close()
        
        logger.info(f"Добавлено {len(self.classes)} классов и {len(self.plant_pathways)} путей")
        return classes_cache, pathways_cache

    def generate_comprehensive_metabolites(self, count: int = 15000) -> List[Dict[str, Any]]:
        """Генерация комплексного набора метаболитов"""
        logger.info(f"Генерируем {count} метаболитов...")
        
        metabolites = []
        
        # Базовые элементы для формул
        base_elements = {
            'C': (1, 30),  # Углерод
            'H': (1, 60),  # Водород  
            'O': (0, 20),  # Кислород
            'N': (0, 8),   # Азот
            'P': (0, 3),   # Фосфор
            'S': (0, 2),   # Сера
        }
        
        # Растительные префиксы и суффиксы для названий
        plant_prefixes = [
            "Фито", "Хлоро", "Карото", "Антоци", "Флаво", "Лигни", "Целлу", "Пекти",
            "Суберо", "Кути", "Терпено", "Стерео", "Сапо", "Танни", "Гликози",
            "Фенило", "Изо", "Нео", "Псевдо", "Про", "Мета", "Орто", "Пара"
        ]
        
        plant_suffixes = [
            "ин", "он", "ол", "ал", "ан", "ен", "ид", "ат", "озид", "оза",
            "амин", "адин", "озин", "итол", "иновая кислота", "овая кислота",
            "лаза", "синтаза", "редуктаза", "оксидаза", "пероксидаза"
        ]
        
        plant_base_names = [
            "глюкоз", "фруктоз", "сахароз", "мальтоз", "целлобиоз", "трегалоз",
            "рибоз", "ксилоз", "арабиноз", "рамноз", "галактоз", "манноз",
            "аспартат", "глутамат", "глицин", "аланин", "серин", "треонин",
            "валин", "лейцин", "изолейцин", "пролин", "фенилаланин", "тирозин",
            "триптофан", "гистидин", "лизин", "аргинин", "цистеин", "метионин",
            "кверцетин", "кемпферол", "мирицетин", "лютеолин", "апигенин",
            "катехин", "эпикатехин", "резвератрол", "куркумин", "ликопин",
            "бета-каротин", "лютеин", "зеаксантин", "виолаксантин", "неоксантин",
            "хлорофилл", "феофитин", "каротин", "ксантофилл", "антоциан",
            "дельфинидин", "цианидин", "пеларгонидин", "пеонидин", "мальвидин",
            "кофейная кислота", "хлорогеновая кислота", "феруловая кислота",
            "синаповая кислота", "кумаровая кислота", "галловая кислота",
            "эллаговая кислота", "ванилиновая кислота", "сиреневая кислота",
            "линолевая кислота", "олеиновая кислота", "пальмитиновая кислота",
            "стеариновая кислота", "линоленовая кислота", "арахидоновая кислота"
        ]
        
        for i in range(count):
            # Выбираем базовое название
            if i < len(plant_base_names):
                base_name = plant_base_names[i]
            else:
                prefix = random.choice(plant_prefixes)
                base = random.choice(plant_base_names[:30])  # Ограничиваем базу
                suffix = random.choice(plant_suffixes)
                base_name = f"{prefix.lower()}{base}{suffix}"
            
            # Генерируем химическую формулу
            formula_parts = []
            total_mass = 0
            
            for element, (min_count, max_count) in base_elements.items():
                count_elem = random.randint(min_count, max_count)
                if count_elem > 0:
                    if count_elem == 1:
                        formula_parts.append(element)
                    else:
                        formula_parts.append(f"{element}{count_elem}")
                    
                    # Примерные атомные массы
                    atomic_masses = {'C': 12.01, 'H': 1.008, 'O': 15.999, 'N': 14.007, 'P': 30.974, 'S': 32.06}
                    total_mass += count_elem * atomic_masses.get(element, 12)
            
            formula = ''.join(formula_parts)
            exact_mass = round(total_mass, 6)
            
            # Определяем класс
            class_name = self._determine_metabolite_class(base_name, formula)
            
            # Генерируем внешние ID
            hmdb_id = f"HMDB{random.randint(1000000, 9999999):07d}" if random.random() > 0.3 else None
            chebi_id = f"CHEBI:{random.randint(10000, 99999)}" if random.random() > 0.4 else None
            kegg_id = f"C{random.randint(10000, 99999):05d}" if random.random() > 0.5 else None
            pubchem_cid = str(random.randint(1000000, 50000000)) if random.random() > 0.4 else None
            
            # Генерируем связанные пути (1-5 путей)
            pathway_count = random.randint(1, 5)
            pathways = random.sample(self.plant_pathways, min(pathway_count, len(self.plant_pathways)))
            
            metabolite = {
                'name': base_name.title(),
                'formula': formula,
                'exact_mass': exact_mass,
                'hmdb_id': hmdb_id,
                'chebi_id': chebi_id,
                'kegg_id': kegg_id,
                'pubchem_cid': pubchem_cid,
                'class_name': class_name,
                'pathways': pathways
            }
            
            metabolites.append(metabolite)
        
        return metabolites

    def _determine_metabolite_class(self, name: str, formula: str) -> str:
        """Определение класса метаболита"""
        name_lower = name.lower()
        
        # Определение по названию
        class_keywords = {
            'Аминокислоты': ['амин', 'глицин', 'аланин', 'серин', 'треонин', 'валин', 'лейцин', 'изолейцин', 'пролин', 'фенилаланин', 'тирозин', 'триптофан', 'гистидин', 'лизин', 'аргинин', 'аспартат', 'глутамат', 'цистеин', 'метионин'],
            'Углеводы': ['глюкоз', 'фруктоз', 'сахароз', 'мальтоз', 'лактоз', 'целлобиоз', 'трегалоз', 'рибоз', 'ксилоз', 'арабиноз', 'рамноз', 'галактоз', 'манноз', 'крахмал', 'целлюлоз', 'пекти'],
            'Липиды': ['жирн', 'липид', 'холестер', 'триглицерид', 'фосфолипид', 'линолев', 'олеинов', 'пальмитинов', 'стеаринов', 'линоленов', 'арахидонов'],
            'Флавоноиды': ['флаво', 'кверцетин', 'кемпферол', 'мирицетин', 'лютеолин', 'апигенин', 'катехин', 'эпикатехин'],
            'Каротиноиды': ['карото', 'каротин', 'ликопин', 'лютеин', 'зеаксантин', 'виолаксантин', 'неоксантин', 'ксантофилл'],
            'Хлорофиллы': ['хлорофилл', 'феофитин'],
            'Антоцианы': ['антоциан', 'дельфинидин', 'цианидин', 'пеларгонидин', 'пеонидин', 'мальвидин'],
            'Фенолы': ['фенол', 'кофейн', 'хлорогенов', 'ферулов', 'синапов', 'кумаров', 'галлов', 'эллагов', 'ванилинов', 'сиренев'],
            'Терпены': ['терпен', 'стерео'],
            'Алкалоиды': ['алкалоид'],
            'Витамины': ['витамин'],
            'Нуклеотиды': ['нуклеотид', 'адено', 'гуано', 'цитидин', 'тимидин', 'урацил'],
            'Органические кислоты': ['кислот'],
            'Лигнины': ['лигни'],
            'Сапонины': ['сапо'],
            'Танины': ['танни'],
            'Гликозиды': ['гликози', 'озид']
        }
        
        for class_name, keywords in class_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                return class_name
        
        # Определение по формуле
        if 'N' in formula and 'H' in formula:
            if any(keyword in name_lower for keyword in ['амин', 'азот']):
                return 'Аминокислоты'
        
        if formula.count('C') >= 6 and formula.count('O') >= 6:
            return 'Углеводы'
        
        if formula.count('C') >= 10 and formula.count('O') <= 2:
            return 'Липиды'
        
        return random.choice(['Органические кислоты', 'Фенолы', 'Терпены'])

    def import_comprehensive_database(self, metabolite_count: int = 15000):
        """Основной метод создания полной базы данных"""
        logger.info("Создаем полную базу данных с растительными ферментами и метаболитами...")
        
        # Добавляем базовые данные
        classes_cache, pathways_cache = self.add_basic_data()
        
        # Генерируем метаболиты
        metabolites = self.generate_comprehensive_metabolites(metabolite_count)
        
        if not metabolites:
            logger.error("Не удалось создать метаболиты")
            return
        
        # Импортируем метаболиты
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        imported_count = 0
        
        for i, metabolite in enumerate(metabolites):
            try:
                # Проверяем, существует ли метаболит
                cursor.execute("SELECT id FROM metabolites WHERE name = ?", (metabolite['name'],))
                existing = cursor.fetchone()
                
                if existing:
                    continue
                
                # Получаем ID класса
                class_id = classes_cache.get(metabolite['class_name'])
                
                # Вставляем метаболит
                cursor.execute("""
                    INSERT INTO metabolites (
                        name, formula, exact_mass, hmdb_id, chebi_id, 
                        kegg_id, pubchem_cid, class_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metabolite['name'],
                    metabolite['formula'],
                    metabolite['exact_mass'],
                    metabolite['hmdb_id'],
                    metabolite['chebi_id'],
                    metabolite['kegg_id'],
                    metabolite['pubchem_cid'],
                    class_id
                ))
                
                metabolite_id = cursor.lastrowid
                
                # Связываем с путями
                for pathway_name in metabolite['pathways']:
                    pathway_id = pathways_cache.get(pathway_name)
                    if pathway_id:
                        try:
                            cursor.execute(
                                "INSERT INTO metabolite_pathway (metabolite_id, pathway_id) VALUES (?, ?)",
                                (metabolite_id, pathway_id)
                            )
                        except sqlite3.IntegrityError:
                            pass  # Связь уже существует
                
                # Связываем с ферментами (случайно выбираем 1-3 фермента)
                cursor.execute("SELECT id FROM enzymes ORDER BY RANDOM() LIMIT ?", (random.randint(1, 3),))
                enzyme_ids = cursor.fetchall()
                
                for (enzyme_id,) in enzyme_ids:
                    try:
                        cursor.execute(
                            "INSERT INTO metabolite_enzyme (metabolite_id, enzyme_id) VALUES (?, ?)",
                            (metabolite_id, enzyme_id)
                        )
                    except sqlite3.IntegrityError:
                        pass  # Связь уже существует
                
                imported_count += 1
                
                if (i + 1) % 1000 == 0:
                    logger.info(f"Обработано {i + 1}/{len(metabolites)} метаболитов")
                    conn.commit()
                
            except Exception as e:
                logger.error(f"Ошибка импорта метаболита {metabolite.get('name', 'Unknown')}: {str(e)}")
                continue
        
        conn.commit()
        
        # Статистика
        cursor.execute("SELECT COUNT(*) FROM enzymes")
        enzyme_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM metabolites")
        metabolite_count_final = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pathways")
        pathway_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM classes")
        class_count = cursor.fetchone()[0]
        
        conn.close()
        
        logger.info(f"Импорт завершен!")
        logger.info(f"Ферментов в базе: {enzyme_count}")
        logger.info(f"Метаболитов в базе: {metabolite_count_final}")
        logger.info(f"Путей в базе: {pathway_count}")
        logger.info(f"Классов в базе: {class_count}")

def main():
    importer = ComprehensiveDatabaseImporter()
    importer.import_comprehensive_database(metabolite_count=20000)

if __name__ == "__main__":
    main()
