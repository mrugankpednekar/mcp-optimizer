FROM python:3.12-slim
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml README.md /app/
RUN pip install --upgrade pip && pip install "mcp[cli]" numpy scipy pydantic
COPY src/ /app/src/
ENV PYTHONPATH=/app/src
EXPOSE 3333
CMD ["mcp", "http", "src/mcp_optimizer/server.py", "--host", "0.0.0.0", "--port", "3333", "--cors", "*"]
