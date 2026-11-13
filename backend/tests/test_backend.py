import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.notes import detect_modules_from_text


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Visvesvaraya" in data["university"]
    assert "gemini_configured" in data


def test_get_catalog(client):
    response = client.get("/api/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "schemes" in data
    assert "2022" in data["schemes"]
    assert len(data["branches"]) > 0
    assert any(b["code"] == "CSE" for b in data["branches"])
    assert any(c["code"] == "BCS304" for c in data["courses"])


def test_create_and_fetch_plan(client):
    # Test plan creation
    payload = {
        "course_code": "BCS304",
        "course_title": "Data Structures and Applications",
        "branch": "CSE",
        "semester": 3,
        "scheme": "2022",
        "num_modules": 3,
        "num_days": 4,
        "only_important_questions": True,
    }
    create_res = client.post("/api/plan", json=payload)
    assert create_res.status_code == 201
    plan_data = create_res.json()
    assert "plan_id" in plan_data
    assert plan_data["course_code"] == "BCS304"
    assert len(plan_data["days"]) == 4
    assert len(plan_data["answers"]) > 0

    plan_id = plan_data["plan_id"]

    # Test plan retrieval
    get_res = client.get(f"/api/plan/{plan_id}")
    assert get_res.status_code == 200
    fetched_data = get_res.json()
    assert fetched_data["plan_id"] == plan_id
    assert len(fetched_data["days"]) == 4

    # Test toggle completion of an item
    first_item = fetched_data["days"][0]["items"][0]
    item_id = first_item["id"]
    patch_res = client.patch(
        f"/api/plan/{plan_id}/items/{item_id}",
        json={"is_completed": True}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_completed"] is True


def test_detect_modules_from_text():
    sample_text = """
    VTU Model Question Paper
    MODULE - 1
    Explain linear and non-linear data structures.
    MODULE 2
    Write C code for singly linked list insertion.
    Unit 3
    Explain binary search trees.
    """
    modules = detect_modules_from_text(sample_text)
    assert 1 in modules
    assert 2 in modules
    assert 3 in modules
