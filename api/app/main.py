from fastapi import FastAPI, Depends, Query, UploadFile, File, HTTPException, Response, Body
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional
import io
import pandas as pd
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from api.database.base import get_db
from api.schemas import MetaboliteOut, SearchResponse, AnnotationResponse, AnnotationCandidate, AnnotationItem, EnzymeOut
from api.models import Metabolite, Enzyme

# Create FastAPI app
app = FastAPI(
    title="Metabolome Handbook API",
    description="Educational metabolomics reference API for biochemistry and chemistry courses",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=dict)
async def root():
    """Корневой endpoint с информацией о приложении"""
    return {
        "message": "Метаболомный справочник API",
        "version": "1.0.0",
        "description": "Учебное API для поиска метаболитов и аннотации данных LC-MS",
        "endpoints": {
            "/health": "Проверка состояния сервера",
            "/metabolites/search": "Поиск метаболитов",
            "/annotate/csv": "Аннотация CSV файлов"
        }
    }

@app.get("/health", response_model=dict)
async def health_check(session: AsyncSession = Depends(get_db)):
    """Проверка состояния сервера и базы данных"""
    try:
        # Подсчитываем количество метаболитов
        result = await session.execute(select(func.count(Metabolite.id)))
        metabolites_count = result.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
            "metabolites_count": metabolites_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/metabolites/search", response_model=SearchResponse)
