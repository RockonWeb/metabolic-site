import streamlit as st
import pandas as pd
import sqlite3
import io
from typing import List, Dict, Any, Optional
import math
import plotly.express as px
import plotly.graph_objects as go
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------
# Вспомогательные стили/утилиты UI
# -------------------------

def truncate_description(text: str, max_words: int = 6) -> str:
    """Обрезает описание до указанного количества слов"""
    if not text or text == 'None':
        return text
    
    words = text.split()
    if len(words) <= max_words:
        return text
    
    truncated = ' '.join(words[:max_words])
    return truncated + '...'

def _inject_base_css() -> None:
    """Добавляет базовые CSS-стили для карточек, шапки-метрик и таблиц."""
    st.markdown(
        """
        <style>
        /* Карточки результатов */
        .card {
            background: #262730;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 6px 18px rgba(0,0,0,0.3);
            padding: 18px 18px 16px 18px;
            margin-bottom: 12px;
            min-height: 120px;
            display: flex;
            flex-direction: column;
        }
        .card-title {
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 8px 0;
            color: #FAFAFA;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: auto;
            line-height: 1.3;
            max-height: 4.5em;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
        }
        .card-subtitle { 
            font-size: 14px; 
            color: #B0B0B0; 
            margin-bottom: 12px; 
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.4;
            white-space: pre-line;
        }
        .pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #f1f5f9;
            color: #0f172a;
            font-size: 13px;
            border: 1px solid #e2e8f0;
            margin-right: 8px;
            margin-bottom: 8px;
        }
        .row-divider { height: 8px; }
        .ext-link a { text-decoration: none; font-size: 14px; }
        .ext-link a:hover { text-decoration: underline; }
        
        /* Стили для улучшения UX поиска */
        .search-input {
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            transition: border-color 0.3s ease;
        }
        
        .search-input:focus {
            border-color: #7C3AED;
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }
        
        .search-hint {
            color: #6B7280;
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }
        
        /* Стили для кликабельных карточек */
        .clickable-card {
            transition: all 0.3s ease;
            position: relative;
        }
        
        .clickable-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            border-color: #7C3AED;
        }
        
        .clickable-card:active {
            transform: translateY(0);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .card-hint {
            color: #7C3AED;
            font-size: 12px;
            font-style: italic;
            margin-top: 8px;
            text-align: center;
            opacity: 0.8;
        }
        
        .clickable-card:hover .card-hint {
            opacity: 1;
            color: #6D28D9;
        }
        
        /* Стили для ссылок деталей */
        .card-hint a {
            color: #7C3AED !important;
            text-decoration: none !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        
        .card-hint a:hover {
            color: #6D28D9 !important;
            text-decoration: underline !important;
        }
        
        /* Стили для химических формул */
        .formula {
            font-family: 'Times New Roman', serif;
            font-style: normal;
        }
        
        .formula .subscript {
            font-size: 0.7em;
            vertical-align: sub;
            font-weight: normal;
        }
        
        .formula .superscript {
            font-size: 0.7em;
            vertical-align: super;
            font-weight: normal;
        }
        

        </style>
        

        """,
        unsafe_allow_html=True,
    )

# Конфигурация баз данных
METABOLITES_DB_PATH = os.getenv("METABOLITES_DB_PATH", "data/metabolites.db")
ENZYMES_DB_PATH = os.getenv("ENZYMES_DB_PATH", "data/enzymes.db")
PROTEINS_DB_PATH = os.getenv("PROTEINS_DB_PATH", "data/proteins.db")
CARBOHYDRATES_DB_PATH = os.getenv("CARBOHYDRATES_DB_PATH", "data/carbohydrates.db")
LIPIDS_DB_PATH = os.getenv("LIPIDS_DB_PATH", "data/lipids.db")

def format_chemical_formula(formula: str) -> str:
    """Преобразует химическую формулу в HTML с правильными индексами"""
    if not formula or formula == "—" or formula == "None":
        return formula
    
    # Заменяем цифры на подстрочные индексы
    import re
    
    # Обрабатываем заряды (например, Ca2+, Fe3+)
    formula = re.sub(r'(\d+)\+', r'<span class="superscript">\1+</span>', formula)
    
    # Обрабатываем обычные индексы (например, H2O, CO2)
    formula = re.sub(r'(\d+)', r'<span class="subscript">\1</span>', formula)
    
    # Обрабатываем отрицательные заряды (например, SO4^2-)
    formula = re.sub(r'\^(\d+)-', r'<span class="superscript">\1-</span>', formula)
    
    return f'<span class="formula">{formula}</span>'

# Отладочная информация
#logger.info(f"Текущая рабочая директория: {os.getcwd()}")
#logger.info(f"Путь к базе метаболитов: {os.path.abspath(METABOLITES_DB_PATH)}")
#logger.info(f"Путь к базе ферментов: {os.path.abspath(ENZYMES_DB_PATH)}")
#logger.info(f"Путь к базе белков: {os.path.abspath(PROTEINS_DB_PATH)}")

