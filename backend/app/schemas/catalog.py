from typing import List
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


class CatalogResponse(BaseModel):
    university: str
    schemes: List[str]
    branches: List[BranchSchema]
    courses: List[CourseSchema]
