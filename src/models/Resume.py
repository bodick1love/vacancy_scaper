from typing import Optional
from pydantic import BaseModel


class Experience(BaseModel):
    position: Optional[str]
    duration: Optional[str]
    details: Optional[str]


class Resume(BaseModel):
    href: str
    salary_expectation: Optional[str]
    experience: Optional[list[Experience]]
    filling_percentage: int

    def __lt__(self, other):
        return self.filling_percentage < other.filling_percentage
