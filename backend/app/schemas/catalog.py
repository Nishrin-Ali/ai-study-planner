from typing import List, Optional
from pydantic import BaseModel


class BranchSchema(BaseModel):
    code: str
    name: str
    semesters: List[int]


class CourseSchema(BaseModel):
    code: str
    title: str
    branch: str
    semester: int
    scheme: str
    credits: Optional[float] = None
    verified: Optional[bool] = True
    source_url: Optional[str] = None


class CatalogResponse(BaseModel):
    university: str
    schemes: List[str]
    branches: List[BranchSchema]
    courses: List[CourseSchema]
