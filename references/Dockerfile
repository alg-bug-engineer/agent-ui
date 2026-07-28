# 信控智能体应用镜像 - 云原生部署（对应架构 7.2 节）
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . && pip install uvicorn[standard]

COPY src/ ./src/
COPY docs/ ./docs/
COPY config/ ./config/

ENV PYTHONPATH=/app
# 现场可通过 volume 覆盖 /app/config/business_rules/default.yaml
ENV SIGNAL_AGENT_BUSINESS_RULES_PATH=/app/config/business_rules/default.yaml
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
