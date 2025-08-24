# Метаболомный справочник для учебных задач (MVP)

## 0) Цель и аудитория
Учебный pet‑проект для курсов по **генетике**, **биохимии** и **химии**. Приложение позволяет:
- искать метаболиты по **массе (m/z)**, **химической формуле** и **названию**;
- просматривать краткие сведения: **пути**, **связанные ферменты**, **классы соединений**;
- загружать **CSV** или **списки пиков** и автоматически **аннотировать** их метаболитами;
- **экспортировать** результаты для отчётов и лабораторных работ.

Минимум интерфейса: один экран поиска + экран аннотации загрузок. Далее — расширение.

---

## 1) Предлагаемый стек
- **Бэкенд:** Python **FastAPI** (+ Pydantic, SQLAlchemy 2.x).
- **База данных:** **PostgreSQL** (для MVP допустим **SQLite**).
- **Фронтенд (простой):**
  - Вариант A: **Streamlit** (быстрый старт, минимум JS).
  - Вариант B: **Next.js/React** (если нужен «нормальный» UI и рост).
- **Химия/метаболомика:**
  - **RDKit** или **Open Babel** — масса по формуле, SMILES/InChI.
  - **pandas** — CSV/таблицы; **pyarrow/xlsxwriter** — экспорт.
  - **pymzML** (или **pyOpenMS/OpenMS**) — работа с файлами mzML (расширение).
- **Инфраструктура:** Docker + docker‑compose (бэкенд, БД, фронтенд).

> Для учебного прототипа: FastAPI + SQLite + Streamlit — самый быстрый путь к MVP.

---

## 2) Функциональность MVP
1. **Поиск метаболитов**
   - По **массе**: точный/приблизительный (допуск ±ppm или ±Da).
   - По **формуле**: точное совпадение (с валидацией парсера формул).
   - По **названию/синониму**: подстрока/полнотекстовый поиск.
2. **Карточка метаболита**
   - Название, формула, **точная масса**.
   - Ссылки: **HMDB**, **KEGG**, **ChEBI**, **PubChem**, **UniProt** (для ферментов).
   - Список **биохимических путей**, **ферментов**, **класс соединения**.
3. **Загрузка CSV/списков m/z**
   - Чтение файла, выбор столбца с m/z.
   - Авто‑аннотация: для каждой массы — кандидаты из БД с рейтингом по допуску.
   - Ручной выбор «верного» кандидата (чекбокс/селект).
4. **Экспорт**
   - Таблица результатов (CSV/Excel).
   - Отчёт (при желании — PDF).

---

## 3) Источники данных
Используй открытые базы (для MVP достаточно 500–2000 записей).

- **HMDB** — https://hmdb.ca  
  Экспорт записей, в каждой много перекрёстных ссылок (KEGG/ChEBI/PubChem/UniProt).
- **ChEBI** — https://www.ebi.ac.uk/chebi/  (дампы: https://ftp.ebi.ac.uk/pub/databases/chebi/)  
  SDF/SQL‑дампы с формулами, массами и онтологиями.
- **KEGG (REST API)** — https://rest.kegg.jp  
  Соединения (COMPOUND), пути (PATHWAY) и пр.
- **LIPID MAPS (LMSD)** — https://www.lipidmaps.org/resources/databases/lmsd  
  Полезно для липидов, SDF выгрузки.
- **PubChem PUG‑REST** — https://pubchem.ncbi.nlm.nih.gov/programmatic/
- **MetaboLights** — https://www.ebi.ac.uk/metabolights/ (реальные учебные наборы).
- **MassBank/MoNA** — спектральные библиотеки для расширений.

На старте возьми: **LIPID MAPS SDF** + небольшую **выборку HMDB/ChEBI**. Этого хватит для поиска по массе/формуле и ссылок.

---

## 4) Модель данных (ER‑диаграмма)
```mermaid
erDiagram
    METABOLITE {
        int id PK
        varchar name
        varchar formula
        double exact_mass
        varchar hmdb_id
        varchar chebi_id
        varchar kegg_id
        varchar pubchem_cid
        int class_id FK
    }
    CLASS {
        int id PK
        varchar name
    }
    PATHWAY {
        int id PK
        varchar name
        varchar source   // kegg|reactome|hmdb
        varchar ext_id   // внеш. ID в источнике
    }
    ENZYME {
        int id PK
        varchar name
        varchar uniprot_id
    }
    METABOLITE ||--o{ METABOLITE_PATHWAY : participates
    PATHWAY ||--o{ METABOLITE_PATHWAY : has
    METABOLITE ||--o{ METABOLITE_ENZYME  : linked_to
    ENZYME ||--o{ METABOLITE_ENZYME  : catalyzes
    CLASS ||--o{ METABOLITE : class_of
```

