FROM python:3.12-slim

WORKDIR /app

# Installiere Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere Anwendungscode
COPY . .

# Erstelle Verzeichnisse
RUN mkdir -p /app/data /app/logs

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV MAX_WORKERS=4
ENV MIN_CHUNK_SIZE=50
ENV MAX_CHUNK_SIZE=10000
ENV MEMORY_TARGET=0.7

# Exponiere Ports
EXPOSE 5000 9090

# Starte Anwendung
CMD ["python", "app.py"] 