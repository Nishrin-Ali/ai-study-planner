import json
from pathlib import Path
import pytest
from app.schemas.catalog import CatalogResponse, CourseSchema


CATALOG_FILE = Path(__file__).resolve().parent.parent / "data" / "vtu_catalog.json"


def test_catalog_file_exists_and_valid():
    assert CATALOG_FILE.exists(), "vtu_catalog.json must exist in backend/data"
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate against Pydantic schema
    catalog = CatalogResponse(**data)
    assert catalog.university == "Visvesvaraya Technological University (VTU)"
    assert len(catalog.schemes) >= 3
    assert "2022" in catalog.schemes
    assert "2021" in catalog.schemes
    assert "2018" in catalog.schemes
    assert len(catalog.branches) >= 8
    assert len(catalog.courses) > 100


def test_catalog_no_duplicates_and_non_empty_fields():
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen = set()
    for c in data["courses"]:
        code = c.get("code")
        title = c.get("title")
        scheme = c.get("scheme")
        branch = c.get("branch")
        sem = c.get("semester")

        assert code and len(code.strip()) >= 3, f"Empty or invalid code: {code}"
        assert title and len(title.strip()) > 0, f"Empty title for {code}"
        assert scheme in ["2022", "2021", "2018"], f"Invalid scheme for {code}: {scheme}"
        assert 1 <= sem <= 8, f"Invalid semester for {code}: {sem}"
        assert c.get("verified") is True, f"Course {code} should be marked verified"

        key = (scheme, sem, code)
        assert key not in seen, f"Duplicate course in same (scheme, sem): {key}"
        seen.add(key)