**Связующие таблицы:**
- `metabolite_pathway(metabolite_id, pathway_id)`
- `metabolite_enzyme(metabolite_id, enzyme_id)`

**Индексы:**
- `metabolite(exact_mass)` — BTREE.
- `metabolite(name)`, `metabolite(formula)` — BTREE + при росте данных можно FTS.
- Уникальные внешние ID (при наличии): `hmdb_id`, `chebi_id`, `kegg_id`, `pubchem_cid`.

---

## 5) Пример API (FastAPI)
```python
from fastapi import FastAPI, Query, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select
from db import async_session, Metabolite  # ваши модели/сессия

app = FastAPI(title="Metabolome Handbook")

class MetaboliteOut(BaseModel):
    id: int
    name: str
    formula: Optional[str] = None
    exact_mass: Optional[float] = None
    hmdb_id: Optional[str] = None
    chebi_id: Optional[str] = None
    kegg_id: Optional[str] = None
    pubchem_cid: Optional[str] = None

@app.get("/metabolites/search", response_model=List[MetaboliteOut])
async def search_metabolites(
    q: Optional[str] = Query(default=None, description="name or formula"),
    mass: Optional[float] = Query(default=None, description="m/z"),
    tol_ppm: float = 10.0
):
    async with async_session() as s:
        stmt = select(Metabolite)
        if q:
            stmt = stmt.where((Metabolite.name.ilike(f"%{q}%")) | (Metabolite.formula == q))
        if mass is not None:
            delta = mass * tol_ppm / 1e6
            low, high = mass - delta, mass + delta
            stmt = stmt.where(Metabolite.exact_mass.between(low, high))
        res = (await s.execute(stmt.limit(200))).scalars().all()
        return [MetaboliteOut.model_validate(r.__dict__) for r in res]

@app.post("/annotate/csv")
async def annotate_csv(file: UploadFile = File(...), mz_column: str = "mz", tol_ppm: float = 10.0):
    import pandas as pd
    import io
    df = pd.read_csv(io.BytesIO(await file.read()))
    mzs = df[mz_column].astype(float).tolist()
    rows = []
    async with async_session() as s:
        for mz in mzs:
            delta = mz * tol_ppm / 1e6
            low, high = mz - delta, mz + delta
            stmt = select(Metabolite).where(Metabolite.exact_mass.between(low, high)).limit(20)
            r = (await s.execute(stmt)).scalars().all()
            rows.append({
                "mz": mz,
                "candidates": [getattr(x, "name") for x in r],
                "ids": [getattr(x, "id") for x in r],
            })
    return {"items": rows}
```

---

## 6) План разработки (2 недели на MVP)

### Неделя 1
1. **Окружение**: репозиторий, poetry/uv/venv, docker‑compose (db, api).
2. **Схема БД**: таблицы из раздела 4, миграции Alembic.
3. **Импорт данных**:
   - Парсинг SDF (ChEBI/LipidMaps) → заполнение таблицы `metabolite` (name, formula, exact_mass, внешние ID).
   - Мини‑набор путей/ферментов (ручной CSV или KEGG API) → `pathway`, `enzyme`, связующие таблицы.
4. **API**: `/metabolites/search` (масса/формула/название), `/metabolites/{id}` (детали).
5. **Smoke‑тесты**: pytest (поиск, границы толеранса, пустые результаты).

### Неделя 2
1. **UI**: Streamlit‑страница
   - Поля ввода: q | mass | tol_ppm
   - Таблица результатов → карточка метаболита
2. **Загрузка CSV**: выбор столбца с m/z → `/annotate/csv` → интерактивная таблица сопоставлений.
3. **Экспорт**: кнопки «Скачать CSV/Excel» (из pandas DataFrame).
4. **Полировка**: ссылки HMDB/KEGG/ChEBI/PubChem/UniProt, простая справка «Как пользоваться».

> Результат: рабочий MVP с поиском и аннотацией CSV.

