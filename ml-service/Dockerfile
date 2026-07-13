FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --default-timeout=120 --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ app/

# Copy model artifacts if present (*.joblib files are gitignored;
# in production images these are injected at deploy time via volume mount)
COPY models/ models/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
# Health: model_loaded=false is valid in degraded mode (no model file)
# Use Python built-in urllib instead of curl (avoids apt dependency)
HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
