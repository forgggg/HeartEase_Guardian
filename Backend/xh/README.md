# 学海（学业辅导）第一阶段 MVP

本目录提供面向主智能体的单学生、单学期学业分析服务。第一阶段使用完全脱敏的 Mock 数据、Mock 问典、Mock 烽火和 Mock LLM，不连接真实教务系统，也不会自动执行辅导员处置动作。

## 已实现

- `POST /api/v1/agents/academic/analyze` 固定请求/响应契约
- 单学生、单学期与辅导员数据范围校验
- 成绩、挂科、考勤、学分、补考和重修指标
- 四条带版本、证据、阈值和缺失事实的确定性技术规则
- 可替换的问典、烽火抽象接口及离线 Mock
- 主智能体、学生画像智能体和学业问题研判智能体的固定接口及离线实现
- 外部依赖失败时返回 `partial`，LLM 使用程序模板降级
- 评估快照、请求幂等和 JSONL 审计
- 自动化单元测试、API 测试与失败模式测试

规则中的阈值均为 `mock-tech-v1` 技术配置，不代表正式学校制度。正式制度只能由问典返回，并保留来源和版本。

## 环境

建议 Python 3.11 或 3.12。

```powershell
cd D:\HeartEase_Guardian-xh\Backend\xh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` 和运行产生的 `var/` 已被忽略。不要在仓库中保存真实密钥或学生隐私数据。

## 启动

```powershell
uvicorn app.main:app --reload --port 8010
```

- 健康检查：`GET http://127.0.0.1:8010/health`
- Swagger：`http://127.0.0.1:8010/docs`

请求示例：

```json
{
  "request_id": "req_20261118_001",
  "counselor_id": "T001",
  "student_scope": {"type": "single", "student_ids": ["S001"]},
  "term": "2026-autumn",
  "task_type": "academic_risk_analysis",
  "requirement": "分析该生本学期成绩下降和缺勤情况，判断是否存在学业问题，并给出处置建议",
  "focus": ["grades", "attendance", "credits"],
  "options": {
    "query_regulations": true,
    "run_warning_detection": true,
    "max_suggestions": 3
  }
}
```

Mock 学生：

- `S001`：四类问题同时命中，且有一项缺失考勤；业务状态为 `partial`。
- `S002`：无明显问题；业务状态为 `completed`。
- `S003`：部分学业数据缺失；相关规则返回 `unknown`。

## 测试

```powershell
python -m pytest -q
```

测试全程离线，不访问 DeepSeek、问典或烽火真实服务。

## 本地运行数据

- `var/assessments.json`：以 `request_id` 幂等保存评估结果。
- `var/audit/audit.jsonl`：保存最小化输入/输出摘要，不记录完整敏感数据。

MySQL 是后续正式存储目标。第一阶段用文件存储完成可运行闭环，真实 HTTP 与数据库适配器可在不修改领域计算逻辑的前提下替换现有 Mock。

## 智能体扩展边界

当前不安装或调用 LangChain。`AcademicCoordinator` 使用确定性规则生成调度计划，`AcademicProfileAgent` 使用程序计算生成学生画像，`AcademicAssessmentAgent` 使用程序模板完成学业问题研判。三者的输入输出均有固定契约。未来接入 LangChain 时，只新增接口实现类，不改变学业指标、规则判断和 API 契约。

问典和烽火属于学海外部模块，由主流程通过 Adapter 调用。画像智能体不查询制度或判断预警，研判智能体只消费问典和烽火的返回结果，不维护制度库，也不修改预警等级。

当前唯一可用模式为：

```env
AGENT_MODE=template
```

`.env.example` 中的 LLM 配置只是预留项，不会读取密钥或发起网络请求。
