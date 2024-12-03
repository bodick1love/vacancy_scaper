from typing import Optional

from pydantic import BaseModel


class SearchOptions(BaseModel):
    search: str
    region: Optional[str]
    salary_from: Optional[int]
    salary_to: Optional[int]
    experience: Optional[list[str]]
