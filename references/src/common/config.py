"""全局配置 - 支持从环境变量与配置文件加载."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """信控智能体运行配置."""

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Kafka
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_task_topic: str = Field(default="signal-control-tasks", env="KAFKA_TASK_TOPIC")

    # 大模型（通义千问可用 LLM_API_KEY 或 DASHSCOPE_API_KEY）
    llm_api_base: Optional[str] = Field(default=None, env="LLM_API_BASE")
    llm_api_key: Optional[str] = Field(default=None, env="LLM_API_KEY")
    dashscope_api_key: Optional[str] = Field(default=None, env="DASHSCOPE_API_KEY")
    vl_api_base: Optional[str] = Field(default=None, env="VL_API_BASE")
    code_gen_api_base: Optional[str] = Field(default=None, env="CODE_GEN_API_BASE")
    amap_js_api_key: Optional[str] = Field(default=None, env="AMAP_JS_API_KEY")
    amap_security_js_code: Optional[str] = Field(default=None, env="AMAP_SECURITY_JS_CODE")

    # 知识库 / RAG
    rag_service_url: Optional[str] = Field(default=None, env="RAG_SERVICE_URL")
    vector_db_host: str = Field(default="localhost", env="VECTOR_DB_HOST")

    # 记忆检索
    memory_retrieval_url: Optional[str] = Field(default=None, env="MEMORY_RETRIEVAL_URL")

    # 数据库（示例）
    mysql_url: Optional[str] = Field(default=None, env="MYSQL_URL")
    # 路口信息表 lon/lat：wgs84（默认）时 API 输出转为 GCJ-02 供高德；gcj02 则库与底图一致不做偏移
    mysql_intersection_lonlat_srs: str = Field(default="wgs84", env="MYSQL_INTERSECTION_LONLAT_SRS")
    neo4j_uri: Optional[str] = Field(default=None, env="NEO4J_URI")
    influxdb_url: Optional[str] = Field(default=None, env="INFLUXDB_URL")

    # 人机协同
    human_confirm_threshold: float = Field(
        default=0.6, description="低于此置信度时进入人工确认模式"
    )
    auto_execute_threshold: float = Field(
        default=0.9, description="高于此置信度时全自动执行"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """获取配置单例（可后续改为依赖注入）."""
    return Settings()


def get_llm_api_key() -> Optional[str]:
    """获取大模型 API Key，优先 LLM_API_KEY，否则使用 DASHSCOPE_API_KEY（通义千问）."""
    s = get_settings()
    return s.llm_api_key or s.dashscope_api_key
