import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.papers.repetition import ensure_seeds_loaded
from app.database import SessionLocal


client = TestClient(app)


def test_paper_file_endpoint_serves_pdf():
    db = SessionLocal()
    try:
        ensure_seeds_loaded(db, "BCS304", "2022")
    finally:
        db.close()

    # Query cached papers to get valid paper ID
    res = client.get("/api/papers?course_code=BCS304&scheme=2022")
    assert res.status_code == 200
    papers = res.json()
    assert len(papers) > 0

    first_paper_id = papers[0]["id"]
    file_res = client.get(f"/api/papers/{first_paper_id}/file")
    assert file_res.status_code == 200
    assert file_res.headers.get("content-type") == "application/pdf"
    assert file_res.content.startswith(b"%PDF")


def test_paper_file_endpoint_404_on_invalid_id():
    res = client.get("/api/papers/non_existent_paper_id_xyz/file")
    assert res.status_code == 404
