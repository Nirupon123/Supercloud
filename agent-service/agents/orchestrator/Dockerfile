FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    openssl \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirement.txt .

RUN pip install --no-cache-dir -r requirement.txt

# Copy project
COPY . .

EXPOSE 8000

CMD ["uvicorn", "agents.orchestrator.services.orchestrator_service:app", "--host", "0.0.0.0", "--port", "8000"]