FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY worker.py ./worker.py
CMD ["python", "worker.py"]

