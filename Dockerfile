FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt && \
    groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --chown=app:app backend ./backend
USER app

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
