FROM python:3.12-slim
WORKDIR /app
COPY . /app/
RUN pip install --upgrade pip \
    && pip install .[mip]
ENV PYTHONPATH=/app/src
EXPOSE 3333
CMD ["python", "-m", "crew_optimizer.server"]
