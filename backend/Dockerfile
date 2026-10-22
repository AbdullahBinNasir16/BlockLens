# The API half: FastAPI under uvicorn, with the shipped model artefact. The
# live scorer loop is on by default; set BLOCKLENS_LIVE=0 to serve only.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
COPY blocklens ./blocklens
RUN pip install .
COPY alembic.ini ./
COPY migrations ./migrations
COPY data/models ./data/models
# Runtime state (live_launches.json) lives under /app/data; mount it to keep it.
VOLUME ["/app/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn blocklens.api.app:app --host 0.0.0.0 --port 8000"]
