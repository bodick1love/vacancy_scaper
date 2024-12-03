from enum import Enum


class UserState(str, Enum):
    ASKING_KEYWORDS = "asking_keywords"
    ASKING_REGION = "asking_region"
    ASKING_SALARY = "asking_salary"
    ASKING_EXPERIENCE = "asking_experience"
    ASKING_SALARY_FROM = "asking_salary_from"
    ASKING_SALARY_TO = "asking_salary_to"
    FREE = "free"
