FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY production/*.py .
COPY communes_mapping.csv .
COPY config/.env .env

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
