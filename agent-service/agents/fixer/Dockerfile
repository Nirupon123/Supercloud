FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# Shares the root requirement.txt (includes fastapi, uvicorn, httpx etc.)
COPY requirement.txt .

RUN pip install --no-cache-dir -r requirement.txt

# Copy entire agent-service project
COPY . .

EXPOSE 8003

CMD ["uvicorn", "agents.fixer.fixer_service:app", "--host", "0.0.0.0", "--port", "8003"]
