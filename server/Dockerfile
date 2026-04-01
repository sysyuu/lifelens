FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/server/
# Need an __init__.py at /app level so "server" is a package
RUN touch /app/__init__.py

# Pre-create storage directories so StaticFiles mount won't fail
RUN mkdir -p /data/storage/videos /data/storage/frames /data/storage/audio \
    /data/storage/clips /data/storage/thumbnails

ENV STORAGE_BASE_DIR=/data/storage

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