def _get_metabolites_connection():
    """Создает подключение к базе данных метаболитов"""
    try:
        #logger.info(f"Проверяем существование файла: {METABOLITES_DB_PATH}")
        if not os.path.exists(METABOLITES_DB_PATH):
            logger.error(f"Файл не найден: {METABOLITES_DB_PATH}")
            return None
        #logger.info(f"Подключаемся к базе метаболитов: {METABOLITES_DB_PATH}")
        conn = sqlite3.connect(METABOLITES_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Проверяем, что таблица существует
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metabolites'")
        if cursor.fetchone() is None:
            logger.error("Таблица 'metabolites' не найдена в базе данных")
            conn.close()
            return None
        #logger.info("Подключение к базе метаболитов успешно")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе метаболитов: {e}")
        return None

def _get_enzymes_connection():
    """Создает подключение к базе данных ферментов"""
    try:
        #logger.info(f"Проверяем существование файла: {ENZYMES_DB_PATH}")
        if not os.path.exists(ENZYMES_DB_PATH):
            logger.error(f"Файл не найден: {ENZYMES_DB_PATH}")
            return None
        #logger.info(f"Подключаемся к базе ферментов: {ENZYMES_DB_PATH}")
        conn = sqlite3.connect(ENZYMES_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Проверяем, что таблица существует
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='enzymes'")
        if cursor.fetchone() is None:
            logger.error("Таблица 'enzymes' не найдена в базе данных")
            conn.close()
            return None
        #logger.info("Подключение к базе ферментов успешно")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе ферментов: {e}")
        return None

def _get_proteins_connection():
    """Создает подключение к базе данных белков"""
    try:
        #logger.info(f"Проверяем существование файла: {PROTEINS_DB_PATH}")
        if not os.path.exists(PROTEINS_DB_PATH):
            logger.error(f"Файл не найден: {PROTEINS_DB_PATH}")
            return None
        #logger.info(f"Подключаемся к базе белков: {PROTEINS_DB_PATH}")
        conn = sqlite3.connect(PROTEINS_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Проверяем, что таблица существует
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proteins'")
        if cursor.fetchone() is None:
            logger.error("Таблица 'proteins' не найдена в базе данных")
            conn.close()
            return None
        #logger.info("Подключение к базе белков успешно")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе белков: {e}")
        return None

def _get_carbohydrates_connection():
    """Создает подключение к базе данных углеводов"""
    try:
        if not os.path.exists(CARBOHYDRATES_DB_PATH):
            logger.error(f"Файл не найден: {CARBOHYDRATES_DB_PATH}")
            return None
        conn = sqlite3.connect(CARBOHYDRATES_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Проверяем, что таблица существует
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='carbohydrates'")
        if cursor.fetchone() is None:
            logger.error("Таблица 'carbohydrates' не найдена в базе данных")
            conn.close()
            return None
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе углеводов: {e}")
        return None

def _get_lipids_connection():
    """Создает подключение к базе данных липидов"""
    try:
        if not os.path.exists(LIPIDS_DB_PATH):
            logger.error(f"Файл не найден: {LIPIDS_DB_PATH}")
            return None
        conn = sqlite3.connect(LIPIDS_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Проверяем, что таблица существует
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lipids'")
        if cursor.fetchone() is None:
            logger.error("Таблица 'lipids' не найдена в базе данных")
            conn.close()
            return None
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе липидов: {e}")
        return None

def _get_totals() -> Dict[str, Any]:
    """Возвращает агрегированные счетчики для шапки"""
    totals = {"metabolites": 0, "enzymes": 0, "proteins": 0, "carbohydrates": 0, "lipids": 0, "db_status": "unknown"}
    
    # Подсчет метаболитов
    #logger.info("Получаем подключение к базе метаболитов для подсчета")
    conn_met = None
    try:
        conn_met = _get_metabolites_connection()
        if conn_met:
            cursor = conn_met.execute("SELECT COUNT(*) FROM metabolites")
            totals["metabolites"] = cursor.fetchone()[0]
            #logger.info(f"Найдено метаболитов: {totals['metabolites']}")
        else:
            logger.error("Не удалось получить подключение к базе метаболитов")
    except Exception as e:
        logger.error(f"Ошибка при подсчете метаболитов: {e}")
    finally:
        if conn_met:
            conn_met.close()
    
    # Подсчет ферментов
    #logger.info("Получаем подключение к базе ферментов для подсчета")
    conn_enz = None
    try:
        conn_enz = _get_enzymes_connection()
        if conn_enz:
            cursor = conn_enz.execute("SELECT COUNT(*) FROM enzymes")
            totals["enzymes"] = cursor.fetchone()[0]
            #logger.info(f"Найдено ферментов: {totals['enzymes']}")
        else:
            logger.error("Не удалось получить подключение к базе ферментов")
    except Exception as e:
        logger.error(f"Ошибка при подсчете ферментов: {e}")
    finally:
        if conn_enz:
            conn_enz.close()
    
    # Подсчет белков
    #logger.info("Получаем подключение к базе белков для подсчета")
    conn_prot = None
    try:
        conn_prot = _get_proteins_connection()
        if conn_prot:
            cursor = conn_prot.execute("SELECT COUNT(*) FROM proteins")
            totals["proteins"] = cursor.fetchone()[0]
            #logger.info(f"Найдено белков: {totals['proteins']}")
        else:
            logger.error("Не удалось получить подключение к базе белков")
    except Exception as e:
        logger.error(f"Ошибка при подсчете белков: {e}")
    finally:
        if conn_prot:
            conn_prot.close()
    
    # Подсчет углеводов
    conn_carb = None
    try:
        conn_carb = _get_carbohydrates_connection()
        if conn_carb:
            cursor = conn_carb.execute("SELECT COUNT(*) FROM carbohydrates")
            totals["carbohydrates"] = cursor.fetchone()[0]
        else:
            logger.error("Не удалось получить подключение к базе углеводов")
    except Exception as e:
        logger.error(f"Ошибка при подсчете углеводов: {e}")
    finally:
        if conn_carb:
            conn_carb.close()
    
    # Подсчет липидов
    conn_lip = None
    try:
        conn_lip = _get_lipids_connection()
        if conn_lip:
            cursor = conn_lip.execute("SELECT COUNT(*) FROM lipids")
            totals["lipids"] = cursor.fetchone()[0]
        else:
            logger.error("Не удалось получить подключение к базе липидов")
    except Exception as e:
        logger.error(f"Ошибка при подсчете липидов: {e}")
    finally:
        if conn_lip:
            conn_lip.close()
    
    # Определяем статус
    if totals["metabolites"] > 0 or totals["enzymes"] > 0 or totals["proteins"] > 0 or totals["carbohydrates"] > 0 or totals["lipids"] > 0:
        totals["db_status"] = "healthy"
        #logger.info("Статус БД: healthy")
    else:
        totals["db_status"] = "offline"
        logger.error("Статус БД: offline - нет данных в базах")
    
    return totals

def _render_metabolite_card(m: Dict[str, Any]) -> None:
    """Карточка метаболита с ссылками и кнопкой деталей"""
    # Приоритет русскому названию, если оно есть
    name = m.get("name_ru") or m.get("name") or "Без названия"
    formula = m.get("formula") or "—"
    mass = m.get("exact_mass")
    mass_fmt = f"{mass:.6f} Da" if isinstance(mass, (int, float)) else "—"
    cls = m.get("class_name") or "—"
    
    # Убираем None значения
    if name == "None":
        name = "Без названия"
    if formula == "None":
        formula = "—"
    if cls == "None":
        cls = "—"

    # Ссылки на внешние ресурсы
    links = []
    if m.get("hmdb_id"):
        links.append(f"<span class='ext-link'><a href='https://hmdb.ca/metabolites/{m['hmdb_id']}' target='_blank'>HMDB</a></span>")
    if m.get("kegg_id"):
        links.append(f"<span class='ext-link'><a href='https://www.kegg.jp/entry/{m['kegg_id']}' target='_blank'>KEGG</a></span>")
    if m.get("chebi_id"):
        links.append(f"<span class='ext-link'><a href='https://www.ebi.ac.uk/chebi/searchId.do?chebiId={m['chebi_id']}' target='_blank'>ChEBI</a></span>")
    if m.get("pubchem_cid"):
        links.append(f"<span class='ext-link'><a href='https://pubchem.ncbi.nlm.nih.gov/compound/{m['pubchem_cid']}' target='_blank'>PubChem</a></span>")
    links_html = " &middot; ".join(links) if links else ""

    pills = []
    if cls and cls != "—":
        pills.append(f"<span class='pill'>{cls}</span>")
    pills_html = " ".join(pills)

    # Создаем уникальный ключ для карточки
    card_key = f"met_card_{m.get('id', hash(name))}"

    # Форматируем формулу с правильными индексами
    formatted_formula = format_chemical_formula(formula)
    
    # Создаем карточку с кнопкой
    st.markdown(
        f"""
        <div class="card clickable-card" style="cursor: pointer;">
          <div class="card-title">{name}</div>
          <div class="card-subtitle">Формула: <b>{formatted_formula}</b><br>Масса: <b>{mass_fmt}</b></div>
          <div>{pills_html}</div>
          <div class="row-divider"></div>
          <div>{links_html}</div>

        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Кнопка для открытия деталей
    if st.button("📋 Показать детали", key=card_key, use_container_width=True):
        st.session_state.selected_metabolite = m
        st.session_state.show_metabolite_details = True
        st.rerun()

def _render_enzyme_card(e: Dict[str, Any]) -> None:
    """Карточка фермента с ссылками и кнопкой деталей"""
    # Приоритет русскому названию, если оно есть
    name = e.get("name_ru") or e.get("name") or "Без названия"
    ec = e.get("ec_number") or "—"
    org = e.get("organism") or "—"
    fam = e.get("family") or "—"
    
    # Убираем None значения
    if name == "None":
        name = "Без названия"
    if ec == "None":
        ec = "—"
    if org == "None":
        org = "—"
    if fam == "None":
        fam = "—"
    
    # Ссылки на внешние ресурсы
    links = []
    if e.get("uniprot_id"):
        links.append(f"<span class='ext-link'><a href='https://www.uniprot.org/uniprot/{e['uniprot_id']}' target='_blank'>UniProt</a></span>")
    if e.get("kegg_enzyme_id"):
        links.append(f"<span class='ext-link'><a href='https://www.kegg.jp/entry/{e['kegg_enzyme_id']}' target='_blank'>KEGG</a></span>")
    if ec and ec != "—":
        links.append(f"<span class='ext-link'><a href='https://enzyme.expasy.org/EC/{ec}' target='_blank'>ExPASy</a></span>")
    links_html = " &middot; ".join(links) if links else ""
    
    props = []
    if ec != "—":
        props.append(f"EC: <b>{ec}</b>")
    if org != "—":
        props.append(f"Организм: <b>{org}</b>")
    if fam != "—":
        props.append(f"Семейство: <b>{fam}</b>")
    subtitle = "<br>".join(props)
    
    # Создаем уникальный ключ для карточки
    card_key = f"enz_card_{e.get('id', hash(name))}"
    
    # Создаем карточку с кнопкой
    st.markdown(
        f"""
        <div class="card clickable-card" style="cursor: pointer;">
          <div class="card-title">{name}</div>
          <div class="card-subtitle">{subtitle}</div>
          <div class="row-divider"></div>
          <div>{links_html}</div>

        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Кнопка для открытия деталей
    if st.button("📋 Показать детали", key=card_key, use_container_width=True):
        st.session_state.selected_enzyme = e
        st.session_state.show_enzyme_details = True
        st.rerun()

def _render_protein_card(p: Dict[str, Any]) -> None:
    """Карточка белка с ссылками и кнопкой деталей"""
    # Приоритет русскому названию, если оно есть
    name = p.get("name_ru") or p.get("name") or "Без названия"
    func = p.get("function") or "—"
    org = p.get("organism") or "—"
    fam = p.get("family") or "—"
    
    # Убираем None значения
    if name == "None":
        name = "Без названия"
    if func == "None":
        func = "—"
    if org == "None":
        org = "—"
    if fam == "None":
        fam = "—"
    
    # Ссылки на внешние ресурсы
    links = []
    if p.get("uniprot_id"):
        links.append(f"<span class='ext-link'><a href='https://www.uniprot.org/uniprot/{p['uniprot_id']}' target='_blank'>UniProt</a></span>")
    if p.get("pdb_id"):
        links.append(f"<span class='ext-link'><a href='https://www.rcsb.org/structure/{p['pdb_id']}' target='_blank'>PDB</a></span>")
    if p.get("gene_name"):
        links.append(f"<span class='ext-link'><a href='https://www.ncbi.nlm.nih.gov/gene/?term={p['gene_name']}' target='_blank'>NCBI Gene</a></span>")
    links_html = " &middot; ".join(links) if links else ""
    
    props = []
    if func != "—":
        truncated_func = truncate_description(func)
        props.append(f"Функция: <b>{truncated_func}</b>")
    if org != "—":
        props.append(f"Организм: <b>{org}</b>")
    if fam != "—":
        props.append(f"Семейство: <b>{fam}</b>")
    subtitle = "<br>".join(props)
    
    # Создаем уникальный ключ для карточки
    card_key = f"prot_card_{p.get('id', hash(name))}"
    
    # Создаем карточку с кнопкой
    st.markdown(
        f"""
        <div class="card clickable-card" style="cursor: pointer;">
          <div class="card-title">{name}</div>
          <div class="card-subtitle">{subtitle}</div>
          <div class="row-divider"></div>
          <div>{links_html}</div>

        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Кнопка для открытия деталей
    if st.button("📋 Показать детали", key=card_key, use_container_width=True):
        st.session_state.selected_protein = p
        st.session_state.show_protein_details = True
        st.rerun()

def _show_metabolite_details(metabolite: Dict[str, Any]) -> None:
    """Показывает детальную информацию о метаболите"""
    #st.markdown("---")
    # В заголовке используем русское название, если оно есть
    display_name = metabolite.get('name_ru') or metabolite.get('name') or 'Метаболит'
    st.subheader(f"🧬 {display_name}")
    
    # Основная информация в карточках
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Основная информация")
        with st.container():
            # Форматируем формулу для деталей
            detail_formula = format_chemical_formula(metabolite.get('formula') or 'Не указано')
            st.markdown(f"""
            **Название (EN):** {metabolite.get('name') or 'Не указано'}  
            **Название (RU):** {metabolite.get('name_ru') or 'Не указано'}  
            **Формула:** {detail_formula}  
            **Класс:** {metabolite.get('class_name') or 'Не указано'}
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### ⚖️ Физико-химические свойства")
        with st.container():
            mass = metabolite.get('exact_mass')
            mass_str = f"{mass:.6f} Da" if isinstance(mass, (int, float)) else 'Не указано'
            # Форматируем формулу для второй части деталей
            detail_formula2 = format_chemical_formula(metabolite.get('formula') or 'Не указано')
            st.markdown(f"""
            **Масса:** {mass_str}  
            **Молекулярная формула:** {detail_formula2}
            """, unsafe_allow_html=True)
    
    # Внешние идентификаторы
    st.markdown("### 🔗 Внешние идентификаторы")
    id_col1, id_col2, id_col3, id_col4 = st.columns(4)
    
    with id_col1:
        hmdb_id = metabolite.get('hmdb_id')
        if hmdb_id and hmdb_id != 'None':
            st.markdown(f"**HMDB:** [{hmdb_id}](https://hmdb.ca/metabolites/{hmdb_id})")
        else:
            st.markdown("**HMDB:** Не указано")
    
    with id_col2:
        kegg_id = metabolite.get('kegg_id')
        if kegg_id and kegg_id != 'None':
            st.markdown(f"**KEGG:** [{kegg_id}](https://www.kegg.jp/entry/{kegg_id})")
        else:
            st.markdown("**KEGG:** Не указано")
    
    with id_col3:
        chebi_id = metabolite.get('chebi_id')
        if chebi_id and chebi_id != 'None':
            st.markdown(f"**ChEBI:** [{chebi_id}](https://www.ebi.ac.uk/chebi/searchId.do?chebiId={chebi_id})")
        else:
            st.markdown("**ChEBI:** Не указано")
    
    with id_col4:
        pubchem_id = metabolite.get('pubchem_cid')
        if pubchem_id and pubchem_id != 'None':
            st.markdown(f"**PubChem:** [{pubchem_id}](https://pubchem.ncbi.nlm.nih.gov/compound/{pubchem_id})")
        else:
            st.markdown("**PubChem:** Не указано")
    
    # Описание
    description = metabolite.get('description')
    if description and description != 'None':
        st.markdown("### 📝 Описание")
        st.info(description)
    
    st.markdown("---")

def _show_enzyme_details(enzyme: Dict[str, Any]) -> None:
    """Показывает детальную информацию о ферменте"""
    #st.markdown("---")
    # В заголовке используем русское название, если оно есть
    display_name = enzyme.get('name_ru') or enzyme.get('name') or 'Фермент'
    st.subheader(f"🧪 {display_name}")
    
    # Основная информация
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Основная информация")
        with st.container():
            st.markdown(f"""
            **Название (EN):** {enzyme.get('name') or 'Не указано'}  
            **Название (RU):** {enzyme.get('name_ru') or 'Не указано'}  
            **EC номер:** `{enzyme.get('ec_number') or 'Не указано'}`  
            **Семейство:** {enzyme.get('family') or 'Не указано'}  
            **Организм:** {enzyme.get('organism') or 'Не указано'}  
            **Тип организма:** {enzyme.get('organism_type') or 'Не указано'}
            """)
    
    with col2:
        st.markdown("### 🧬 Генетическая информация")
        with st.container():
            st.markdown(f"""
            **Белок:** {enzyme.get('protein_name') or 'Не указано'}  
            **Ген:** {enzyme.get('gene_name') or 'Не указано'}  
            **Локализация:** {enzyme.get('subcellular_location') or 'Не указано'}
            """)
    
    # Биохимические свойства
    st.markdown("### ⚗️ Биохимические свойства")
    bio_col1, bio_col2, bio_col3 = st.columns(3)
    
    with bio_col1:
        mol_weight = enzyme.get('molecular_weight')
        if mol_weight and mol_weight != 'None':
            st.metric("Молекулярная масса", f"{mol_weight:.1f} kDa")
        else:
            st.metric("Молекулярная масса", "Не указано")
    
    with bio_col2:
        opt_ph = enzyme.get('optimal_ph')
        if opt_ph and opt_ph != 'None':
            st.metric("Оптимальный pH", str(opt_ph))
        else:
            st.metric("Оптимальный pH", "Не указано")
    
    with bio_col3:
        opt_temp = enzyme.get('optimal_temperature')
        if opt_temp and opt_temp != 'None':
            st.metric("Оптимальная температура", f"{opt_temp}°C")
        else:
            st.metric("Оптимальная температура", "Не указано")
    
    # Внешние идентификаторы
    st.markdown("### 🔗 Внешние идентификаторы")
    id_col1, id_col2, id_col3 = st.columns(3)
    
    with id_col1:
        uniprot_id = enzyme.get('uniprot_id')
        if uniprot_id and uniprot_id != 'None':
            st.markdown(f"**UniProt:** [{uniprot_id}](https://www.uniprot.org/uniprot/{uniprot_id})")
        else:
            st.markdown("**UniProt:** Не указано")
    
    with id_col2:
        kegg_id = enzyme.get('kegg_enzyme_id')
        if kegg_id and kegg_id != 'None':
            st.markdown(f"**KEGG:** [{kegg_id}](https://www.kegg.jp/entry/{kegg_id})")
        else:
            st.markdown("**KEGG:** Не указано")
    
    with id_col3:
        ec_number = enzyme.get('ec_number')
        if ec_number and ec_number != 'None':
            st.markdown(f"**ExPASy:** [{ec_number}](https://enzyme.expasy.org/EC/{ec_number})")
        else:
            st.markdown("**ExPASy:** Не указано")
    
    # Описание и специфичность
    description = enzyme.get('description')
    if description and description != 'None':
        st.markdown("### 📝 Описание функции")
        st.info(description)
    
    tissue_spec = enzyme.get('tissue_specificity')
    if tissue_spec and tissue_spec != 'None':
        st.markdown("### 🏥 Тканевая специфичность")
        st.warning(tissue_spec)
    
    st.markdown("---")

def _show_protein_details(protein: Dict[str, Any]) -> None:
    """Показывает детальную информацию о белке"""
    #st.markdown("---")
    # В заголовке используем русское название, если оно есть
    display_name = protein.get('name_ru') or protein.get('name') or 'Белок'
    st.subheader(f"🔬 {display_name}")
    
    # Основная информация
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Основная информация")
        with st.container():
            st.markdown(f"""
            **Название (EN):** {protein.get('name') or 'Не указано'}  
            **Название (RU):** {protein.get('name_ru') or 'Не указано'}  
            **Функция:** {protein.get('function') or 'Не указано'}  
            **Семейство:** {protein.get('family') or 'Не указано'}  
            **Организм:** {protein.get('organism') or 'Не указано'}  
            **Тип организма:** {protein.get('organism_type') or 'Не указано'}
            """)
    
    with col2:
        st.markdown("### 🧬 Генетическая информация")
        with st.container():
            st.markdown(f"""
            **Ген:** {protein.get('gene_name') or 'Не указано'}  
            **Локализация:** {protein.get('subcellular_location') or 'Не указано'}  
            **PDB ID:** `{protein.get('pdb_id') or 'Не указано'}`
            """)
    
    # Физико-химические свойства
    st.markdown("### ⚗️ Физико-химические свойства")
    bio_col1, bio_col2, bio_col3 = st.columns(3)
    
    with bio_col1:
        mol_weight = protein.get('molecular_weight')
        if mol_weight and mol_weight != 'None':
            st.metric("Молекулярная масса", f"{(mol_weight / 1000):.1f} kDa")
        else:
            st.metric("Молекулярная масса", "Не указано")
    
    with bio_col2:
        iso_point = protein.get('isoelectric_point')
        if iso_point and iso_point != 'None':
            st.metric("Точка pH", str(iso_point))
        else:
            st.metric("Точка pH", "Не указано")
    
    with bio_col3:
        length = protein.get('length')
        if length and length != 'None':
            st.metric("Длина", f"{length} а/к")
        else:
            st.metric("Длина", "Не указано")
    
    # Внешние идентификаторы
    st.markdown("### 🔗 Внешние идентификаторы")
    id_col1, id_col2, id_col3 = st.columns(3)
    
    with id_col1:
        uniprot_id = protein.get('uniprot_id')
        if uniprot_id and uniprot_id != 'None':
            st.markdown(f"**UniProt:** [{uniprot_id}](https://www.uniprot.org/uniprot/{uniprot_id})")
        else:
            st.markdown("**UniProt:** Не указано")
    
    with id_col2:
        pdb_id = protein.get('pdb_id')
        if pdb_id and pdb_id != 'None':
            st.markdown(f"**PDB:** [{pdb_id}](https://www.rcsb.org/structure/{pdb_id})")
        else:
            st.markdown("**PDB:** Не указано")
    
    with id_col3:
        gene_name = protein.get('gene_name')
        if gene_name and gene_name != 'None':
            st.markdown(f"**NCBI Gene:** [{gene_name}](https://www.ncbi.nlm.nih.gov/gene/?term={gene_name})")
        else:
            st.markdown("**NCBI Gene:** Не указано")
    
    # Описание и специфичность
    description = protein.get('description')
    if description and description != 'None':
        st.markdown("### 📝 Описание")
        st.info(description)
    
    tissue_spec = protein.get('tissue_specificity')
    if tissue_spec and tissue_spec != 'None':
        st.markdown("### 🏥 Тканевая специфичность")
        st.warning(tissue_spec)
    
    ptm = protein.get('post_translational_modifications')
    if ptm and ptm != 'None':
        st.markdown("### 🔧 Посттрансляционные модификации")
        st.success(ptm)
    
    st.markdown("---")

def _search_metabolites(query: Optional[str] = None, mass: Optional[float] = None, tol_ppm: int = 10, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск метаболитов"""
    conn = None
    try:
        conn = _get_metabolites_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM metabolites WHERE 1=1"
        params = []
        
        if query and query.strip():
            # Приводим запрос к формату с заглавной буквы
            formatted_query = query.strip().capitalize()
            base_query += " AND (name LIKE ? OR name_ru LIKE ? OR formula LIKE ? OR class_name LIKE ?)"
            params.extend([f"%{formatted_query}%" for _ in range(4)])
        
        if mass and mass > 0:
            tolerance = mass * tol_ppm / 1000000
            base_query += " AND exact_mass BETWEEN ? AND ?"
            params.extend([mass - tolerance, mass + tolerance])
            logger.info(f"Mass search: {mass} ± {tolerance} (tolerance: {tol_ppm} ppm)")
            logger.info(f"SQL: {base_query}")
            logger.info(f"Params: {params}")
        
        # Подсчет общего количества
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Добавляем пагинацию
        base_query += " LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        cursor = conn.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        return {
            "metabolites": results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Metabolite search error: {str(e)}")
        return {"error": f"Metabolite search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _search_enzymes(query: Optional[str] = None, mass: Optional[float] = None, tol_ppm: int = 10, organism_type: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск ферментов"""
    conn = None
    try:
        conn = _get_enzymes_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM enzymes WHERE 1=1"
        params = []
        
        if query and query.strip():
            # Приводим запрос к формату с заглавной буквы
            formatted_query = query.strip().capitalize()
            base_query += " AND (name LIKE ? OR name_ru LIKE ? OR ec_number LIKE ? OR family LIKE ?)"
            params.extend([f"%{formatted_query}%" for _ in range(4)])
        
        if mass and mass > 0:
            # Для ферментов масса в kDa, переводим в Da для поиска
            mass_da = mass * 1000  # 1 kDa = 1000 Da
            tolerance = mass_da * tol_ppm / 1000000
            base_query += " AND molecular_weight BETWEEN ? AND ?"
            params.extend([(mass_da - tolerance) / 1000, (mass_da + tolerance) / 1000])  # Обратно в kDa
            logger.info(f"Enzyme mass search: {mass} kDa ± {tolerance/1000:.6f} kDa (tolerance: {tol_ppm} ppm)")
        
        if organism_type and organism_type != "Все":
            base_query += " AND organism_type LIKE ?"
            params.append(f"%{organism_type}%")
        
        # Подсчет общего количества
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Добавляем пагинацию
        base_query += " LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        cursor = conn.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        return {
            "enzymes": results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Enzyme search error: {str(e)}")
        return {"error": f"Enzyme search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _search_proteins(query: Optional[str] = None, mass: Optional[float] = None, tol_ppm: int = 10, organism_type: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск белков"""
    conn = None
    try:
        conn = _get_proteins_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM proteins WHERE 1=1"
        params = []
        
        if query and query.strip():
            # Приводим запрос к формату с заглавной буквы
            formatted_query = query.strip().capitalize()
            base_query += " AND (name LIKE ? OR name_ru LIKE ? OR function LIKE ? OR family LIKE ?)"
            params.extend([f"%{formatted_query}%" for _ in range(4)])
        
        if mass and mass > 0:
            # Для белков масса в kDa, переводим в Da для поиска
            mass_da = mass * 1000  # 1 kDa = 1000 Da
            tolerance = mass_da * tol_ppm / 1000000
            base_query += " AND molecular_weight BETWEEN ? AND ?"
            params.extend([(mass_da - tolerance) / 1000, (mass_da + tolerance) / 1000])  # Обратно в kDa
            logger.info(f"Protein mass search: {mass} kDa ± {tolerance/1000:.6f} kDa (tolerance: {tol_ppm} ppm)")
        
        if organism_type and organism_type != "Все":
            base_query += " AND organism_type LIKE ?"
            params.append(f"%{organism_type}%")
        
        # Подсчет общего количества
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Добавляем пагинацию
        base_query += " LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        cursor = conn.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        return {
            "proteins": results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Protein search error: {str(e)}")
        return {"error": f"Protein search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _search_carbohydrates(query: Optional[str] = None, mass: Optional[float] = None, tol_ppm: int = 10, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск углеводов"""
    conn = None
    try:
        conn = _get_carbohydrates_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM carbohydrates WHERE 1=1"
        params = []
        
        if query and query.strip():
            # Приводим запрос к формату с заглавной буквы
            formatted_query = query.strip().capitalize()
            base_query += " AND (name LIKE ? OR name_ru LIKE ? OR formula LIKE ? OR type LIKE ?)"
            params.extend([f"%{formatted_query}%" for _ in range(4)])
        
        if mass and mass > 0:
            # Поиск по массе с допуском
            tolerance = mass * (tol_ppm / 1000000)
            base_query += " AND exact_mass BETWEEN ? AND ?"
            params.extend([mass - tolerance, mass + tolerance])
        
        # Подсчет общего количества
        count_query = base_query.replace("SELECT *", "SELECT COUNT(*)")
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Добавляем пагинацию
        base_query += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        cursor = conn.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        return {
            "carbohydrates": results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Carbohydrate search error: {str(e)}")
        return {"error": f"Carbohydrate search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _search_lipids(query: Optional[str] = None, mass: Optional[float] = None, tol_ppm: int = 10, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск липидов"""
    conn = None
    try:
        conn = _get_lipids_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM lipids WHERE 1=1"
        params = []
        
        if query and query.strip():
            # Приводим запрос к формату с заглавной буквы
            formatted_query = query.strip().capitalize()
            base_query += " AND (name LIKE ? OR name_ru LIKE ? OR formula LIKE ? OR type LIKE ?)"
            params.extend([f"%{formatted_query}%" for _ in range(4)])
        
        if mass and mass > 0:
            # Поиск по массе с допуском
            tolerance = mass * (tol_ppm / 1000000)
            base_query += " AND exact_mass BETWEEN ? AND ?"
            params.extend([mass - tolerance, mass + tolerance])
        
        # Подсчет общего количества
        count_query = base_query.replace("SELECT *", "SELECT COUNT(*)")
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Добавляем пагинацию
        base_query += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        cursor = conn.execute(base_query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        return {
            "lipids": results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Lipid search error: {str(e)}")
        return {"error": f"Lipid search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _unified_search(query: str, mass: Optional[float] = None, tol_ppm: int = 10, organism_type: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Унифицированный поиск по всем базам данных"""
    results = {
        "metabolites": {"data": [], "total": 0},
        "enzymes": {"data": [], "total": 0},
        "proteins": {"data": [], "total": 0},
        "carbohydrates": {"data": [], "total": 0},
        "lipids": {"data": [], "total": 0}
    }
    
    # Проверяем, что есть что искать
    if not query and not mass:
        logger.warning("Empty search query and mass")
        return results
    
    # Если есть только масса, очищаем запрос для поиска только по массе
    if mass and mass > 0 and not query:
        query = ""
    
    # Поиск метаболитов
    try:
        if mass and mass > 0:
            logger.info(f"Searching metabolites by mass: {mass} ± {tol_ppm} ppm")
            met_result = _search_metabolites(mass=mass, tol_ppm=tol_ppm, page=page, page_size=page_size)
        else:
            logger.info(f"Searching metabolites by query: {query}")
            met_result = _search_metabolites(query=query, page=page, page_size=page_size)
        
        if "error" not in met_result:
            results["metabolites"]["data"] = met_result.get("metabolites", [])
            results["metabolites"]["total"] = met_result.get("total", 0)
        else:
            logger.error(f"Metabolite search error: {met_result['error']}")
    except Exception as e:
        logger.error(f"Unexpected error in metabolite search: {e}")
    
    # Поиск ферментов (по тексту и/или массе)
    if query and query.strip() or mass and mass > 0:
        try:
            enz_result = _search_enzymes(query=query, mass=mass, tol_ppm=tol_ppm, organism_type=organism_type, page=page, page_size=page_size)
            if "error" not in enz_result:
                results["enzymes"]["data"] = enz_result.get("enzymes", [])
                results["enzymes"]["total"] = enz_result.get("total", 0)
            else:
                logger.error(f"Enzyme search error: {enz_result['error']}")
        except Exception as e:
            logger.error(f"Unexpected error in enzyme search: {e}")
    
    # Поиск белков (по тексту и/или массе)
    if query and query.strip() or mass and mass > 0:
        try:
            prot_result = _search_proteins(query=query, mass=mass, tol_ppm=tol_ppm, organism_type=organism_type, page=page, page_size=page_size)
            if "error" not in prot_result:
                results["proteins"]["data"] = prot_result.get("proteins", [])
                results["proteins"]["total"] = prot_result.get("total", 0)
            else:
                logger.error(f"Protein search error: {prot_result['error']}")
        except Exception as e:
            logger.error(f"Unexpected error in protein search: {e}")
    
    # Поиск углеводов (по тексту и/или массе)
    if query and query.strip() or mass and mass > 0:
        try:
            carb_result = _search_carbohydrates(query=query, mass=mass, tol_ppm=tol_ppm, page=page, page_size=page_size)
            if "error" not in carb_result:
                results["carbohydrates"]["data"] = carb_result.get("carbohydrates", [])
                results["carbohydrates"]["total"] = carb_result.get("total", 0)
            else:
                logger.error(f"Carbohydrate search error: {carb_result['error']}")
        except Exception as e:
            logger.error(f"Unexpected error in carbohydrate search: {e}")
    
    # Поиск липидов (по тексту и/или массе)
    if query and query.strip() or mass and mass > 0:
        try:
            lip_result = _search_lipids(query=query, mass=mass, tol_ppm=tol_ppm, page=page, page_size=page_size)
            if "error" not in lip_result:
                results["lipids"]["data"] = lip_result.get("lipids", [])
                results["lipids"]["total"] = lip_result.get("total", 0)
            else:
                logger.error(f"Lipid search error: {lip_result['error']}")
        except Exception as e:
            logger.error(f"Unexpected error in lipid search: {e}")
    
    return results

# Настройка страницы
st.set_page_config(
    page_title="Справочник соединений",
    page_icon="🧬",
    layout="centered"
)

# Заголовок и базовые стили
_inject_base_css()

# Проверка наличия баз данных
db_files = [METABOLITES_DB_PATH, ENZYMES_DB_PATH, PROTEINS_DB_PATH, CARBOHYDRATES_DB_PATH, LIPIDS_DB_PATH]
missing_dbs = [f for f in db_files if not os.path.exists(f)]

if missing_dbs:
    st.error(f"❌ **Базы данных не найдены!**")
    st.markdown(f"""
    Следующие файлы не найдены:
    {chr(10).join([f"• {f}" for f in missing_dbs])}
    
    **Для решения запустите:**
    ```bash
    python data/create_all_databases.py
    ```
    """)
    st.stop()

st.title("🧬 Справочник соединений")
st.markdown("**Унифицированный поиск по метаболитам, ферментам, белкам, углеводам и липидам**", help="Поиск по всем типам соединений в одной форме")

# Статус баз данных
totals = _get_totals()
status = totals.get("db_status", "unknown")

# KPI-панель - отцентрированная по горизонтали
st.markdown("### Статистика базы данных")
st.markdown("""
<div style="display: flex; justify-content: center; align-items: center; gap: 1rem; margin: 1rem 0; flex-wrap: wrap;">
    <div style="text-align: center; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 4px; min-width: 80px;">
        <div style="font-size: 0.8rem; color: #B0B0B0; font-weight: 500;">Метаболиты</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA;">{}</div>
    </div>
    <div style="text-align: center; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 4px; min-width: 80px;">
        <div style="font-size: 0.8rem; color: #B0B0B0; font-weight: 500;">Ферменты</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA;">{}</div>
    </div>
    <div style="text-align: center; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 4px; min-width: 80px;">
        <div style="font-size: 0.8rem; color: #B0B0B0; font-weight: 500;">Белки</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA;">{}</div>
    </div>
    <div style="text-align: center; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 4px; min-width: 80px;">
        <div style="font-size: 0.8rem; color: #B0B0B0; font-weight: 500;">Углеводы</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA;">{}</div>
    </div>
    <div style="text-align: center; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 4px; min-width: 80px;">
        <div style="font-size: 0.8rem; color: #B0B0B0; font-weight: 500;">Липиды</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA;">{}</div>
    </div>
    <div style="text-align: center; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 4px; min-width: 80px;">
        <div style="font-size: 0.8rem; color: #B0B0B0; font-weight: 500;">Статус БД</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA;">{}</div>
    </div>
</div>
""".format(
    totals.get("metabolites") or "—",
    totals.get("enzymes") or "—", 
    totals.get("proteins") or "—",
    totals.get("carbohydrates") or "—",
    totals.get("lipids") or "—",
    "OK" if status == "healthy" else "Нет файла"
), unsafe_allow_html=True)


# Инициализация state
if "page" not in st.session_state:
    st.session_state.page = 1
if "page_size" not in st.session_state:
    st.session_state.page_size = 50
if "search_submitted" not in st.session_state:
    st.session_state.search_submitted = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Карточки"
if "show_metabolite_details" not in st.session_state:
    st.session_state.show_metabolite_details = False
if "show_enzyme_details" not in st.session_state:
    st.session_state.show_enzyme_details = False
if "show_protein_details" not in st.session_state:
    st.session_state.show_protein_details = False
if "search_results" not in st.session_state:
    st.session_state.search_results = {}
if "selected_metabolite" not in st.session_state:
    st.session_state.selected_metabolite = None
if "selected_enzyme" not in st.session_state:
    st.session_state.selected_enzyme = None
if "selected_protein" not in st.session_state:
    st.session_state.selected_protein = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "last_mass" not in st.session_state:
    st.session_state.last_mass = None
if "last_organism_type" not in st.session_state:
    st.session_state.last_organism_type = "Все"
if "last_tolerance_ppm" not in st.session_state:
    st.session_state.last_tolerance_ppm = 10

# Унифицированная форма поиска

with st.form("unified_search_form"):
    st.subheader("🔍 Поиск")
    
    # Основное поле поиска
    search_query = st.text_input(
        "Поисковый запрос",
        placeholder="Например: глюкоза, dehydrogenase, insulin",
        help="Поиск по названию, формуле, EC номеру, функции. Запрос автоматически приводится к формату с заглавной буквы. Нажмите Enter для быстрого поиска.",
        key="search_query_input"
    )
    
    # Кнопка поиска прямо под полем ввода
    search_submitted = st.form_submit_button("🔍 Найти", use_container_width=True, type="primary")
    
    # Дополнительные настройки в компактном виде
    with st.expander("⚙️ Дополнительные настройки", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            mass_query = st.number_input(
                "Масса (m/z) для поиска соединений",
                min_value=0.0,
                step=0.001,
                format="%.6f",
                help="Поиск по массе среди метаболитов (Da), ферментов и белков (kDa). Оставьте 0 для поиска только по названию.",
                key="mass_query_input"
            )
            
            tolerance_ppm = st.slider("Допуск (ppm)", min_value=250, max_value=10000, value=1000, step=50, help="Частей на миллион. 250 ppm = ±0.025% от массы, 1000 ppm = ±0.1% от массы, 10000 ppm = ±1% от массы")
        
        with col2:
            organism_type = st.selectbox(
                "🌱 Тип организма",
                ["Все", "plant", "animal", "microorganism", "universal"],
                help="Фильтрация по типу организма"
            )
            
            st.session_state.page_size = st.selectbox(
                "Размер страницы",
                options=[25, 50, 100, 200],
                index=[25, 50, 100, 200].index(st.session_state.page_size)
                if st.session_state.page_size in [25, 50, 100, 200]
                else 1,
            )
    
    # Пресеты
    st.caption("💡 Быстрые пресеты (нажмите Enter для поиска):")
    presets_col1, presets_col2, presets_col3 = st.columns(3)
    with presets_col1:
        glucose_preset = st.form_submit_button("Глюкоза", use_container_width=True)
        if glucose_preset:
            st.session_state.page = 1
            st.session_state.search_query = "Глюкоза"
            # Выполняем поиск для пресета
            results = _unified_search(
                query="Глюкоза",
                mass=None,
                tol_ppm=10,
                organism_type="Все",
                page=1,
                page_size=st.session_state.page_size or 50
            )
            st.session_state.search_results = results
            st.session_state.search_submitted = True
    with presets_col2:
        dehydrogenase_preset = st.form_submit_button("Dehydrogenase", use_container_width=True)
        if dehydrogenase_preset:
            st.session_state.page = 1
            st.session_state.search_query = "Dehydrogenase"
            # Выполняем поиск для пресета
            results = _unified_search(
                query="Dehydrogenase",
                mass=None,
                tol_ppm=10,
                organism_type="Все",
                page=1,
                page_size=st.session_state.page_size or 50
            )
            st.session_state.search_results = results
            st.session_state.search_submitted = True
    with presets_col3:
        insulin_preset = st.form_submit_button("Formaldehyde", use_container_width=True)
        if insulin_preset:
            st.session_state.page = 1
            st.session_state.search_query = "Formaldehyde"
            # Выполняем поиск для пресета
            results = _unified_search(
                query="Formaldehyde",
                mass=None,
                tol_ppm=10,
                organism_type="Все",
                page=1,
                page_size=st.session_state.page_size or 50
            )
            st.session_state.search_results = results
            st.session_state.search_submitted = True

    # Обработка поиска (работает как с кнопкой, так и с Enter)
    if search_submitted:
        st.session_state.page = 1
        st.session_state.search_submitted = True
        
        with st.status("Выполняется поиск...", expanded=False):
            # Выполняем унифицированный поиск
            # Если есть только масса, передаем None для запроса
            query_to_search = search_query if search_query.strip() else None
            results = _unified_search(
                query=query_to_search,
                mass=mass_query if mass_query > 0 else None,
                tol_ppm=tolerance_ppm,
                organism_type=organism_type or "Все",
                page=1,
                page_size=st.session_state.page_size or 50
            )
            
            # Сохраняем результаты
            st.session_state.search_results = results
            st.session_state.last_query = search_query
            st.session_state.last_mass = mass_query if mass_query > 0 else None
            st.session_state.last_organism_type = organism_type
            st.session_state.last_tolerance_ppm = tolerance_ppm
        
        st.rerun()


# Отображение результатов
if st.session_state.get("search_submitted", False) and st.session_state.get("search_results"):
    st.header("Результаты поиска")
    
    results = st.session_state.get("search_results", {})
    
    # Общая статистика
    total_metabolites = results.get("metabolites", {}).get("total", 0)
    total_enzymes = results.get("enzymes", {}).get("total", 0)
    total_proteins = results.get("proteins", {}).get("total", 0)
    total_carbohydrates = results.get("carbohydrates", {}).get("total", 0)
    total_lipids = results.get("lipids", {}).get("total", 0)
    total_all = total_metabolites + total_enzymes + total_proteins + total_carbohydrates + total_lipids
    
    if total_all > 0:
        st.success(f"✅ Найдено {total_all} результатов (метаболиты: {total_metabolites}, ферменты: {total_enzymes}, белки: {total_proteins}, углеводы: {total_carbohydrates}, липиды: {total_lipids})")
        
        # Переключение вида
        view_choice = st.radio(
            "Вид", 
            options=["Карточки", "Таблица"], 
            horizontal=True, 
            index=["Карточки", "Таблица"].index(st.session_state.view_mode),
            key="view_radio"
        )
        if view_choice != st.session_state.view_mode:
            st.session_state.view_mode = view_choice
        
        # Отображение метаболитов
        metabolites = results.get("metabolites", {}).get("data", [])
        if metabolites:
            st.subheader(f"🧬 Метаболиты ({len(metabolites)})")
            
            if st.session_state.view_mode == "Таблица":
                df_rows = []
                for met in metabolites:
                    # Формируем ссылки
                    hmdb_link = f"https://hmdb.ca/metabolites/{met.get('hmdb_id')}" if met.get("hmdb_id") else ""
                    kegg_link = f"https://www.kegg.jp/entry/{met.get('kegg_id')}" if met.get("kegg_id") else ""
                    chebi_link = f"https://www.ebi.ac.uk/chebi/searchId.do?chebiId={met.get('chebi_id')}" if met.get("chebi_id") else ""
                    pubchem_link = f"https://pubchem.ncbi.nlm.nih.gov/compound/{met.get('pubchem_cid')}" if met.get("pubchem_cid") else ""
                    
                    df_rows.append({
                        "Название": met.get("name_ru", "") or met.get("name", ""),
                        "Название (EN)": met.get("name", ""),
                        "Формула": met.get("formula", ""),
                        "Масса": float(met["exact_mass"]) if isinstance(met.get("exact_mass"), (int, float)) else None,
                        "Класс": met.get("class_name", ""),
                        "HMDB": hmdb_link,
                        "KEGG": kegg_link,
                        "ChEBI": chebi_link,
                        "PubChem": pubchem_link,
                    })
                df = pd.DataFrame(df_rows)
                
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Масса": st.column_config.NumberColumn(format="%.6f"),
                        "HMDB": st.column_config.LinkColumn(
                            "HMDB",
                            help="Ссылка на HMDB",
                            validate="^https://hmdb.ca/metabolites/.*$",
                            max_chars=None,
                        ),
                        "KEGG": st.column_config.LinkColumn(
                            "KEGG",
                            help="Ссылка на KEGG",
                            validate="^https://www.kegg.jp/entry/.*$",
                            max_chars=None,
                        ),
                        "ChEBI": st.column_config.LinkColumn(
                            "ChEBI",
                            help="Ссылка на ChEBI",
                            validate="^https://www.ebi.ac.uk/chebi/searchId.do?chebiId=.*$",
                            max_chars=None,
                        ),
                        "PubChem": st.column_config.LinkColumn(
                            "PubChem",
                            help="Ссылка на PubChem",
                            validate="^https://pubchem.ncbi.nlm.nih.gov/compound/.*$",
                            max_chars=None,
                        ),
                    },
                )
                st.info("💡 **Совет:** Переключитесь в режим 'Карточки' для просмотра деталей по клику на карточку")
            else:
                cols = st.columns(3)
                for idx, met in enumerate(metabolites):
                    with cols[idx % 3]:
                        _render_metabolite_card(met)
        
        # Отображение ферментов
        enzymes = results.get("enzymes", {}).get("data", [])
        if enzymes:
            st.subheader(f"🧪 Ферменты ({len(enzymes)})")
            
            if st.session_state.view_mode == "Таблица":
                df_rows = []
                for enz in enzymes:
                    # Формируем ссылки
                    uniprot_link = f"https://www.uniprot.org/uniprot/{enz.get('uniprot_id')}" if enz.get("uniprot_id") else ""
                    kegg_link = f"https://www.kegg.jp/entry/{enz.get('kegg_enzyme_id')}" if enz.get("kegg_enzyme_id") else ""
                    expasy_link = f"https://enzyme.expasy.org/EC/{enz.get('ec_number')}" if enz.get("ec_number") else ""
                    
                    df_rows.append({
                        "Название": enz.get("name_ru", "") or enz.get("name", ""),
                        "Название (EN)": enz.get("name", ""),
                        "EC номер": enz.get("ec_number", ""),
                        "Семейство": enz.get("family", ""),
                        "Организм": enz.get("organism", ""),
                        "Тип организма": enz.get("organism_type", ""),
                        "UniProt": uniprot_link,
                        "KEGG": kegg_link,
                        "ExPASy": expasy_link,
                    })
                df = pd.DataFrame(df_rows)
                st.dataframe(
                    df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "UniProt": st.column_config.LinkColumn(
                            "UniProt",
                            help="Ссылка на UniProt",
                            validate="^https://www.uniprot.org/uniprot/.*$",
                            max_chars=None,
                        ),
                        "KEGG": st.column_config.LinkColumn(
                            "KEGG",
                            help="Ссылка на KEGG",
                            validate="^https://www.kegg.jp/entry/.*$",
                            max_chars=None,
                        ),
                        "ExPASy": st.column_config.LinkColumn(
                            "ExPASy",
                            help="Ссылка на ExPASy",
                            validate="^https://enzyme.expasy.org/EC/.*$",
                            max_chars=None,
                        ),
                    },
                )
                st.info("💡 **Совет:** Переключитесь в режим 'Карточки' для просмотра деталей по клику на карточку")
            else:
                cols = st.columns(3)
                for idx, enz in enumerate(enzymes):
                    with cols[idx % 3]:
                        _render_enzyme_card(enz)
        
        # Отображение белков
        proteins = results.get("proteins", {}).get("data", [])
        if proteins:
            st.subheader(f"🔬 Белки ({len(proteins)})")
            
            if st.session_state.view_mode == "Таблица":
                df_rows = []
                for prot in proteins:
                    # Формируем ссылки
                    uniprot_link = f"https://www.uniprot.org/uniprot/{prot.get('uniprot_id')}" if prot.get("uniprot_id") else ""
                    pdb_link = f"https://www.rcsb.org/structure/{prot.get('pdb_id')}" if prot.get("pdb_id") else ""
                    ncbi_link = f"https://www.ncbi.nlm.nih.gov/gene/?term={prot.get('gene_name')}" if prot.get("gene_name") else ""
                    
                    df_rows.append({
                        "Название": prot.get("name_ru", "") or prot.get("name", ""),
                        "Название (EN)": prot.get("name", ""),
                        "Функция": prot.get("function", ""),
                        "Семейство": prot.get("family", ""),
                        "Организм": prot.get("organism", ""),
                        "Тип организма": prot.get("organism_type", ""),
                        "UniProt": uniprot_link,
                        "PDB": pdb_link,
                        "NCBI Gene": ncbi_link,
                    })
                df = pd.DataFrame(df_rows)
                st.dataframe(
                    df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "UniProt": st.column_config.LinkColumn(
                            "UniProt",
                            help="Ссылка на UniProt",
                            validate="^https://www.uniprot.org/uniprot/.*$",
                            max_chars=None,
                        ),
                        "PDB": st.column_config.LinkColumn(
                            "PDB",
                            help="Ссылка на PDB",
                            validate="^https://www.rcsb.org/structure/.*$",
                            max_chars=None,
                        ),
                        "NCBI Gene": st.column_config.LinkColumn(
                            "NCBI Gene",
                            help="Ссылка на NCBI Gene",
                            validate="^https://www.ncbi.nlm.nih.gov/gene/?term=.*$",
                            max_chars=None,
                        ),
                    },
                )
                st.info("💡 **Совет:** Переключитесь в режим 'Карточки' для просмотра деталей по клику на карточку")
            else:
                cols = st.columns(3)
                for idx, prot in enumerate(proteins):
                    with cols[idx % 3]:
                        _render_protein_card(prot)
    
    else:
        st.warning("🔍 Результаты не найдены. Попробуйте изменить параметры поиска.")

    # Пагинация для унифицированного поиска
    max_results = max(total_metabolites, total_enzymes, total_proteins)
    if max_results > st.session_state.page_size:
        total_pages = math.ceil(max_results / st.session_state.page_size)
        
        st.subheader("📄 Пагинация")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Предыдущая", key="prev_page", disabled=st.session_state.page <= 1):
                st.session_state.page = max(1, st.session_state.page - 1)
                # Обновляем результаты для новой страницы
                results = _unified_search(
                    query=st.session_state.get("last_query", ""),
                    mass=st.session_state.get("last_mass"),
                    tol_ppm=st.session_state.get("last_tolerance_ppm", 10),
                    organism_type=st.session_state.get("last_organism_type", "Все"),
                    page=st.session_state.page,
                    page_size=st.session_state.page_size or 50
                )
                st.session_state.search_results = results
                st.rerun()
        
        with col2:
            st.markdown(f"Страница {st.session_state.page} из {total_pages}")
        
        with col3:
            if st.button("Следующая ➡️", key="next_page", disabled=st.session_state.page >= total_pages):
                st.session_state.page = min(total_pages, st.session_state.page + 1)
                # Обновляем результаты для новой страницы
                results = _unified_search(
                    query=st.session_state.get("last_query", ""),
                    mass=st.session_state.get("last_mass"),
                    tol_ppm=st.session_state.get("last_tolerance_ppm", 10),
                    organism_type=st.session_state.get("last_organism_type", "Все"),
                    page=st.session_state.page,
                    page_size=st.session_state.page_size or 50
                )
                st.session_state.search_results = results
                st.rerun()

# Отображение детальной информации
if st.session_state.get("show_metabolite_details") and st.session_state.get("selected_metabolite"):
    metabolite = st.session_state.selected_metabolite
    if metabolite and isinstance(metabolite, dict):
        st.markdown("---")
        st.markdown("## 📋 Детальная информация о метаболите")
        #st.markdown(f"**Выбран:** {metabolite.get('name', 'Метаболит')}")
        _show_metabolite_details(metabolite)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("❌ Закрыть детали", key="close_met_details", use_container_width=True):
                st.session_state.show_metabolite_details = False
                st.session_state.selected_metabolite = None
                st.rerun()
    

if st.session_state.get("show_enzyme_details") and st.session_state.get("selected_enzyme"):
    enzyme = st.session_state.selected_enzyme
    if enzyme and isinstance(enzyme, dict):
        st.markdown("---")
        st.markdown("## 📋 Детальная информация о ферменте")
        #st.markdown(f"**Выбран:** {enzyme.get('name', 'Фермент')}")
        _show_enzyme_details(enzyme)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("❌ Закрыть детали", key="close_enz_details", use_container_width=True):
                st.session_state.show_enzyme_details = False
                st.session_state.selected_enzyme = None
                st.rerun()
    

if st.session_state.get("show_protein_details") and st.session_state.get("selected_protein"):
    protein = st.session_state.selected_protein
    if protein and isinstance(protein, dict):
        #st.markdown("---")
        st.markdown("## Детальная информация о белке")
        #st.markdown(f"**Выбран:** {protein.get('name', 'Белок')}")
        _show_protein_details(protein)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("❌ Закрыть детали", key="close_prot_details", use_container_width=True):
                st.session_state.show_protein_details = False
                st.session_state.selected_protein = None
                st.rerun()
    
# Футер
st.markdown("---")
st.markdown("🧬 **Cправочник** - поиск среди метаболитов, ферментов и белков")
