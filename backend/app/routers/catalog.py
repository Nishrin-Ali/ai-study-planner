"""VTU Academic Catalog Router."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["catalog"])

CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "vtu_catalog.json"


@router.get("/catalog")
def get_vtu_catalog():
    """Returns available VTU branches, years, semesters, schemes, and courses."""
    if not CATALOG_PATH.exists():
        raise HTTPException(status_code=404, detail="Catalog file not found.")

    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed loading catalog: {exc}")
