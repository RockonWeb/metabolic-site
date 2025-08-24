import streamlit as st
import pandas as pd
import sqlite3
import io
from typing import List, Dict, Any
import math
import plotly.express as px
import plotly.graph_objects as go
import os

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
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid rgba(0,0,0,0.07);
            box-shadow: 0 6px 18px rgba(0,0,0,0.06);
            padding: 18px 18px 16px 18px;
            margin-bottom: 12px;
        }
        .card-title {
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 8px 0;
            color: #000000;
        }
        .card-subtitle { font-size: 14px; color: #475569; margin-bottom: 12px; }
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
        </style>
        """,
        unsafe_allow_html=True,
    )





def _get_database_connection():
    """Создает подключение к базе данных"""
    try:
        # Проверяем существование файла
        if not os.path.exists(DATABASE_PATH):
            return None
            
        return sqlite3.connect(DATABASE_PATH)
    except Exception as e:
        return None

def _get_totals() -> Dict[str, Any]:
    """Возвращает агрегированные счетчики для шапки: метаболиты, ферменты и статус БД."""
    totals = {"metabolites": None, "enzymes": None, "db_status": "unknown"}

    try:
        conn = _get_database_connection()
        if conn is None:
            totals["db_status"] = "offline"
            return totals
        
        # Получаем список всех таблиц
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Ищем таблицы с метаболитами и ферментами
        for table in tables:
            try:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                if "metabolite" in table.lower() or "compound" in table.lower():
                    totals["metabolites"] = count
                elif "enzyme" in table.lower() or "protein" in table.lower():
                    totals["enzymes"] = count
                    
            except Exception:
                continue
        
        conn.close()
        totals["db_status"] = "healthy"
        
    except Exception:
        totals["db_status"] = "offline"

    return totals


def _render_metabolite_card(m: Dict[str, Any]) -> None:
    """Карточка метаболита: название, формула, масса, класс и внешние ID."""
    name = m.get("name") or "Без названия"
    formula = m.get("formula") or "—"
    mass = m.get("exact_mass")
    mass_fmt = f"{mass:.6f} Da" if isinstance(mass, (int, float)) else "—"
    cls = m.get("class_name") or "—"

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

    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">{name}</div>
          <div class="card-subtitle">Формула: <b>{formula}</b> &nbsp;|&nbsp; Масса: <b>{mass_fmt}</b></div>
          <div>{pills_html}</div>
          <div class="row-divider"></div>
          <div>{links_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_enzyme_card(e: Dict[str, Any]) -> None:
    name = e.get("name") or e.get("name_en") or "Без названия"
    ec = e.get("ec_number") or "—"
    org = e.get("organism") or "—"
    fam = e.get("family") or "—"
    props = []
    if ec != "—":
        props.append(f"EC: <b>{ec}</b>")
    if org != "—":
        props.append(f"Организм: <b>{org}</b>")
    if fam != "—":
        props.append(f"Семейство: <b>{fam}</b>")
    subtitle = " &nbsp;|&nbsp; ".join(props)
    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">{name}</div>
          <div class="card-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _search_metabolites(query: str = None, mass: float = None, tol_ppm: int = 10, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск метаболитов в базе данных"""
    try:
        conn = _get_database_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        # Пытаемся найти таблицу metabolites
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%metabolite%'")
        metabolite_tables = [row[0] for row in cursor.fetchall()]
        
        if not metabolite_tables:
            return {"error": "No metabolite tables found"}
        
        table_name = metabolite_tables[0]  # Берем первую найденную таблицу
        
        # Получаем структуру таблицы
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Базовый запрос
        base_query = f"SELECT * FROM {table_name} WHERE 1=1"
        params = []
        
        # Поиск по тексту
        if query:
            # Ищем поля для текстового поиска
            text_fields = [col for col in columns if any(keyword in col.lower() for keyword in ['name', 'formula', 'class'])]
            if text_fields:
                search_conditions = [f"{col} LIKE ?" for col in text_fields]
                base_query += " AND (" + " OR ".join(search_conditions) + ")"
                params.extend([f"%{query}%" for _ in text_fields])
        
        # Поиск по массе
        if mass:
            # Ищем поле для массы
            mass_fields = [col for col in columns if any(keyword in col.lower() for keyword in ['mass', 'weight', 'mz'])]
            if mass_fields:
                mass_field = mass_fields[0]
                tolerance = mass * tol_ppm / 1000000
                base_query += f" AND {mass_field} BETWEEN ? AND ?"
                params.extend([mass - tolerance, mass + tolerance])
        
        # Подсчет общего количества
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Добавляем пагинацию
        base_query += " LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        # Выполняем основной запрос
        cursor = conn.execute(base_query, params)
        results = []
        
        for row in cursor.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col] = row[i]
            results.append(row_dict)
        
        conn.close()
        
        return {
            "metabolites": results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        return {"error": f"Metabolite search failed: {str(e)}"}

def _search_enzymes(query: str = None, organism_type: str = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Поиск ферментов в базе данных"""
    try:
        conn = _get_database_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        # Пытаемся найти таблицу enzymes
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%enzyme%'")
        enzyme_tables = [row[0] for row in cursor.fetchall()]
        
        if not enzyme_tables:
            return {"error": "No enzyme tables found"}
        
        table_name = enzyme_tables[0]  # Берем первую найденную таблицу
        
        # Получаем структуру таблицы
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Базовый запрос
        base_query = f"SELECT * FROM {table_name} WHERE 1=1"
        params = []
        
        # Поиск по тексту
        if query:
            # Ищем поля для текстового поиска
            text_fields = [col for col in columns if any(keyword in col.lower() for keyword in ['name', 'ec', 'family'])]
            if text_fields:
                search_conditions = [f"{col} LIKE ?" for col in text_fields]
                base_query += " AND (" + " OR ".join(search_conditions) + ")"
                params.extend([f"%{query}%" for _ in text_fields])
        
        # Фильтр по типу организма
        if organism_type and organism_type != "Все":
            # Ищем поле для типа организма
            org_fields = [col for col in columns if any(keyword in col.lower() for keyword in ['organism', 'type', 'species'])]
            if org_fields:
                org_field = org_fields[0]
                base_query += f" AND {org_field} LIKE ?"
                params.append(f"%{organism_type}%")
        
        # Подсчет общего количества
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Добавляем пагинацию
        base_query += " LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        # Выполняем основной запрос
        cursor = conn.execute(base_query, params)
        results = []
        
        for row in cursor.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col] = row[i]
            results.append(row_dict)
        
        conn.close()
        
        return {
            "enzymes": results,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        return {"error": f"Enzyme search failed: {str(e)}"}

def _annotate_csv_data(file_content: bytes, mz_column: str, tol_ppm: int = 10) -> Dict[str, Any]:
    """Аннотация CSV данных метаболитами"""
    try:
        # Читаем CSV
        df = pd.read_csv(io.BytesIO(file_content))
        
        if mz_column not in df.columns:
            return {"error": f"Column {mz_column} not found in CSV"}
        
        # Получаем массы
        mz_values = df[mz_column].astype(float).tolist()
        
        # Аннотируем каждую массу
        annotated_items = []
        for mz in mz_values:
            # Ищем метаболиты по массе
            metabolites = _search_metabolites(mass=mz, tol_ppm=tol_ppm, page_size=5)
            
            if "error" not in metabolites and metabolites.get("metabolites"):
                candidates = [met.get("name", "Unknown") for met in metabolites["metabolites"]]
                best_match = metabolites["metabolites"][0] if metabolites["metabolites"] else None
            else:
                candidates = []
                best_match = None
            
            annotated_items.append({
                "mz": mz,
                "candidates": candidates,
                "best_match": best_match
            })
        
        return {
            "items": annotated_items,
            "total_annotated": len(annotated_items),
            "tolerance_ppm": tol_ppm
        }
        
    except Exception as e:
        return {"error": f"CSV annotation failed: {str(e)}"}

# Конфигурация базы данных
# 🔧 НАСТРОЙКА ПУТИ К БД:
# ✅ УСТАНОВЛЕНО: metabolome.db
# 
# Для изменения используйте:
# 1. Файл .env в папке ui/ с содержимым:
#    DATABASE_PATH=path/to/your/database.db
# 2. Или переменную окружения:
#    export DATABASE_PATH=path/to/your/database.db
# 3. Или замените значение по умолчанию ниже

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/metabolome.db")

# Настройка страницы
st.set_page_config(
    page_title="Метаболомный справочник",
    page_icon="🧬",
    layout="wide"
)

# Заголовок и базовые стили
_inject_base_css()

# Проверка наличия базы данных
if not os.path.exists(DATABASE_PATH):
    st.error(f"❌ **База данных не найдена!**")
    st.markdown(f"""
    Файл `{DATABASE_PATH}` не найден в текущей директории.
    
    **Для решения:**
    1. Убедитесь, что файл базы данных находится в папке `ui/`
    2. Или измените переменную `DATABASE_PATH` в коде
    3. Или создайте файл `.env` с содержимым: `DATABASE_PATH=path/to/your/database.db`
    
    **Текущий путь:** `{os.path.abspath(DATABASE_PATH)}`
    """)
    st.stop()

st.title("🧬 Метаболомный справочник")
st.markdown("**Учебное приложение для анализа метаболитов и аннотации данных LC-MS - поиск доступен сразу на главной странице**")

# Отладочная информация (удалить в продакшене)
# with st.expander("🔍 DEBUG: Состояние session_state"):
#     st.write("**Метаболиты:**")
#     st.write(f"- met_page: {st.session_state.get('met_page', 'не установлен')}")
#     st.write(f"- met_search_results: {len(st.session_state.get('met_search_results', []))} результатов")
#     st.write(f"- view_mode: {st.session_state.get('view_mode', 'не установлен')}")
#     st.write(f"- search_submitted: {st.session_state.get('search_submitted', 'не установлен')}")
#     
#     st.write("**Ферменты:**")
#     st.write(f"- enz_page: {st.session_state.get('enz_page', 'не установлен')}")
#     st.write(f"- enz_view_mode: {st.session_state.get('enz_view_mode', 'не установлен')}")

# Статус базы данных
totals = _get_totals()
status = totals.get("db_status", "unknown")
if status == "healthy":
    st.success("✅ База данных активна")
else:
    st.error("❌ База данных неактивна")

# Инициализация state
if "met_page" not in st.session_state:
    st.session_state.met_page = 1
if "met_page_size" not in st.session_state:
    st.session_state.met_page_size = 50
if "met_sort_by" not in st.session_state:
    st.session_state.met_sort_by = "Релевантность"
if "search_submitted" not in st.session_state:
    st.session_state.search_submitted = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Карточки"
if "enz_view_mode" not in st.session_state:
    st.session_state.enz_view_mode = "Карточки"

# Переключатель типа поиска
st.markdown("### 🎯 Выберите тип поиска")
search_type = st.radio(
    "Тип поиска",
    options=["🧬 Метаболиты", "🧪 Ферменты"],
    horizontal=True,
    key="search_type_selector"
)

# Индикатор активного поиска
if search_type == "🧬 Метаболиты":
    st.success("🔍 Активен поиск метаболитов")
else:
    st.info("🔍 Активен поиск ферментов")

# Форма поиска метаболитов
if search_type == "🧬 Метаболиты":
    st.markdown("---")
    with st.form("metabolite_search_form"):
        st.subheader("🔍 Поиск метаболитов")
        
        mode = st.radio(
            "Режим поиска",
            options=["По названию/формуле", "По массе (m/z)"],
            horizontal=False,
        )

        search_query = ""
        mass_query = 0.0

        if mode == "По названию/формуле":
            # Инициализация preset_query
            if "preset_query" not in st.session_state:
                st.session_state.preset_query = ""
            
            search_query = st.text_input(
                "Название или формула",
                value=st.session_state.preset_query,
                placeholder="например: глюкоза, C6H12O6",
                key="met_text_query",
            )
            
            # Сброс preset после использования
            if st.session_state.preset_query:
                st.session_state.preset_query = ""
        else:
            mass_query = st.number_input(
                "Масса (m/z)", min_value=0.0, step=0.001, format="%.6f", key="met_mass_query"
            )

        col_fs1, col_fs2 = st.columns(2)
        with col_fs1:
            tolerance_ppm = st.slider("Допуск (ppm)", min_value=1, max_value=100, value=10, step=1)
        with col_fs2:
            st.session_state.met_page_size = st.selectbox(
                "Размер страницы",
                options=[25, 50, 100, 200],
                index=[25, 50, 100, 200].index(st.session_state.met_page_size)
                if st.session_state.met_page_size in [25, 50, 100, 200]
                else 1,
            )

        # Пресеты
        st.caption("💡 Быстрые пресеты:")
        presets_col1, presets_col2, presets_col3 = st.columns(3)
        with presets_col1:
            if st.form_submit_button("Глюкоза", use_container_width=True):
                st.session_state.met_page = 1
                st.session_state.preset_query = "глюкоза"
        with presets_col2:
            if st.form_submit_button("Пируват", use_container_width=True):
                st.session_state.met_page = 1
                st.session_state.preset_query = "пируват"
        with presets_col3:
            if st.form_submit_button("C6H12O6", use_container_width=True):
                st.session_state.met_page = 1
                st.session_state.preset_query = "C6H12O6"

        # Кнопка поиска
        search_submitted = st.form_submit_button("🔍 Найти метаболиты", use_container_width=True, type="primary")
        
        if search_submitted:
            st.session_state.met_page = 1
            st.session_state.search_submitted = True
            
            # Сохраняем параметры поиска для пагинации
            if mode == "По названию/формуле":
                st.session_state.last_search_query = search_query
                st.session_state.last_mass_query = None
            else:
                st.session_state.last_search_query = None
                st.session_state.last_mass_query = mass_query
            st.session_state.last_tolerance_ppm = tolerance_ppm
            
            # Выполняем поиск и сохраняем результаты
            data = _search_metabolites(search_query, mass_query, tolerance_ppm, 1, st.session_state.met_page_size)
            if "error" not in data:
                st.session_state.met_search_results = data.get("metabolites", [])
                st.session_state.met_total_results = data.get("total", 0)
                st.rerun()
            else:
                st.error(f"Ошибка поиска: {data['error']}")

# Форма поиска ферментов
elif search_type == "🧪 Ферменты":
    st.markdown("---")
    with st.form("enzyme_search_form"):
        st.subheader("🔍 Поиск ферментов")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Инициализация enz_preset_query
            if "enz_preset_query" not in st.session_state:
                st.session_state.enz_preset_query = ""
            
            enzyme_query = st.text_input(
                "Название, EC номер или организм",
                value=st.session_state.enz_preset_query,
                placeholder="Например: Ribulose, dehydrogenase, 4.1.1.39",
                help="Введите название фермента, EC номер или название организма"
            )
            
            # Сброс preset после использования
            if st.session_state.enz_preset_query:
                st.session_state.enz_preset_query = ""
            
        with col2:
            organism_type = st.selectbox(
                "🌱 Тип организма",
                ["Все", "plant", "animal", "bacteria", "fungi"],
                help="Фильтрация по типу организма"
            )
        
        # Параметры пагинации и сортировки
        if "enz_page" not in st.session_state:
            st.session_state.enz_page = 1
        if "enz_page_size" not in st.session_state:
            st.session_state.enz_page_size = 50
        if "enz_sort_by" not in st.session_state:
            st.session_state.enz_sort_by = "Релевантность"

        colp1, colp2 = st.columns(2)
        with colp1:
            st.session_state.enz_page_size = st.selectbox(
                "Размер страницы",
                options=[25, 50, 100, 200],
                index=[25, 50, 100, 200].index(st.session_state.enz_page_size)
                if st.session_state.enz_page_size in [25, 50, 100, 200]
                else 1,
            )
        with colp2:
            st.session_state.enz_sort_by = st.selectbox(
                "Сортировать по",
                options=["Релевантность", "Название", "EC", "Организм", "Семейство"],
            )

        # Пресеты
        st.caption("💡 Быстрые пресеты:")
        pcol1, pcol2, pcol3 = st.columns(3)
        with pcol1:
            if st.form_submit_button("Ribulose", use_container_width=True):
                st.session_state.enz_page = 1
                st.session_state.enz_preset_query = "Ribulose"
        with pcol2:
            if st.form_submit_button("dehydrogenase", use_container_width=True):
                st.session_state.enz_page = 1
                st.session_state.enz_preset_query = "dehydrogenase"
        with pcol3:
            if st.form_submit_button("4.1.1.39", use_container_width=True):
                st.session_state.enz_page = 1
                st.session_state.enz_preset_query = "4.1.1.39"

        submitted = st.form_submit_button("🔍 Найти ферменты", use_container_width=True, type="primary")
        
        if submitted:
            st.session_state.enz_page = 1
        
        if submitted:
            if enzyme_query or organism_type != "Все":
                # Выполняем поиск ферментов
                data = _search_enzymes(enzyme_query, organism_type, 1, st.session_state.enz_page_size)
                
                if "error" not in data:
                    enzymes = data.get("enzymes", [])
                    total = data.get("total", 0)
                    total_pages = max(1, math.ceil(total / st.session_state.enz_page_size))
                    
                    # Сохраняем результаты для использования вне формы
                    st.session_state.enz_search_results = enzymes
                    st.session_state.enz_total_results = total
                    st.session_state.enz_total_pages = total_pages
                    st.session_state.enz_last_query = enzyme_query
                    st.session_state.enz_last_organism_type = organism_type
                    st.session_state.enz_search_submitted = True
                    
                    if enzymes:
                        st.success(f"✅ Найдено {total} ферментов")
                    else:
                        st.warning("🔍 Ферменты не найдены. Попробуйте изменить параметры поиска.")
                else:
                    st.error(f"❌ Ошибка поиска: {data['error']}")
            else:
                st.warning("🔍 Введите поисковый запрос или выберите тип организма")
    


# Основной контент
# Проверяем, есть ли сохраненные результаты поиска метаболитов
if st.session_state.get("search_submitted", False) and st.session_state.get("met_search_results"):
    st.header("📊 Результаты поиска метаболитов")
    
    # Используем сохраненные результаты поиска
    metabolites = st.session_state.get("met_search_results", [])
    total = st.session_state.get("met_total_results", 0)
    total_pages = max(1, math.ceil(total / st.session_state.met_page_size))
    
    if metabolites:
        st.success(f"✅ Найдено {len(metabolites)} метаболитов")

        # Сортировка и вид (вынесено наверх для стабильности)
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            st.session_state.met_sort_by = st.selectbox(
                "Сортировать по",
                options=["Релевантность", "Название", "Масса", "Класс"],
                index=["Релевантность", "Название", "Масса", "Класс"].index(
                    st.session_state.met_sort_by
                )
                if st.session_state.met_sort_by in ["Релевантность", "Название", "Масса", "Класс"]
                else 0,
                key="met_sort_select"
            )
        with col_v2:
            view_choice = st.radio(
                "Вид", 
                options=["Карточки", "Таблица"], 
                horizontal=True, 
                index=["Карточки", "Таблица"].index(st.session_state.view_mode),
                key="met_view_radio"
            )
            if view_choice != st.session_state.view_mode:
                st.session_state.view_mode = view_choice

        # Применяем сортировку
        if st.session_state.met_sort_by != "Релевантность":
            key_map = {
                "Название": lambda m: (m.get("name") or "").lower(),
                "Масса": lambda m: m.get("exact_mass") or 0,
                "Класс": lambda m: (m.get("class_name") or "").lower(),
            }
            metabolites = sorted(metabolites, key=key_map[st.session_state.met_sort_by])
            # Обновляем сохраненные результаты
            st.session_state.met_search_results = metabolites

        # Табличное представление
        df_data = []
        for met in metabolites:
            df_data.append({
                "Название": met.get("name", ""),
                "Формула": met.get("formula", ""),
                "Масса": f"{met['exact_mass']:.6f}" if isinstance(met.get('exact_mass'), (int, float)) else "",
                "Класс": met.get("class_name", ""),
                "HMDB ID": met.get("hmdb_id", ""),
                "KEGG ID": met.get("kegg_id", ""),
                "ChEBI ID": met.get("chebi_id", ""),
                "PubChem CID": met.get("pubchem_cid", "")
            })
        df = pd.DataFrame(df_data)

        if st.session_state.view_mode == "Таблица":
            st.dataframe(df, use_container_width=True)
        else:
            # Карточки, 3 колонки
            cols = st.columns(3)
            for idx, met in enumerate(metabolites):
                with cols[idx % 3]:
                    _render_metabolite_card(met)

        # Гистограмма по массе (если есть данные)
        if len(df) and (df["Масса"] != "").any():
            try:
                df_mass = df[df["Масса"] != ""].copy()
                df_mass["Масса"] = df_mass["Масса"].astype(float)
                st.subheader("📈 Распределение масс (m/z) в результатах")
                fig = px.histogram(df_mass, x="Масса", nbins=30, height=280)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass
        
        # Детальная информация (селектор)
        with st.expander("📋 Детальная информация по метаболиту"):
            selected_metabolite_name = st.selectbox(
                "Выберите метаболит:",
                options=[met.get("name", "Неизвестно") for met in metabolites],
                format_func=lambda x: x if x != "Неизвестно" else "Без названия"
            )

            if selected_metabolite_name and selected_metabolite_name != "Неизвестно":
                selected_metabolite = next((met for met in metabolites if met.get("name") == selected_metabolite_name), None)
                if selected_metabolite:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Основная информация:**")
                        st.write(f"**Название:** {selected_metabolite.get('name', 'Не указано')}")
                        st.write(f"**Формула:** {selected_metabolite.get('formula', 'Не указано')}")
                        st.write(f"**Масса:** {selected_metabolite.get('exact_mass', 'Не указано')}")
                        st.write(f"**Класс:** {selected_metabolite.get('class_name', 'Не указано')}")
                        st.write(f"**HMDB ID:** {selected_metabolite.get('hmdb_id', 'Не указано')}")
                        st.write(f"**KEGG ID:** {selected_metabolite.get('kegg_id', 'Не указано')}")
                    with col2:
                        st.markdown("**Дополнительные данные:**")
                        st.write(f"**ChEBI ID:** {selected_metabolite.get('chebi_id', 'Не указано')}")
                        st.write(f"**PubChem CID:** {selected_metabolite.get('pubchem_cid', 'Не указано')}")
                        if selected_metabolite.get('description'):
                            st.write(f"**Описание:** {selected_metabolite['description']}")
                        if selected_metabolite.get('pathway'):
                            st.write(f"**Путь:** {selected_metabolite['pathway']}")
                        if selected_metabolite.get('biological_properties'):
                            st.write(f"**Биологические свойства:** {selected_metabolite['biological_properties']}")

# Проверяем, есть ли сохраненные результаты поиска ферментов
if st.session_state.get("enz_search_submitted", False) and st.session_state.get("enz_search_results"):
    st.header("📊 Результаты поиска ферментов")
    
    # Используем сохраненные результаты поиска
    enzymes = st.session_state.get("enz_search_results", [])
    total = st.session_state.get("enz_total_results", 0)
    
    if enzymes:
        st.success(f"✅ Найдено {len(enzymes)} ферментов")
        
        # Переключение вида и сортировка (вынесено наверх для стабильности)
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            st.session_state.enz_sort_by = st.selectbox(
                "Сортировать по",
                options=["Релевантность", "Название", "EC", "Организм", "Семейство"],
                index=["Релевантность", "Название", "EC", "Организм", "Семейство"].index(
                    st.session_state.enz_sort_by
                )
                if st.session_state.enz_sort_by in ["Релевантность", "Название", "EC", "Организм", "Семейство"]
                else 0,
                key="enz_sort_select"
            )
        with col_v2:
            enz_view_choice = st.radio(
                "Вид", 
                options=["Карточки", "Таблица"], 
                horizontal=True, 
                index=["Карточки", "Таблица"].index(st.session_state.enz_view_mode),
                key="enz_view_radio"
            )
            if enz_view_choice != st.session_state.enz_view_mode:
                st.session_state.enz_view_mode = enz_view_choice

        # Таблица данных для отображения
        df_data = []
        for enzyme in enzymes:
            df_data.append({
                "ID": enzyme.get("id"),
                "Название": enzyme.get("name", ""),
                "EC номер": enzyme.get("ec_number", ""),
                "Организм": enzyme.get("organism", ""),
                "Тип": enzyme.get("organism_type", ""),
                "Семейство": enzyme.get("family", ""),
                "Мол. масса (kDa)": enzyme.get("molecular_weight"),
                "Опт. pH": enzyme.get("optimal_ph"),
                "Опт. T°C": enzyme.get("optimal_temperature"),
                "Локализация": enzyme.get("subcellular_location", "")
            })
        df = pd.DataFrame(df_data)

        # Применяем сортировку
        if st.session_state.enz_sort_by != "Релевантность" and len(df):
            sort_map = {
                "Название": "Название",
                "EC": "EC номер",
                "Организм": "Организм",
                "Семейство": "Семейство",
            }
            if st.session_state.enz_sort_by in sort_map:
                df = df.sort_values(by=sort_map[st.session_state.enz_sort_by], kind="mergesort")
                # также сортируем карточки
                key_funcs = {
                    "Название": lambda e: (e.get("name") or "").lower(),
                    "EC": lambda e: (e.get("ec_number") or ""),
                    "Организм": lambda e: (e.get("organism") or "").lower(),
                    "Семейство": lambda e: (e.get("family") or "").lower(),
                }
                enzymes = sorted(enzymes, key=key_funcs[st.session_state.enz_sort_by])
                # Обновляем сохраненные результаты
                st.session_state.enz_search_results = enzymes

        # Отображение в выбранном виде
        if st.session_state.enz_view_mode == "Таблица":
            st.dataframe(df, use_container_width=True)
        else:
            # Карточки, 3 колонки
            cols = st.columns(3)
            for idx, e in enumerate(enzymes):
                with cols[idx % 3]:
                    _render_enzyme_card(e)

        # Детальная информация (селектор)
        with st.expander("📋 Детальная информация по ферменту"):
            selected_enzyme_id = st.selectbox(
                "Выберите фермент:",
                options=[e["id"] for e in enzymes],
                format_func=lambda x: f"{x}: {next(e['name'] for e in enzymes if e['id'] == x)}"
            )

            if selected_enzyme_id:
                selected_enzyme = next(e for e in enzymes if e["id"] == selected_enzyme_id)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Основная информация:**")
                    st.write(f"**Название:** {selected_enzyme.get('name', 'Не указано')}")
                    st.write(f"**Белок:** {selected_enzyme.get('protein_name', 'Не указано')}")
                    st.write(f"**Ген:** {selected_enzyme.get('gene_name', 'Не указано')}")
                    st.write(f"**EC номер:** {selected_enzyme.get('ec_number', 'Не указано')}")
                    st.write(f"**Семейство:** {selected_enzyme.get('family', 'Не указано')}")
                    st.write(f"**UniProt ID:** {selected_enzyme.get('uniprot_id', 'Не указано')}")
                with col2:
                    st.markdown("**Биохимические свойства:**")
                    if selected_enzyme.get('molecular_weight'):
                        st.write(f"**Мол. масса:** {selected_enzyme['molecular_weight']:.1f} kDa")
                    if selected_enzyme.get('optimal_ph'):
                        st.write(f"**Оптимальный pH:** {selected_enzyme['optimal_ph']}")
                    if selected_enzyme.get('optimal_temperature'):
                        st.write(f"**Оптимальная T:** {selected_enzyme['optimal_temperature']}°C")
                    st.write(f"**Организм:** {selected_enzyme.get('organism', 'Не указано')}")
                    st.write(f"**Локализация:** {selected_enzyme.get('subcellular_location', 'Не указано')}")
                if selected_enzyme.get('description'):
                    st.markdown("**Описание функции:**")
                    st.write(selected_enzyme['description'])
                if selected_enzyme.get('tissue_specificity'):
                    st.markdown("**Тканевая специфичность:**")
                    st.write(selected_enzyme['tissue_specificity'])

# Пагинация для метаболитов
if st.session_state.get("search_submitted", False) and st.session_state.get("met_total_results", 0):
    total = st.session_state.get("met_total_results", 0)
    total_pages = max(1, math.ceil(total / st.session_state.met_page_size))
    
    if total_pages > 1:
        st.subheader("📄 Пагинация метаболитов")
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("⬅️ Предыдущая", disabled=st.session_state.met_page <= 1, key="met_prev"):
                st.session_state.met_page = max(1, st.session_state.met_page - 1)
                # Обновляем результаты для новой страницы
                data = _search_metabolites(
                    st.session_state.get("last_search_query"),
                    st.session_state.get("last_mass_query"),
                    st.session_state.get("last_tolerance_ppm", 10),
                    st.session_state.met_page,
                    st.session_state.met_page_size
                )
                if "error" not in data:
                    st.session_state.met_search_results = data.get("metabolites", [])
                    st.rerun()
        with pc2:
            st.markdown(f"Страница {st.session_state.met_page} из {total_pages}")
        with pc3:
            if st.button("Следующая ➡️", disabled=st.session_state.met_page >= total_pages, key="met_next"):
                st.session_state.met_page = min(total_pages, st.session_state.met_page + 1)
                # Обновляем результаты для новой страницы
                data = _search_metabolites(
                    st.session_state.get("last_search_query"),
                    st.session_state.get("last_mass_query"),
                    st.session_state.get("last_tolerance_ppm", 10),
                    st.session_state.met_page,
                    st.session_state.met_page_size
                )
                if "error" not in data:
                    st.session_state.met_search_results = data.get("metabolites", [])
                    st.rerun()

# Пагинация для ферментов
if st.session_state.get("enz_search_submitted", False) and st.session_state.get("enz_total_results", 0):
    total = st.session_state.get("enz_total_results", 0)
    total_pages = max(1, math.ceil(total / st.session_state.enz_page_size))
    
    if total_pages > 1:
        st.subheader("📄 Пагинация ферментов")
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        
        with pc1:
            if st.button("⬅️ Предыдущая", key="enz_prev", disabled=st.session_state.enz_page <= 1):
                st.session_state.enz_page = max(1, st.session_state.enz_page - 1)
                # Обновляем результаты для новой страницы
                data = _search_enzymes(
                    st.session_state.get("enz_last_query"),
                    st.session_state.get("enz_last_organism_type"),
                    st.session_state.enz_page,
                    st.session_state.enz_page_size
                )
                if "error" not in data:
                    st.session_state.enz_search_results = data.get("enzymes", [])
                    st.rerun()
                    
        with pc2:
            st.markdown(f"Страница {st.session_state.enz_page} из {total_pages}")
            
        with pc3:
            if st.button("Следующая ➡️", key="enz_next", disabled=st.session_state.enz_page >= total_pages):
                st.session_state.enz_page = min(total_pages, st.session_state.enz_page + 1)
                # Обновляем результаты для новой страницы
                data = _search_enzymes(
                    st.session_state.get("enz_last_query"),
                    st.session_state.get("enz_last_organism_type"),
                    st.session_state.enz_page,
                    st.session_state.enz_page_size
                )
                if "error" not in data:
                    st.session_state.enz_search_results = data.get("enzymes", [])
                    st.rerun()

# Вкладки для разных функций
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Поиск метаболитов", "🧪 Поиск ферментов", "📁 Аннотация CSV", "📚 Справка"])

with tab1:
    st.header("🔍 Поиск метаболитов")
    st.markdown("""
    **Поиск выполняется напрямую в локальной базе данных по:**
    - **Названию** (например: глюкоза, пируват)
    - **Химической формуле** (например: C6H12O6)
    - **Массе (m/z)** с указанием допуска в ppm
    
    **База данных:** `{DATABASE_PATH}`
    
    **💡 Используйте форму поиска на главной странице для быстрого доступа!**
    """.format(DATABASE_PATH=DATABASE_PATH))

with tab2:
    st.header("🧪 Поиск ферментов")
    st.markdown("""
    **Поиск выполняется напрямую в локальной базе данных по:**
    - **Названию** (например: Ribulose, dehydrogenase)
    - **EC номеру** (например: 4.1.1.39, 1.1.1)
    - **Организму** (например: Arabidopsis, Cucumis)
    - **Типу организма** (plant, animal, bacteria, fungi)
    
    **База данных:** `{DATABASE_PATH}`
    
    **💡 Используйте форму поиска на главной странице для быстрого доступа!**
    """.format(DATABASE_PATH=DATABASE_PATH))

with tab3:
    st.header("📁 Аннотация CSV файлов")
    st.markdown("Загрузите CSV файл с пиками LC-MS для автоматической аннотации метаболитами из локальной базы данных")
    st.markdown(f"**База данных:** `{DATABASE_PATH}`")
    st.markdown("**💡 Используйте эту вкладку для аннотации CSV файлов с данными LC-MS!**")
    
    # Загрузка файла
    uploaded_file = st.file_uploader(
        "Выберите CSV файл",
        type=['csv'],
        help="Файл должен содержать столбец с массами (m/z)"
    )
    
    if uploaded_file is not None:
        try:
            # Читаем CSV
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Файл загружен: {len(df)} строк")
            
            # Показываем первые строки
            st.subheader("📊 Предварительный просмотр")
            st.dataframe(df.head(), use_container_width=True)
            
            # Выбор столбца с массами
            if len(df.columns) > 0:
                mass_column = st.selectbox(
                    "Выберите столбец с массами (m/z):",
                    df.columns,
                    index=0
                )
                
                # Параметры аннотации
                col1, col2 = st.columns(2)
                with col1:
                    annotation_tolerance = st.slider(
                        "Допуск аннотации (ppm):",
                        min_value=1,
                        max_value=100,
                        value=10,
                        step=1
                    )
                
                with col2:
                    max_candidates = st.slider(
                        "Максимум кандидатов:",
                        min_value=1,
                        max_value=20,
                        value=5,
                        step=1
                    )
                
                # Кнопка аннотации
                if st.button("🔬 Начать аннотацию", type="primary"):
                    with st.spinner("Выполняется аннотация..."):
                        # Выполняем аннотацию
                        annotation_data = _annotate_csv_data(
                            uploaded_file.getvalue(),
                            mass_column,
                            annotation_tolerance
                        )
                        
                        if "error" not in annotation_data:
                            st.success("✅ Аннотация завершена!")
                            
                            # Показываем результаты
                            st.subheader("📋 Результаты аннотации")
                            
                            results_data = []
                            for item in annotation_data.get("items", []):
                                mz = item["mz"]
                                candidates = item.get("candidates", [])
                                best_match = item.get("best_match")
                                
                                results_data.append({
                                    "m/z": mz,
                                    "Кандидаты": ", ".join(candidates[:3]) if candidates else "Не найдено",
                                    "Лучший кандидат": best_match["name"] if best_match else "Не выбран",
                                    "Формула": best_match["formula"] if best_match else "",
                                    "Класс": best_match.get("class_name", "") if best_match else ""
                                })
                            
                            results_df = pd.DataFrame(results_data)
                            st.dataframe(results_df, use_container_width=True)
                            
                            # Экспорт результатов
                            st.subheader("💾 Экспорт результатов")
                            
                            # CSV экспорт
                            csv_buffer = io.StringIO()
                            results_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                            csv_data = csv_buffer.getvalue()
                            
                            st.download_button(
                                label="📥 Скачать CSV",
                                data=csv_data,
                                file_name="annotation_results.csv",
                                mime="text/csv"
                                )
                            
                            # Excel экспорт
                            excel_buffer = io.BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                results_df.to_excel(writer, sheet_name='Аннотация', index=False)
                            excel_data = excel_buffer.getvalue()
                            
                            st.download_button(
                                label="📥 Скачать Excel",
                                data=excel_data,
                                file_name="annotation_results.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.error(f"❌ Ошибка аннотации: {annotation_data['error']}")
            else:
                st.warning("⚠️ CSV файл не содержит столбцов")
                
        except Exception as e:
            st.error(f"❌ Ошибка чтения файла: {str(e)}")

with tab4:
    st.header("📚 Справка по использованию")
    st.markdown(f"**База данных:** `{DATABASE_PATH}`")
    st.markdown("**💡 Здесь собраны все подсказки, примеры и инструкции по использованию приложения!**")
    
    st.subheader("🎯 Назначение приложения")
    st.markdown("""
     **Метаболомный справочник** - это учебное приложение для:
     - Поиска метаболитов по массе, названию и химической формуле
     - Поиска растительных ферментов по различным параметрам
     - Аннотации пиков LC-MS данных
     - Изучения биохимических путей и ферментов
     - Создания справочных таблиц для лабораторных работ
     """)
     
    st.subheader("🚀 Быстрый старт")
    st.markdown("""
     **Поиск доступен сразу на главной странице!**
     
     1. Выберите тип поиска: **Метаболиты** или **Ферменты**
     2. Введите поисковый запрос или используйте пресеты
     3. Нажмите кнопку поиска
     4. Результаты отображаются сразу под формой поиска
     
     **Все подсказки и примеры находятся в этой вкладке "Справка"**
     """)
    
    st.subheader("💾 База данных")
    st.markdown(f"""
    **Текущая база данных:** `{DATABASE_PATH}`
    
    Приложение автоматически обнаруживает таблицы в базе данных и адаптируется к их структуре.
    
    **Поддерживаемые типы таблиц:**
    - **Метаболиты**: таблицы с названиями, содержащими `metabolite` или `compound`
    - **Ферменты**: таблицы с названиями, содержащими `enzyme` или `protein`
    
    **Автоматическое обнаружение полей:**
    - Поиск по названию: поля `name`, `formula`, `class`
    - Поиск по массе: поля `mass`, `weight`, `mz`
    - Поиск ферментов: поля `name`, `ec`, `family`, `organism`
    """)
    
    st.subheader("🔍 Как искать метаболиты")
    st.markdown("""
     1. **По названию**: Введите название метаболита (например: глюкоза, пируват)
     2. **По формуле**: Введите химическую формулу (например: C6H12O6)
     3. **По массе**: Укажите массу (m/z) и допустимое отклонение в ppm
     
     **Примечание:** Поиск выполняется напрямую в локальной базе данных SQLite
     """)
     
    st.subheader("💡 Примеры поиска метаболитов")
    col1, col2 = st.columns(2)
     
    with col1:
         st.markdown("**По названию:**")
         st.code("глюкоза")
         st.code("пируват")
         st.code("аланин")
     
    with col2:
         st.markdown("**По массе:**")
         st.code("180.063 ±10 ppm")
         st.code("88.016 ±5 ppm")
         st.code("507.182 ±20 ppm")
    
         st.subheader("🧪 Как искать ферменты")
    st.markdown("""
     1. **По названию**: Введите полное или частичное название (например: Ribulose, dehydrogenase)
     2. **По EC номеру**: Введите номер классификации (например: 4.1.1.39, 1.1.1)
     3. **По организму**: Введите название организма (например: Arabidopsis, Cucumis)
     4. **По типу**: Выберите тип организма из списка (plant, animal, bacteria, fungi)
     
     **Примечание:** Поиск выполняется напрямую в локальной базе данных SQLite
     """)
     
    st.subheader("💡 Примеры поиска ферментов")
    col1, col2 = st.columns(2)
     
    with col1:
         st.markdown("**По названию:**")
         st.code("RuBisCO")
         st.code("Глутамин-синтетаза")
         st.code("Нитрат-редуктаза")
         
         st.markdown("**По семейству:**")
         st.code("Оксидоредуктазы")
         st.code("Трансферазы")
         st.code("Гидролазы")
     
    with col2:
         st.markdown("**По EC номеру:**")
         st.code("4.1.1.39")
         st.code("6.3.1.2")
         st.code("1.7.1.1")
         
         st.markdown("**По организму:**")
         st.code("Arabidopsis")
         st.code("Растения")
         st.code("plant")
    
    st.subheader("📁 Как аннотировать CSV файлы")
    st.markdown("""
    1. Подготовьте CSV файл со столбцом, содержащим массы (m/z)
    2. Загрузите файл в разделе "Аннотация CSV"
    3. Выберите столбец с массами
    4. Установите параметры аннотации (допуск, количество кандидатов)
    5. Запустите аннотацию
    6. Экспортируйте результаты в CSV или Excel
    
    **Примечание:** Аннотация выполняется по локальной базе данных метаболитов
    """)
    
    st.subheader("📊 Формат CSV файла")
    st.markdown("""
    Пример структуры CSV файла:
    ```csv
    mz,intensity,rt
    180.063,120000,85.2
    255.232,55000,76.1
    507.182,89000,92.3
    ```
    """)
    
    st.subheader("🔗 Источники данных")
    st.markdown("""
    Приложение работает с локальной базой данных SQLite, которая может содержать данные из:
    - **HMDB** (Human Metabolome Database)
    - **KEGG** (Kyoto Encyclopedia of Genes and Genomes)
    - **ChEBI** (Chemical Entities of Biological Interest)
    - **PubChem** (Chemical Database)
    
    **Важно:** Убедитесь, что база данных содержит необходимые таблицы и данные
    """)
    
    st.subheader("📚 Учебные сценарии")
    st.markdown("""
    - **Лабораторная работа**: "Аннотируйте 20 пиков LC-MS, выделите три ключевых метаболита"
    - **Задание**: "Найдите метаболиты для массы 180.063 ±10 ppm и составьте таблицу ссылок"
    - **Демонстрация**: "Свяжите найденные метаболиты с путями гликолиза и цикла Кребса"
    
    **Преимущества локальной версии:**
    - Работает без интернета
    - Быстрый доступ к данным
    - Возможность работы с собственными данными
    """)

# Футер
st.markdown("---")
st.markdown("🧬 **Метаболомный справочник** - Учебное приложение для курсов по биохимии и химии")
st.markdown("💾 **Работает напрямую с базой данных SQLite**")

