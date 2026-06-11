# Pin to a specific minor version for reproducible, scannable builds.
FROM python:3.14-slim

# Avoid interactive prompts and reduce image cruft.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the runtime needs.
COPY app/ ./app/

# Create and switch to an unprivileged user. Containers should not run as root.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Basic container-level health check.
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# Run under gunicorn (production WSGI server), not the Flask dev server.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app.main:app"]