async def search_metabolites(
    q: Optional[str] = Query(default=None, description="Название или химическая формула"),
    mass: Optional[float] = Query(default=None, description="Масса (m/z) для поиска"),
    tol_ppm: float = Query(default=10.0, description="Допуск в ppm для поиска по массе"),
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    page_size: int = Query(default=50, ge=1, le=200, description="Размер страницы"),
    session: AsyncSession = Depends(get_db)
):
    """Поиск метаболитов по названию, формуле или массе"""
    try:
            # Базовый запрос
            query = select(Metabolite).options(
                selectinload(Metabolite.class_),
                selectinload(Metabolite.pathways),
                selectinload(Metabolite.enzymes)
            )
            
            # Применяем фильтры
            if q:
                # Поиск по названию (английскому и русскому) или формуле (регистронезависимый)
                # Используем lower() для регистронезависимого поиска в SQLite
                query = query.where(
                    or_(
                        func.lower(Metabolite.name).like(f"%{q.lower()}%"),
                        func.lower(Metabolite.name_ru).like(f"%{q.lower()}%"),
                        func.lower(Metabolite.formula).like(f"%{q.lower()}%"),
                        func.lower(Metabolite.hmdb_id).like(f"%{q.lower()}%"),
                        func.lower(Metabolite.kegg_id).like(f"%{q.lower()}%"),
                        func.lower(Metabolite.chebi_id).like(f"%{q.lower()}%"),
                        func.lower(Metabolite.pubchem_cid).like(f"%{q.lower()}%")
                    )
                )
            
            if mass is not None:
                # Поиск по массе с допуском
                delta = mass * tol_ppm / 1e6
                low_mass = mass - delta
                high_mass = mass + delta
                query = query.where(Metabolite.exact_mass.between(low_mass, high_mass))
            
            # Подсчитываем общее количество
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # Применяем пагинацию
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Выполняем запрос
            result = await session.execute(query)
            metabolites = result.scalars().all()
            
            # Формируем ответ
            metabolite_list = []
            for met in metabolites:
                met_data = {
                    "id": met.id,
                    "name": met.name,
                    "formula": met.formula,
                    "exact_mass": met.exact_mass,
                    "hmdb_id": met.hmdb_id,
                    "chebi_id": met.chebi_id,
                    "kegg_id": met.kegg_id,
                    "pubchem_cid": met.pubchem_cid,
                    "class_id": met.class_id,
                    "class_name": met.class_.name if met.class_ else None,
                    "pathways": [p.name for p in met.pathways],
                    "enzymes": [e.name for e in met.enzymes]
                }
                metabolite_list.append(met_data)
            
            return SearchResponse(
                metabolites=metabolite_list,
                total=total,
                page=page,
                page_size=page_size
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")

@app.get("/metabolites/{metabolite_id}", response_model=MetaboliteOut)
async def get_metabolite(metabolite_id: int, session: AsyncSession = Depends(get_db)):
    """Получение информации о конкретном метаболите по ID"""
    try:
            query = select(Metabolite).options(
                selectinload(Metabolite.class_),
                selectinload(Metabolite.pathways),
                selectinload(Metabolite.enzymes)
            ).where(Metabolite.id == metabolite_id)
            
            result = await session.execute(query)
            metabolite = result.scalar_one_or_none()
            
            if not metabolite:
                raise HTTPException(status_code=404, detail="Метаболит не найден")
            
            return MetaboliteOut(
                id=metabolite.id,
                name=metabolite.name,
                name_ru=metabolite.name_ru,
                formula=metabolite.formula,
                exact_mass=metabolite.exact_mass,
                hmdb_id=metabolite.hmdb_id,
                chebi_id=metabolite.chebi_id,
                kegg_id=metabolite.kegg_id,
                pubchem_cid=metabolite.pubchem_cid,
                class_id=metabolite.class_id,
                class_name=metabolite.class_.name_ru if metabolite.class_ and metabolite.class_.name_ru else (metabolite.class_.name if metabolite.class_ else None),
                pathways=[p.name_ru if p.name_ru else p.name for p in metabolite.pathways],
                enzymes=[e.name_ru if e.name_ru else e.name for e in metabolite.enzymes]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения метаболита: {str(e)}")

@app.post("/annotate/csv", response_model=AnnotationResponse)
async def annotate_csv(
    file: UploadFile = File(..., description="CSV файл с данными"),
    mz_column: str = Query(default="mz", description="Название столбца с массами (m/z)"),
    tol_ppm: float = Query(default=10.0, description="Допуск в ppm для аннотации"),
    max_candidates: int = Query(default=10, description="Максимальное количество кандидатов на пик"),
    session: AsyncSession = Depends(get_db)
):
    """Аннотация CSV файла с пиками LC-MS"""
    try:
        # Проверяем тип файла
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Файл должен быть в формате CSV")
        
        # Читаем содержимое файла (максимум 10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Файл слишком большой (максимум 10MB)")
        
        content = await file.read()
        
        try:
            # Парсим CSV
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка чтения CSV файла: {str(e)}")
        
        # Проверяем наличие столбца с массами
        if mz_column not in df.columns:
            available_columns = ", ".join(df.columns)
            raise HTTPException(
                status_code=400, 
                detail=f"Столбец '{mz_column}' не найден. Доступные столбцы: {available_columns}"
            )
        
        # Извлекаем массы
        try:
            mz_values = df[mz_column].astype(float).tolist()
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Ошибка преобразования столбца '{mz_column}' в числа: {str(e)}"
            )
        
        # Аннотируем каждый пик
        annotation_items = []
        annotated_count = 0
        
        for mz in mz_values:
                # Поиск кандидатов по массе
                delta = mz * tol_ppm / 1e6
                low_mass = mz - delta
                high_mass = mz + delta
                
                query = select(Metabolite).options(
                    selectinload(Metabolite.class_)
                ).where(
                    Metabolite.exact_mass.between(low_mass, high_mass)
                ).order_by(
                    func.abs(Metabolite.exact_mass - mz)
                ).limit(max_candidates)
                
                result = await session.execute(query)
                candidates = result.scalars().all()
                
                # Формируем кандидатов
                candidate_list = []
                for candidate in candidates:
                    mass_error_da = candidate.exact_mass - mz
                    mass_error_ppm = (mass_error_da / mz) * 1e6
                    
                    candidate_data = AnnotationCandidate(
                        metabolite=MetaboliteOut(
                            id=candidate.id,
                            name=candidate.name,
                            formula=candidate.formula,
                            exact_mass=candidate.exact_mass,
                            hmdb_id=candidate.hmdb_id,
                            chebi_id=candidate.chebi_id,
                            kegg_id=candidate.kegg_id,
                            pubchem_cid=candidate.pubchem_cid,
                            class_id=candidate.class_id,
                            class_name=candidate.class_.name if candidate.class_ else None,
                            pathways=[],
                            enzymes=[]
                        ),
                        mass_error_ppm=round(mass_error_ppm, 2),
                        mass_error_da=round(mass_error_da, 6)
                    )
                    candidate_list.append(candidate_data)
                
                # Лучший кандидат (первый в списке, если есть)
                best_match = candidate_list[0] if candidate_list else None
                if best_match:
                    annotated_count += 1
                
                # Создаем элемент аннотации
                item = AnnotationItem(
                    mz=round(mz, 6),
                    candidates=candidate_list,
                    best_match=best_match
                )
                annotation_items.append(item)
        
        return AnnotationResponse(
            items=annotation_items,
            total_peaks=len(mz_values),
            annotated_peaks=annotated_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка аннотации: {str(e)}")

@app.post("/annotate/mz-list", response_model=AnnotationResponse)
async def annotate_mz_list(
    mz_list: List[float] = Body(..., description="Список масс (m/z) для аннотации"),
    tol_ppm: float = Query(default=10.0, description="Допуск в ppm для аннотации"),
    max_candidates: int = Query(default=10, description="Максимальное количество кандидатов на пик"),
    session: AsyncSession = Depends(get_db)
):
    """Аннотация списка масс (m/z)"""
    try:
        if not mz_list:
            raise HTTPException(status_code=400, detail="Список масс не может быть пустым")
        
        # Аннотируем каждый пик
        annotation_items = []
        annotated_count = 0
        
        for mz in mz_list:
                # Поиск кандидатов по массе
                delta = mz * tol_ppm / 1e6
                low_mass = mz - delta
                high_mass = mz + delta
                
                query = select(Metabolite).options(
                    selectinload(Metabolite.class_)
                ).where(
                    Metabolite.exact_mass.between(low_mass, high_mass)
                ).order_by(
                    func.abs(Metabolite.exact_mass - mz)
                ).limit(max_candidates)
                
                result = await session.execute(query)
                candidates = result.scalars().all()
                
                # Формируем кандидатов
                candidate_list = []
                for candidate in candidates:
                    mass_error_da = candidate.exact_mass - mz
                    mass_error_ppm = (mass_error_da / mz) * 1e6
                    
                    candidate_data = AnnotationCandidate(
                        metabolite=MetaboliteOut(
                            id=candidate.id,
                            name=candidate.name,
                            formula=candidate.formula,
                            exact_mass=candidate.exact_mass,
                            hmdb_id=candidate.hmdb_id,
                            chebi_id=candidate.chebi_id,
                            kegg_id=candidate.kegg_id,
                            pubchem_cid=candidate.pubchem_cid,
                            class_id=candidate.class_id,
                            class_name=candidate.class_.name if candidate.class_ else None,
                            pathways=[],
                            enzymes=[]
                        ),
                        mass_error_ppm=round(mass_error_ppm, 2),
                        mass_error_da=round(mass_error_da, 6)
                    )
                    candidate_list.append(candidate_data)
                
                # Лучший кандидат (первый в списке, если есть)
                best_match = candidate_list[0] if candidate_list else None
                if best_match:
                    annotated_count += 1
                
                # Создаем элемент аннотации
                item = AnnotationItem(
                    mz=round(mz, 6),
                    candidates=candidate_list,
                    best_match=best_match
                )
                annotation_items.append(item)
        
        return AnnotationResponse(
            items=annotation_items,
            total_peaks=len(mz_list),
            annotated_peaks=annotated_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка аннотации: {str(e)}")

@app.get("/export/csv")
async def export_metabolites_csv(
    format: str = Query(default="csv", regex="^(csv|excel)$", description="Формат экспорта"),
    session: AsyncSession = Depends(get_db)
):
    """Экспорт всех метаболитов в CSV или Excel формат"""
    try:
            query = select(Metabolite).options(
                selectinload(Metabolite.class_),
                selectinload(Metabolite.pathways),
                selectinload(Metabolite.enzymes)
            )
            
            result = await session.execute(query)
            metabolites = result.scalars().all()
            
            # Формируем данные для экспорта
            export_data = []
            for met in metabolites:
                export_data.append({
                    "ID": met.id,
                    "Название": met.name,
                    "Формула": met.formula,
                    "Точная масса": met.exact_mass,
                    "HMDB ID": met.hmdb_id,
                    "ChEBI ID": met.chebi_id,
                    "KEGG ID": met.kegg_id,
                    "PubChem CID": met.pubchem_cid,
                    "Класс": met.class_.name if met.class_ else "",
                    "Пути": "; ".join([p.name for p in met.pathways]),
                    "Ферменты": "; ".join([e.name for e in met.enzymes])
                })
            
            df = pd.DataFrame(export_data)
            
            if format == "csv":
                # CSV экспорт
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                csv_data = csv_buffer.getvalue()
                
                return Response(
                    content=csv_data,
                    media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=metabolites.csv"}
                )
            else:
                # Excel экспорт
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Метаболиты', index=False)
                excel_data = excel_buffer.getvalue()
                
                return Response(
                    content=excel_data,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=metabolites.xlsx"}
                )
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")

@app.get("/enzymes/search", response_model=dict)
async def search_enzymes(
    q: Optional[str] = Query(default=None, description="Название, EC номер или организм"),
    organism_type: Optional[str] = Query(default=None, description="Тип организма (plant, animal, bacteria)"),
    ec_number: Optional[str] = Query(default=None, description="EC номер"),
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    page_size: int = Query(default=50, ge=1, le=200, description="Размер страницы"),
    session: AsyncSession = Depends(get_db)
):
    """Поиск ферментов по различным критериям"""
    try:
        # Базовый запрос
        query = select(Enzyme)
        
        # Применяем фильтры
        if q:
            # Поиск по названию (английскому и русскому), EC номеру, организму (регистронезависимый)
            # Используем lower() для регистронезависимого поиска в SQLite
            query = query.where(
                or_(
                    func.lower(Enzyme.name).like(f"%{q.lower()}%"),
                    func.lower(Enzyme.name_ru).like(f"%{q.lower()}%"),
                    func.lower(Enzyme.ec_number).like(f"%{q.lower()}%"),
                    func.lower(Enzyme.organism).like(f"%{q.lower()}%"),
                    func.lower(Enzyme.protein_name).like(f"%{q.lower()}%"),
                    func.lower(Enzyme.gene_name).like(f"%{q.lower()}%"),
                    func.lower(Enzyme.family).like(f"%{q.lower()}%")
                )
            )
        
        if organism_type:
            query = query.where(func.lower(Enzyme.organism_type).like(f"%{organism_type.lower()}%"))
        
        if ec_number:
            query = query.where(func.lower(Enzyme.ec_number).like(f"%{ec_number.lower()}%"))
        
        # Подсчет общего количества
        count_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()
        
        # Пагинация
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Выполняем запрос
        result = await session.execute(query)
        enzymes = result.scalars().all()
        
        # Формируем результат
        enzyme_list = []
        for enzyme in enzymes:
            enzyme_data = {
                "id": enzyme.id,
                "name": enzyme.name_ru if enzyme.name_ru else enzyme.name,
                "name_en": enzyme.name,
                "name_ru": enzyme.name_ru,
                "ec_number": enzyme.ec_number,
                "organism": enzyme.organism,
                "organism_type": enzyme.organism_type,
                "family": enzyme.family,
                "description": enzyme.description,
                "molecular_weight": enzyme.molecular_weight,
                "optimal_ph": enzyme.optimal_ph,
                "optimal_temperature": enzyme.optimal_temperature,
                "protein_name": enzyme.protein_name,
                "gene_name": enzyme.gene_name,
                "tissue_specificity": enzyme.tissue_specificity,
                "subcellular_location": enzyme.subcellular_location,
                "uniprot_id": enzyme.uniprot_id
            }
            enzyme_list.append(enzyme_data)
        
        return {
            "enzymes": enzyme_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка поиска ферментов: {str(e)}")

@app.get("/enzymes/{enzyme_id}", response_model=dict)
async def get_enzyme(enzyme_id: int, session: AsyncSession = Depends(get_db)):
    """Получение информации о конкретном ферменте по ID"""
    try:
        query = select(Enzyme).where(Enzyme.id == enzyme_id)
        result = await session.execute(query)
        enzyme = result.scalar_one_or_none()
        
        if not enzyme:
            raise HTTPException(status_code=404, detail="Фермент не найден")
        
        return {
            "id": enzyme.id,
            "name": enzyme.name,
            "ec_number": enzyme.ec_number,
            "organism": enzyme.organism,
            "organism_type": enzyme.organism_type,
            "family": enzyme.family,
            "description": enzyme.description,
            "molecular_weight": enzyme.molecular_weight,
            "optimal_ph": enzyme.optimal_ph,
            "optimal_temperature": enzyme.optimal_temperature,
            "protein_name": enzyme.protein_name,
            "gene_name": enzyme.gene_name,
            "tissue_specificity": enzyme.tissue_specificity,
            "subcellular_location": enzyme.subcellular_location,
            "uniprot_id": enzyme.uniprot_id,
            "brenda_id": enzyme.brenda_id,
            "kegg_enzyme_id": enzyme.kegg_enzyme_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения фермента: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
