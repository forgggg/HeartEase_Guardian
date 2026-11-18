from typing import Literal

from pydantic import BaseModel, Field, model_validator


class StudentScope(BaseModel):
    type: Literal["single", "batch"] = "single"
    student_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_mvp_scope(self):
        if self.type != "single" or len(self.student_ids) != 1:
            raise ValueError("第一阶段仅支持单个学生")
        return self


class AnalyzeOptions(BaseModel):
    query_regulations: bool = True
    run_warning_detection: bool = True
    max_suggestions: int = Field(default=3, ge=1, le=3)


class AcademicAnalyzeRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=100)
    counselor_id: str = Field(min_length=1, max_length=100)
    student_scope: StudentScope
    term: str = Field(pattern=r"^\d{4}-(spring|autumn)$")
    task_type: Literal["academic_risk_analysis"]
    requirement: str = Field(min_length=1, max_length=1000)
    focus: list[Literal["grades", "attendance", "credits"]] = Field(min_length=1)
    options: AnalyzeOptions = Field(default_factory=AnalyzeOptions)
