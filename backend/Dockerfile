FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_URL=sqlite:////data/nodum.db

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip check \
    && groupadd --gid 10001 nodum \
    && useradd --uid 10001 --gid nodum --no-create-home --shell /usr/sbin/nologin nodum \
    && mkdir /data \
    && chown nodum:nodum /data

COPY app ./app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-m", "app.healthcheck"]
CMD ["python", "-m", "app.run"]
