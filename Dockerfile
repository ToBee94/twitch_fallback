FROM python:3.11-slim

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Installiere FFmpeg und andere Dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Erstelle Arbeitsverzeichnis
WORKDIR /app

# Kopiere Requirements
COPY requirements.txt .

# Installiere Python-Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere Anwendungscode
COPY . .

# Erstelle Verzeichnis für Fallback-Media
RUN mkdir -p /app/media

# Exponiere Port für Web-UI
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/status')" || exit 1

# Starte Anwendung
CMD ["python", "app.py"]
