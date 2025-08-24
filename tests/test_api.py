import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.main import app
from api.database.base import Base, get_db
from api.models import Metabolite, Class

# Test database URL
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def test_client(test_db):
    """Create test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="function")
def sample_metabolites(test_db):
    """Create sample metabolites for testing"""
    # Create test class
    test_class = Class(name="Test Class")
    test_db.add(test_class)
    test_db.flush()
    
    # Create test metabolites
    metabolites = [
        Metabolite(
            name="Glucose",
            formula="C6H12O6",
            exact_mass=180.063388,
            hmdb_id="HMDB0000122",
            class_id=test_class.id
        ),
        Metabolite(
            name="Pyruvate",
            formula="C3H4O3",
            exact_mass=88.016043,
            hmdb_id="HMDB0000243",
            class_id=test_class.id
        )
    ]
    
    for metabolite in metabolites:
        test_db.add(metabolite)
    
    test_db.commit()
    return metabolites

@pytest.mark.asyncio
async def test_root_endpoint(test_client):
    """Test root endpoint"""
    response = await test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data

@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    """Test health endpoint"""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

@pytest.mark.asyncio
async def test_search_by_name(test_client, sample_metabolites):
    """Test metabolite search by name"""
    response = await test_client.get("/metabolites/search?q=glucose")
    assert response.status_code == 200
    data = response.json()
    assert "metabolites" in data
    assert len(data["metabolites"]) > 0
    assert data["metabolites"][0]["name"] == "Glucose"

@pytest.mark.asyncio
async def test_search_by_mass(test_client, sample_metabolites):
    """Test metabolite search by mass"""
    response = await test_client.get("/metabolites/search?mass=180.063&tol_ppm=10")
    assert response.status_code == 200
    data = response.json()
    assert "metabolites" in data
    assert len(data["metabolites"]) > 0
    assert "Glucose" in [m["name"] for m in data["metabolites"]]

@pytest.mark.asyncio
async def test_search_no_parameters(test_client):
    """Test search without parameters should fail"""
    response = await test_client.get("/metabolites/search")
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_get_metabolite_by_id(test_client, sample_metabolites):
    """Test get metabolite by ID"""
    metabolite_id = sample_metabolites[0].id
    response = await test_client.get(f"/metabolites/{metabolite_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Glucose"
    assert data["formula"] == "C6H12O6"

@pytest.mark.asyncio
async def test_get_metabolite_not_found(test_client):
    """Test get metabolite with non-existent ID"""
    response = await test_client.get("/metabolites/999999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_annotate_mz_list(test_client, sample_metabolites):
    """Test m/z list annotation"""
    mz_values = [180.063, 88.016]
    response = await test_client.post("/annotate/mz-list", json=mz_values)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["total_peaks"] == 2

@pytest.mark.asyncio
async def test_annotate_empty_list(test_client):
    """Test annotation with empty list should fail"""
    response = await test_client.post("/annotate/mz-list", json=[])
    assert response.status_code == 400

if __name__ == "__main__":
    pytest.main([__file__])
