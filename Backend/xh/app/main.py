from fastapi import FastAPI

from app.api.academic import router
from app.errors import install as install_errors

app = FastAPI(
    title="学海 · 学业辅导模块",
    version="0.1.0",
    description="面向主智能体的单学生、单学期学业风险分析服务。",
)
install_errors(app)
app.include_router(router)
