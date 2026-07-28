"""数据底座各组件抽象/适配 - 对应架构第 6 节.

MySQL/PostgreSQL 结构化数据；Neo4j 拓扑与关联；InfluxDB 时序；
Redis 缓存；MinIO 对象存储；ChromaDB/Milvus 向量检索.
"""

from __future__ import annotations

from typing import Any


class RedisStore:
    """Redis：全局态势关键指标、任务状态、配时实时参数、工作记忆."""

    def __init__(self, url: str = "redis://localhost:6379/0"):
        self._url = url
        self._client = None

    def get(self, key: str) -> Any:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        pass

    def hgetall(self, key: str) -> dict:
        return {}


class MySQLStore:
    """MySQL：设施基础参数、配时方案、评价指标、诊断结果、设备信息."""

    def __init__(self, url: str = ""):
        self._url = url

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        return []

    def execute(self, sql: str, params: tuple = ()) -> int:
        return 0


class InfluxStore:
    """InfluxDB：实时交通流时序数据（车速、流量、饱和度）、信号机运行数据."""

    def __init__(self, url: str = "", token: str = ""):
        self._url = url
        self._token = token

    def query_timeseries(self, measurement: str, tags: dict, start: str, end: str) -> list:
        return []


class Neo4jStore:
    """Neo4j：路网拓扑、路口关联、拥堵扩散路径、管控子区节点关联."""

    def __init__(self, uri: str = "", user: str = "", password: str = ""):
        self._uri = uri
        self._user = user
        self._password = password

    def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        return []


class MinIOStore:
    """MinIO：视频、图片等多模态数据；评价报告附件；模型训练数据."""

    def __init__(self, endpoint: str = "", access_key: str = "", secret_key: str = ""):
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key

    def get_object(self, bucket: str, key: str) -> bytes:
        return b""

    def put_object(self, bucket: str, key: str, data: bytes) -> None:
        pass


class VectorStore:
    """向量库（ChromaDB/Milvus）：记忆与知识库向量索引，语义检索."""

    def __init__(self, host: str = "localhost", collection: str = "default"):
        self._host = host
        self._collection = collection

    def add(self, ids: list[str], texts: list[str], embeddings: list[list[float]] | None = None) -> None:
        pass

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        return []