---

## 7) Форматы данных для загрузки

### CSV (минимум)
```text
mz,intensity,rt
180.063,120000,85.2
255.232, 55000, 76.1
...
```
- Обязателен столбец **mz** (float).
- Остальные (intensity, rt) — опционально, просто показываем в таблице.

### mzML (расширение)
- Использовать `pymzML` для чтения, извлекать пики (m/z, intensity, rt).
- Для MVP достаточно агрегировать top‑N пиков по интенсивности и передать как список m/z в аннотацию.

---

## 8) Логика аннотации
- Допуск по массе (ppm) переводится в интервал:  
  `delta = m * tol_ppm / 1e6; [m - delta, m + delta]`.
- Кандидаты сортируются по |m − exact_mass| (возрастающе).
- При наличии формулы в CSV разрешить «строгий» режим: сначала точное совпадение формулы, затем масса.
- Сохранение пользовательского выбора (таблица `annotation`: user_id | upload_id | mz | metabolite_id | note | created_at).

---

## 9) Экспорт
- **CSV/Excel** (UTF‑8): исходные столбцы + колонки `best_match_name`, `best_match_id`, `tolerance_ppm`, `delta_mDa`.
- При желании — **PDF‑отчёт** (WeasyPrint/ReportLab) с краткой сводкой и таблицей.

---

## 10) Развёртывание (пример docker‑compose.yml)
```yaml
version: "3.9"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: metab
      POSTGRES_USER: metab
      POSTGRES_PASSWORD: metab
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]

  api:
    build: ./api
    environment:
      DATABASE_URL: postgresql+psycopg://metab:metab@db:5432/metab
    ports: ["8000:8000"]
    depends_on: [db]

  ui:
    build: ./ui
    ports: ["8501:8501"]
    depends_on: [api]

volumes:
  pgdata:
```

---

## 11) Идеи для расширения
- Визуализация путей (Cytoscape.js/D3.js, KEGG/Reactome overlays).
- Поддержка **mzML** целиком, извлечение пиков, фильтры по интенсивности/rt.
- Интеграция **UniProt/AlphaFold** для вкладки ферментов (просмотр 3D‑структур).
- Рейтинг кандидатов: комбинировать массу, изотопные паттерны, правила химии.
- Многопользовательский режим, учебные задания, автопроверка решений.
- Кэширование запросов к внешним API (Redis).

---

## 12) Учебные сценарии
- **Лаба:** «Аннотируй 20 пиков LC‑MS, выдели три ключевых метаболита, объясни выбор».
- **Задание:** «Найти метаболиты для массы 180.063 ±10 ppm и составить таблицу ссылок HMDB/KEGG/ChEBI».
- **Демонстрация:** «Связать найденные метаболиты с путями гликолиза/ЦТК».

---

## 13) Правовые аспекты и лицензии
- Проверь лицензии: KEGG (ограничения на коммерческое использование), HMDB/ChEBI/LipidMaps (обычно допускают академическое/некоммерческое).
- В UI/README добавь раздел «Источники данных» и условия использования.
- Для публикации кода — лицензия MIT/Apache‑2.0; для данных — укажи источники и версии дампов.

---

## 14) Чек‑лист готовности MVP
- [ ] Схема БД и миграции применяются
- [ ] Импорт тестовых метаболитов (≥500 записей)
- [ ] Поиск работает: по массе/формуле/названию
- [ ] Карточка метаболита со ссылками HMDB/KEGG/ChEBI/PubChem
- [ ] Загрузка CSV и авто‑аннотация по tol_ppm
- [ ] Экспорт результата (CSV/Excel)
- [ ] Документация API (Swagger) и README с шагами запуска
- [ ] Пример учебного датасета в репозитории

---

## 15) Полезные ссылки
- HMDB: https://hmdb.ca
- ChEBI (дампы): https://ftp.ebi.ac.uk/pub/databases/chebi/
- KEGG REST API: https://rest.kegg.jp
- LIPID MAPS LMSD: https://www.lipidmaps.org/resources/databases/lmsd
- PubChem PUG‑REST: https://pubchem.ncbi.nlm.nih.gov/programmatic/
- MetaboLights: https://www.ebi.ac.uk/metabolights/
- pymzML: https://pymzml.github.io/
- OpenMS/pyOpenMS: https://www.openms.de/
