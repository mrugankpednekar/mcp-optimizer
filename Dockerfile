FROM python:3.12-slim
WORKDIR /app
COPY . /app/
RUN pip install --upgrade pip \
    && pip install .[mip]
ENV PYTHONPATH=/app/src
EXPOSE 3333
CMD ["mcp", "http", "src/crew_optimizer/server.py", "--host", "0.0.0.0", "--port", "3333", "--cors", "*"]
