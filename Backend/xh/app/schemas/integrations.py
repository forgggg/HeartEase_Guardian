from pydantic import BaseModel

from .responses import Analysis, Recommendation, RegulationResult


class WendianRequest(BaseModel):
    request_id: str
    domain: str = "academic"
    query: str
    student_facts: dict


class WendianResponse(BaseModel):
    status: str
    regulations: list[RegulationResult]


class FenghuoRequest(BaseModel):
    request_id: str
    facts: dict
    findings: list[dict]
    regulations: list[dict]


class LLMResult(BaseModel):
    analysis: Analysis
    recommendations: list[Recommendation]
