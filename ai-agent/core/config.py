"""
女娲 AI 智能体 - 核心配置
"""
import os

class Settings:
    # 服务配置
    APP_NAME: str = "nuwa-ai-agent"
    APP_VERSION: str = "1.0.0"
    HOST: str = os.getenv("NUWA_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("NUWA_PORT", "8000"))

    # LLM 配置 - 复用 Coze 环境变量
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", ""))
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", ""))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "coze/auto")

    # Redis 配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Qdrant 配置
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "mirofish_rag")

    # RAG 配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text2vec-base-chinese")
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))

settings = Settings()
