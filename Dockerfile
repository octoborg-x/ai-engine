FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Keep the runtime process unprivileged.
RUN groupadd --system app && \
    useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app app/ ./app/

RUN pip install --no-cache-dir .

ENV APP_MODULE=app.main:app
EXPOSE 8000

USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
