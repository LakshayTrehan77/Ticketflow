# build stage: install python packages into a separate folder
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# final stage: only what we need to run
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# do not run as root inside the container
RUN useradd --create-home --uid 10001 appuser
WORKDIR /srv

COPY --from=builder /install /usr/local
COPY app ./app
COPY ml ./ml

# train the model while building so the image is ready to serve
RUN python -m ml.train && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
