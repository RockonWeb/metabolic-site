import streamlit as st
import pandas as pd
import sqlite3
import io
from typing import List, Dict, Any
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
        }
        .card-title {
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 8px 0;
            color: #FAFAFA;
        }
        .card-subtitle { font-size: 14px; color: #B0B0B0; margin-bottom: 12px; }
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
        

        </style>
        

        """,
        unsafe_allow_html=True,
    )

# Конфигурация баз данных
METABOLITES_DB_PATH = os.getenv("METABOLITES_DB_PATH", "data/metabolites.db")
ENZYMES_DB_PATH = os.getenv("ENZYMES_DB_PATH", "data/enzymes.db")
PROTEINS_DB_PATH = os.getenv("PROTEINS_DB_PATH", "data/proteins.db")

# Отладочная информация
logger.info(f"Текущая рабочая директория: {os.getcwd()}")
logger.info(f"Путь к базе метаболитов: {os.path.abspath(METABOLITES_DB_PATH)}")
logger.info(f"Путь к базе ферментов: {os.path.abspath(ENZYMES_DB_PATH)}")
logger.info(f"Путь к базе белков: {os.path.abspath(PROTEINS_DB_PATH)}")

def _get_metabolites_connection():
    """Создает подключение к базе данных метаболитов"""
    try:
        logger.info(f"Проверяем существование файла: {METABOLITES_DB_PATH}")
        if not os.path.exists(METABOLITES_DB_PATH):
            logger.error(f"Файл не найден: {METABOLITES_DB_PATH}")
            return None
        logger.info(f"Подключаемся к базе метаболитов: {METABOLITES_DB_PATH}")
        conn = sqlite3.connect(METABOLITES_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        logger.info("Подключение к базе метаболитов успешно")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе метаболитов: {e}")
        return None

def _get_enzymes_connection():
    """Создает подключение к базе данных ферментов"""
    try:
        logger.info(f"Проверяем существование файла: {ENZYMES_DB_PATH}")
        if not os.path.exists(ENZYMES_DB_PATH):
            logger.error(f"Файл не найден: {ENZYMES_DB_PATH}")
            return None
        logger.info(f"Подключаемся к базе ферментов: {ENZYMES_DB_PATH}")
        conn = sqlite3.connect(ENZYMES_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        logger.info("Подключение к базе ферментов успешно")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе ферментов: {e}")
        return None

def _get_proteins_connection():
    """Создает подключение к базе данных белков"""
    try:
        logger.info(f"Проверяем существование файла: {PROTEINS_DB_PATH}")
        if not os.path.exists(PROTEINS_DB_PATH):
            logger.error(f"Файл не найден: {PROTEINS_DB_PATH}")
            return None
        logger.info(f"Подключаемся к базе белков: {PROTEINS_DB_PATH}")
        conn = sqlite3.connect(PROTEINS_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        logger.info("Подключение к базе белков успешно")
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе белков: {e}")
        return None

def _get_totals() -> Dict[str, Any]:
    """Возвращает агрегированные счетчики для шапки"""
    totals = {"metabolites": 0, "enzymes": 0, "proteins": 0, "db_status": "unknown"}
    
    # Подсчет метаболитов
    logger.info("Получаем подключение к базе метаболитов для подсчета")
    conn_met = None
    try:
        conn_met = _get_metabolites_connection()
        if conn_met:
            cursor = conn_met.execute("SELECT COUNT(*) FROM metabolites")
            totals["metabolites"] = cursor.fetchone()[0]
            logger.info(f"Найдено метаболитов: {totals['metabolites']}")
        else:
            logger.error("Не удалось получить подключение к базе метаболитов")
    except Exception as e:
        logger.error(f"Ошибка при подсчете метаболитов: {e}")
    finally:
        if conn_met:
            conn_met.close()
    
    # Подсчет ферментов
    logger.info("Получаем подключение к базе ферментов для подсчета")
    conn_enz = None
    try:
        conn_enz = _get_enzymes_connection()
        if conn_enz:
            cursor = conn_enz.execute("SELECT COUNT(*) FROM enzymes")
            totals["enzymes"] = cursor.fetchone()[0]
            logger.info(f"Найдено ферментов: {totals['enzymes']}")
        else:
            logger.error("Не удалось получить подключение к базе ферментов")
    except Exception as e:
        logger.error(f"Ошибка при подсчете ферментов: {e}")
    finally:
        if conn_enz:
            conn_enz.close()
    
    # Подсчет белков
    logger.info("Получаем подключение к базе белков для подсчета")
    conn_prot = None
    try:
        conn_prot = _get_proteins_connection()
        if conn_prot:
            cursor = conn_prot.execute("SELECT COUNT(*) FROM proteins")
            totals["proteins"] = cursor.fetchone()[0]
            logger.info(f"Найдено белков: {totals['proteins']}")
        else:
            logger.error("Не удалось получить подключение к базе белков")
    except Exception as e:
        logger.error(f"Ошибка при подсчете белков: {e}")
    finally:
        if conn_prot:
            conn_prot.close()
    
    # Определяем статус
    if totals["metabolites"] > 0 or totals["enzymes"] > 0 or totals["proteins"] > 0:
        totals["db_status"] = "healthy"
        logger.info("Статус БД: healthy")
    else:
        totals["db_status"] = "offline"
        logger.error("Статус БД: offline - нет данных в базах")
    
    return totals

def _render_metabolite_card(m: Dict[str, Any]) -> None:
    """Карточка метаболита с ссылками и кнопкой деталей"""
    name = m.get("name") or "Без названия"
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

    # Создаем карточку с кнопкой
    st.markdown(
        f"""
        <div class="card clickable-card" style="cursor: pointer;">
          <div class="card-title">{name}</div>
          <div class="card-subtitle">Формула: <b>{formula}</b> &nbsp;|&nbsp; Масса: <b>{mass_fmt}</b></div>
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
    name = e.get("name") or e.get("name_ru") or "Без названия"
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
    subtitle = " &nbsp;|&nbsp; ".join(props)
    
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
    name = p.get("name") or p.get("name_ru") or "Без названия"
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
        props.append(f"Функция: <b>{func}</b>")
    if org != "—":
        props.append(f"Организм: <b>{org}</b>")
    if fam != "—":
        props.append(f"Семейство: <b>{fam}</b>")
    subtitle = " &nbsp;|&nbsp; ".join(props)
    
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
    st.markdown("---")
    st.subheader(f"🧬 {metabolite.get('name', 'Метаболит')}")
    
    # Основная информация в карточках
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Основная информация")
        with st.container():
            st.markdown(f"""
            **Название:** {metabolite.get('name') or 'Не указано'}  
            **Название (RU):** {metabolite.get('name_ru') or 'Не указано'}  
            **Формула:** `{metabolite.get('formula') or 'Не указано'}`  
            **Класс:** {metabolite.get('class_name') or 'Не указано'}
            """)
    
    with col2:
        st.markdown("### ⚖️ Физико-химические свойства")
        with st.container():
            mass = metabolite.get('exact_mass')
            mass_str = f"{mass:.6f} Da" if isinstance(mass, (int, float)) else 'Не указано'
            st.markdown(f"""
            **Масса:** {mass_str}  
            **Молекулярная формула:** `{metabolite.get('formula') or 'Не указано'}`
            """)
    
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
    st.markdown("---")
    st.subheader(f"🧪 {enzyme.get('name', 'Фермент')}")
    
    # Основная информация
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Основная информация")
        with st.container():
            st.markdown(f"""
            **Название:** {enzyme.get('name') or 'Не указано'}  
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
    st.markdown("---")
    st.subheader(f"🔬 {protein.get('name', 'Белок')}")
    
    # Основная информация
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Основная информация")
        with st.container():
            st.markdown(f"""
            **Название:** {protein.get('name') or 'Не указано'}  
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
            st.metric("Молекулярная масса", f"{mol_weight:.1f} kDa")
        else:
            st.metric("Молекулярная масса", "Не указано")
    
    with bio_col2:
        iso_point = protein.get('isoelectric_point')
        if iso_point and iso_point != 'None':
            st.metric("Изоэлектрическая точка", str(iso_point))
        else:
            st.metric("Изоэлектрическая точка", "Не указано")
    
    with bio_col3:
        length = protein.get('length')
        if length and length != 'None':
            st.metric("Длина", f"{length} аминокислот")
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

def _search_metabolites(query: str = None, mass: float = None, tol_ppm: int = 10, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск метаболитов"""
    conn = None
    try:
        conn = _get_metabolites_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM metabolites WHERE 1=1"
        params = []
        
        if query:
            base_query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(name_ru) LIKE LOWER(?) OR LOWER(formula) LIKE LOWER(?) OR LOWER(class_name) LIKE LOWER(?))"
            params.extend([f"%{query}%" for _ in range(4)])
        
        if mass:
            tolerance = mass * tol_ppm / 1000000
            base_query += " AND exact_mass BETWEEN ? AND ?"
            params.extend([mass - tolerance, mass + tolerance])
        
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
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
        return {"error": f"Metabolite search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _search_enzymes(query: str = None, organism_type: str = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск ферментов"""
    conn = None
    try:
        conn = _get_enzymes_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM enzymes WHERE 1=1"
        params = []
        
        if query:
            base_query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(name_ru) LIKE LOWER(?) OR LOWER(ec_number) LIKE LOWER(?) OR LOWER(family) LIKE LOWER(?))"
            params.extend([f"%{query}%" for _ in range(4)])
        
        if organism_type and organism_type != "Все":
            base_query += " AND LOWER(organism_type) LIKE LOWER(?)"
            params.append(f"%{organism_type}%")
        
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
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
        return {"error": f"Enzyme search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _search_proteins(query: str = None, organism_type: str = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск белков"""
    conn = None
    try:
        conn = _get_proteins_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        base_query = "SELECT * FROM proteins WHERE 1=1"
        params = []
        
        if query:
            base_query += " AND (LOWER(name) LIKE LOWER(?) OR LOWER(name_ru) LIKE LOWER(?) OR LOWER(function) LIKE LOWER(?) OR LOWER(family) LIKE LOWER(?))"
            params.extend([f"%{query}%" for _ in range(4)])
        
        if organism_type and organism_type != "Все":
            base_query += " AND LOWER(organism_type) LIKE LOWER(?)"
            params.append(f"%{organism_type}%")
        
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
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
        return {"error": f"Protein search failed: {str(e)}"}
    finally:
        if conn:
            conn.close()

def _unified_search(query: str, mass: float = None, tol_ppm: int = 10, organism_type: str = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Унифицированный поиск по всем базам данных"""
    results = {
        "metabolites": {"data": [], "total": 0},
        "enzymes": {"data": [], "total": 0},
        "proteins": {"data": [], "total": 0}
    }
    
    # Поиск метаболитов
    if mass:
        met_result = _search_metabolites(mass=mass, tol_ppm=tol_ppm, page=page, page_size=page_size)
    else:
        met_result = _search_metabolites(query=query, page=page, page_size=page_size)
    
    if "error" not in met_result:
        results["metabolites"]["data"] = met_result.get("metabolites", [])
        results["metabolites"]["total"] = met_result.get("total", 0)
    
    # Поиск ферментов
    enz_result = _search_enzymes(query=query, organism_type=organism_type, page=page, page_size=page_size)
    if "error" not in enz_result:
        results["enzymes"]["data"] = enz_result.get("enzymes", [])
        results["enzymes"]["total"] = enz_result.get("total", 0)
    
    # Поиск белков
    prot_result = _search_proteins(query=query, organism_type=organism_type, page=page, page_size=page_size)
    if "error" not in prot_result:
        results["proteins"]["data"] = prot_result.get("proteins", [])
        results["proteins"]["total"] = prot_result.get("total", 0)
    
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
db_files = [METABOLITES_DB_PATH, ENZYMES_DB_PATH, PROTEINS_DB_PATH]
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
st.markdown("**Унифицированный поиск по метаболитам, ферментам и белкам**", help="Поиск по всем типам соединений в одной форме")

# Статус баз данных
totals = _get_totals()
status = totals.get("db_status", "unknown")

# KPI-панель - отцентрированная по горизонтали
st.markdown("### Статистика базы данных")
st.markdown("""
<div style="display: flex; justify-content: center; align-items: center; gap: 1rem; margin: 1rem 0;">
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
        <div style="font-size: 0.8rem; color: #B0B0B0; font-weight: 500;">Статус БД</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #FAFAFA;">{}</div>
    </div>
</div>
""".format(
    totals.get("metabolites") or "—",
    totals.get("enzymes") or "—", 
    totals.get("proteins") or "—",
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

# Унифицированная форма поиска

with st.form("unified_search_form"):
    st.subheader("🔍 Поиск")
    
    # Основное поле поиска
    search_query = st.text_input(
        "Поисковый запрос",
        placeholder="Например: глюкоза, dehydrogenase, insulin",
        help="Поиск по названию, формуле, EC номеру, функции. Нажмите Enter для быстрого поиска.",
        key="search_query_input"
    )
    
    # Кнопка поиска прямо под полем ввода
    search_submitted = st.form_submit_button("🔍 Найти", use_container_width=True, type="primary")
    
    # Дополнительные настройки в компактном виде
    with st.expander("⚙️ Дополнительные настройки", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            mass_query = st.number_input(
                "Масса (m/z) для поиска метаболитов",
                min_value=0.0,
                step=0.001,
                format="%.6f",
                help="Оставьте 0 для поиска только по названию.",
                key="mass_query_input"
            )
            
            tolerance_ppm = st.slider("Допуск (ppm)", min_value=1, max_value=100, value=10, step=1)
        
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
                page_size=st.session_state.page_size
            )
            st.session_state.search_results = results
            st.session_state.search_submitted = True
    with presets_col2:
        dehydrogenase_preset = st.form_submit_button("dehydrogenase", use_container_width=True)
        if dehydrogenase_preset:
            st.session_state.page = 1
            st.session_state.search_query = "dehydrogenase"
            # Выполняем поиск для пресета
            results = _unified_search(
                query="dehydrogenase",
                mass=None,
                tol_ppm=10,
                organism_type="Все",
                page=1,
                page_size=st.session_state.page_size
            )
            st.session_state.search_results = results
            st.session_state.search_submitted = True
    with presets_col3:
        insulin_preset = st.form_submit_button("insulin", use_container_width=True)
        if insulin_preset:
            st.session_state.page = 1
            st.session_state.search_query = "insulin"
            # Выполняем поиск для пресета
            results = _unified_search(
                query="insulin",
                mass=None,
                tol_ppm=10,
                organism_type="Все",
                page=1,
                page_size=st.session_state.page_size
            )
            st.session_state.search_results = results
            st.session_state.search_submitted = True
    

    
    # Обработка поиска (работает как с кнопкой, так и с Enter)
    if search_submitted:
        st.session_state.page = 1
        st.session_state.search_submitted = True
        
        with st.status("Выполняется поиск...", expanded=False):
            # Выполняем унифицированный поиск
            results = _unified_search(
                query=search_query,
                mass=mass_query if mass_query > 0 else None,
                tol_ppm=tolerance_ppm,
                organism_type=organism_type,
                page=1,
                page_size=st.session_state.page_size
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
    total_all = total_metabolites + total_enzymes + total_proteins
    
    if total_all > 0:
        st.success(f"✅ Найдено {total_all} результатов (метаболиты: {total_metabolites}, ферменты: {total_enzymes}, белки: {total_proteins})")
        
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
                        "Название": met.get("name", ""),
                        "Название (RU)": met.get("name_ru", ""),
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
                        "Название": enz.get("name", ""),
                        "Название (RU)": enz.get("name_ru", ""),
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
                        "Название": prot.get("name", ""),
                        "Название (RU)": prot.get("name_ru", ""),
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

# Отображение детальной информации
if st.session_state.get("show_metabolite_details") and st.session_state.get("selected_metabolite"):
    st.markdown("---")
    st.markdown("## 📋 Детальная информация о метаболите")
    st.markdown(f"**Выбран:** {st.session_state.selected_metabolite.get('name', 'Метаболит')}")
    _show_metabolite_details(st.session_state.selected_metabolite)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("❌ Закрыть детали", key="close_met_details", use_container_width=True):
            st.session_state.show_metabolite_details = False
            st.session_state.selected_metabolite = None
            st.rerun()
    

if st.session_state.get("show_enzyme_details") and st.session_state.get("selected_enzyme"):
    st.markdown("---")
    st.markdown("## 📋 Детальная информация о ферменте")
    st.markdown(f"**Выбран:** {st.session_state.selected_enzyme.get('name', 'Фермент')}")
    _show_enzyme_details(st.session_state.selected_enzyme)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("❌ Закрыть детали", key="close_enz_details", use_container_width=True):
            st.session_state.show_enzyme_details = False
            st.session_state.selected_enzyme = None
            st.rerun()
    

if st.session_state.get("show_protein_details") and st.session_state.get("selected_protein"):
    st.markdown("---")
    st.markdown("## Детальная информация о белке")
    st.markdown(f"**Выбран:** {st.session_state.selected_protein.get('name', 'Белок')}")
    _show_protein_details(st.session_state.selected_protein)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("❌ Закрыть детали", key="close_prot_details", use_container_width=True):
            st.session_state.show_protein_details = False
            st.session_state.selected_protein = None
            st.rerun()
    
# Футер
st.markdown("---")
st.markdown("🧬 **Cправочник** - поиск среди метаболитов, ферментов и белков")
