import os

# 测试永远走离线/文件后端，避免依赖本机 MySQL 与真实模型
os.environ["LLM_API_KEY"] = ""
os.environ["STORE_BACKEND"] = "json"
