# FastAPI backend microservice — built at the repository root so the build
# context contains app/ and pyproject.toml (the backend Python package).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Keep the runtime process unprivileged.
RUN groupadd --system app && \
    useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

# Install pinned Python dependencies first; pyproject.toml is the dependency
# manifest for this microservice only.
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app app/ ./app/

RUN pip install --no-cache-dir .

ENV APP_MODULE=app.main:app
EXPOSE 8000

# Portable health probe for Docker and hosted platforms. /health is public and
# returns 200 without secrets; /ready also verifies that a provider key exists.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
