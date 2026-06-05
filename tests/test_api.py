import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import Base, get_db
from app.config import BASIC_AUTH_USERNAME, BASIC_AUTH_PASSWORD

# Set up SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the database dependency in FastAPI
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create a TestClient
client = TestClient(app)

# Helper for Basic Authentication headers
AUTH_HEADER = {"Authorization": f"Basic YWRtaW46dHJhdmVsMTIz"}  
WRONG_AUTH_HEADER = {"Authorization": f"Basic YWRtaW46d3Jvbmc="}  

@pytest.fixture(autouse=True)
def setup_database():
    # Create all tables before test
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after test to keep db clean
    Base.metadata.drop_all(bind=engine)


# Authentication Tests

def test_auth_required():
    # No auth header
    response = client.get("/api/v1/projects")
    assert response.status_code == 401

    # Wrong credentials
    response = client.get("/api/v1/projects", headers=WRONG_AUTH_HEADER)
    assert response.status_code == 401

    # Correct credentials
    response = client.get("/api/v1/projects", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == []

def test_user_registration_and_auth():
    # Register a new user
    register_payload = {
        "username": "newtraveler",
        "password": "secretpassword"
    }
    response = client.post("/api/v1/register", json=register_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newtraveler"
    assert "id" in data

    # Registering with duplicate username
    response = client.post("/api/v1/register", json=register_payload)
    assert response.status_code == 400
    assert "Username is already taken" in response.json()["detail"]

    # Accessing project with newly registered user credentials -> succeeds
    new_auth_header = {"Authorization": "Basic bmV3dHJhdmVsZXI6c2VjcmV0cGFzc3dvcmQ="}  
    response = client.get("/api/v1/projects", headers=new_auth_header)
    assert response.status_code == 200



# Projects CRUD Tests

def test_create_project_without_places():
    payload = {
        "name": "Summer in Paris",
        "description": "Trip to Paris",
        "start_date": "2026-07-01"
    }
    response = client.post("/api/v1/projects", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["start_date"] == payload["start_date"]
    assert data["is_completed"] is False
    assert len(data["places"]) == 0
    assert "id" in data


@patch("app.routers.projects.fetch_artwork_by_id", new_callable=AsyncMock)
def test_create_project_with_places(mock_fetch):
    # Mock successful API calls
    mock_fetch.side_effect = lambda artwork_id: {
        "id": artwork_id,
        "title": f"Mock Artwork {artwork_id}"
    } if artwork_id in [101, 102] else None

    payload = {
        "name": "Museum Tour",
        "description": "Visiting museums",
        "start_date": "2026-08-15",
        "places": [
            {"external_id": 101, "notes": "Beautiful painting"},
            {"external_id": 102, "notes": "Must see sculpture"}
        ]
    }
    response = client.post("/api/v1/projects", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Museum Tour"
    assert len(data["places"]) == 2
    assert data["places"][0]["external_id"] == 101
    assert data["places"][0]["title"] == "Mock Artwork 101"
    assert data["places"][0]["notes"] == "Beautiful painting"


@patch("app.routers.projects.fetch_artwork_by_id", new_callable=AsyncMock)
def test_create_project_with_invalid_place(mock_fetch):
    # Mock API returning None
    mock_fetch.return_value = None

    payload = {
        "name": "Invalid Project",
        "places": [
            {"external_id": 9999}
        ]
    }
    response = client.post("/api/v1/projects", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 400
    assert "does not exist in the external API" in response.json()["detail"]


def test_create_project_with_duplicate_places():
    payload = {
        "name": "Duplicate Place Test",
        "places": [
            {"external_id": 101},
            {"external_id": 101}
        ]
    }
    response = client.post("/api/v1/projects", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 400
    assert "Duplicate external place IDs found" in response.json()["detail"]


def test_create_project_limit_validation():
    # Try creating project with 11 places(limit is 10)
    payload = {
        "name": "Too Many Places",
        "places": [{"external_id": i} for i in range(1, 12)]
    }
    response = client.post("/api/v1/projects", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 422  # Pydantic validation error code
    assert "between 1 and 10 places" in response.text


def test_list_and_get_projects():
    # Setup projects
    p1 = client.post("/api/v1/projects", json={"name": "Trip A"}, headers=AUTH_HEADER).json()
    p2 = client.post("/api/v1/projects", json={"name": "Trip B"}, headers=AUTH_HEADER).json()

    # List
    response = client.get("/api/v1/projects", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Get single
    response = client.get(f"/api/v1/projects/{p1['id']}", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json()["name"] == "Trip A"


def test_update_project():
    project = client.post("/api/v1/projects", json={"name": "Original Name"}, headers=AUTH_HEADER).json()
    
    payload = {
        "name": "Updated Name",
        "description": "New description"
    }
    response = client.put(f"/api/v1/projects/{project['id']}", json=payload, headers=AUTH_HEADER)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New description"


# Completion Logic Tests

@patch("app.routers.places.fetch_artwork_by_id", new_callable=AsyncMock)
def test_add_place_to_project(mock_fetch):
    # Mock API response
    mock_fetch.return_value = {"id": 201, "title": "Mona Lisa"}

    # Create project first
    project = client.post("/api/v1/projects", json={"name": "Paris Trip"}, headers=AUTH_HEADER).json()

    # Add place
    payload = {"external_id": 201, "notes": "Must take a photo"}
    response = client.post(f"/api/v1/projects/{project['id']}/places", json=payload, headers=AUTH_HEADER)
    
    assert response.status_code == 201
    data = response.json()
    assert data["external_id"] == 201
    assert data["title"] == "Mona Lisa"
    assert data["is_visited"] is False

    # Check project completed status(should be false since place is not visited)
    proj_response = client.get(f"/api/v1/projects/{project['id']}", headers=AUTH_HEADER).json()
    assert proj_response["is_completed"] is False


@patch("app.routers.places.fetch_artwork_by_id", new_callable=AsyncMock)
def test_project_completion_logic(mock_fetch):
    mock_fetch.side_effect = lambda artwork_id: {
        "id": artwork_id,
        "title": f"Artwork {artwork_id}"
    }

    # Create project
    project = client.post("/api/v1/projects", json={"name": "Gallery Tour"}, headers=AUTH_HEADER).json()

    # Add 2 places
    p1 = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 301}, headers=AUTH_HEADER).json()
    p2 = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 302}, headers=AUTH_HEADER).json()

    # Mark first place as visited
    response = client.patch(f"/api/v1/projects/{project['id']}/places/{p1['id']}", json={"is_visited": True}, headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json()["is_visited"] is True

    # Check project completed status(should still be False because p2 is not visited)
    proj_response = client.get(f"/api/v1/projects/{project['id']}", headers=AUTH_HEADER).json()
    assert proj_response["is_completed"] is False

    # Mark second place as visited
    client.patch(f"/api/v1/projects/{project['id']}/places/{p2['id']}", json={"is_visited": True}, headers=AUTH_HEADER)

    # Check project completed status(should now be True because all places are visited)
    proj_response = client.get(f"/api/v1/projects/{project['id']}", headers=AUTH_HEADER).json()
    assert proj_response["is_completed"] is True

    # Mark a place back to unvisited, completion should become False
    client.patch(f"/api/v1/projects/{project['id']}/places/{p2['id']}", json={"is_visited": False}, headers=AUTH_HEADER)
    proj_response = client.get(f"/api/v1/projects/{project['id']}", headers=AUTH_HEADER).json()
    assert proj_response["is_completed"] is False


@patch("app.routers.places.fetch_artwork_by_id", new_callable=AsyncMock)
def test_cannot_delete_project_with_visited_places(mock_fetch):
    mock_fetch.return_value = {"id": 401, "title": "Artwork"}

    project = client.post("/api/v1/projects", json={"name": "Historical Tour"}, headers=AUTH_HEADER).json()
    place = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 401}, headers=AUTH_HEADER).json()

    # Deletion should work because the place is NOT visited
    client.patch(f"/api/v1/projects/{project['id']}/places/{place['id']}", json={"is_visited": True}, headers=AUTH_HEADER)
    
    # Try deleting
    response = client.delete(f"/api/v1/projects/{project['id']}", headers=AUTH_HEADER)
    assert response.status_code == 400
    assert "Cannot delete project because some of its places are already marked as visited" in response.json()["detail"]

    # Mark it as unvisited
    client.patch(f"/api/v1/projects/{project['id']}/places/{place['id']}", json={"is_visited": False}, headers=AUTH_HEADER)

    # Try deleting
    response = client.delete(f"/api/v1/projects/{project['id']}", headers=AUTH_HEADER)
    assert response.status_code == 204


@patch("app.routers.places.fetch_artwork_by_id", new_callable=AsyncMock)
def test_limit_10_places_per_project(mock_fetch):
    mock_fetch.side_effect = lambda artwork_id: {"id": artwork_id, "title": f"Artwork {artwork_id}"}
    
    project = client.post("/api/v1/projects", json={"name": "Max Limits Test"}, headers=AUTH_HEADER).json()

    # Add 10 places
    for i in range(1, 11):
        resp = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": i}, headers=AUTH_HEADER)
        assert resp.status_code == 201

    # Adding the 11th place should fail
    resp = client.post(f"/api/v1/projects/{project['id']}/places", json={"external_id": 11}, headers=AUTH_HEADER)
    assert resp.status_code == 400
    assert "maximum limit of 10 places" in resp.json()["detail"]
