from fastapi import APIRouter, Depends

from app.agents.assessment import TemplateAssessmentAgent
from app.agents.coordinator import RuleBasedAcademicCoordinator
from app.agents.profile import RuleBasedProfileAgent
from app.config import settings
from app.data.mock_source import MockAcademicDataSource
from app.domain.academic.service import AcademicService
from app.integrations.fenghuo import MockFenghuoAdapter
from app.integrations.wendian import MockWendianAdapter
from app.schemas.requests import AcademicAnalyzeRequest
from app.schemas.responses import AcademicAnalyzeResponse, HealthResponse
from app.storage.assessment_store import JsonAssessmentStore

router = APIRouter()


def get_service() -> AcademicService:
    current = settings()
    return AcademicService(
        current,
        MockAcademicDataSource(current.data_file),
        RuleBasedAcademicCoordinator(),
        RuleBasedProfileAgent(),
        MockWendianAdapter(),
        MockFenghuoAdapter(),
        TemplateAssessmentAgent(),
        JsonAssessmentStore(current.var_dir),
    )


@router.get("/health", response_model=HealthResponse, tags=["元数据"])
def health() -> HealthResponse:
    return HealthResponse()


@router.post(
    "/api/v1/agents/academic/analyze",
    response_model=AcademicAnalyzeResponse,
    tags=["学业分析"],
    responses={
        403: {"description": "无数据权限"},
        404: {"description": "学生不存在"},
        409: {"description": "request_id与已有任务冲突"},
        503: {"description": "关键数据不可用"},
    },
)
def analyze(
    request: AcademicAnalyzeRequest,
    service: AcademicService = Depends(get_service),
) -> AcademicAnalyzeResponse:
    return service.analyze(request)
