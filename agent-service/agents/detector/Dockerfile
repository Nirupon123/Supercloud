FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system deps (needed for numpy sometimes)
RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root
COPY requirement.txt .

RUN pip install --no-cache-dir -r requirement.txt

# Copy entire project
COPY . .

EXPOSE 8001

CMD ["uvicorn", "agents.detector.detector_service:app", "--host", "0.0.0.0", "--port", "8001"]
