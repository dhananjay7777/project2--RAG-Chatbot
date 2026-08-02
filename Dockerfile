# Deploy image for Railway (FastAPI + read-only Phase 9 corpus/index).
# Never bake secrets: .env is excluded via .dockerignore.
# Keep the compressed image under Railway Hobby's ~4 GB limit:
# CPU torch only, no streamlit/chromadb/pytest, no HF weights baked in.

FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.api.txt .

# CPU torch first (much smaller than the CUDA default wheel), then API deps.
RUN pip install --upgrade pip \
    && pip install --prefix=/install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --prefix=/install -r requirements.api.txt

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    MF_HEALTH_STRICT=1 \
    PATH="/usr/local/bin:${PATH}" \
    PYTHONPATH="/usr/local/lib/python3.11/site-packages"

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

# P10-01: refuse images that accidentally include a local .env
RUN if [ -f .env ]; then echo "ERROR: .env must not be copied into the image" >&2; exit 1; fi

# Exit criteria: registry cardinality == 5; index artifacts present for cold start
RUN python -c "from ingest.acquisition.registry import load_source_definitions; n=len(load_source_definitions()); assert n==5, n"
RUN test -f data/index/index_manifest.json \
    && test -f data/index/bm25.pkl \
    && (test -d data/index/chroma || test -f data/index/dense_vectors.pkl) \
    && test -f data/processed/chunks.jsonl

# Do NOT download embedding/reranker weights here — they push the image over
# Railway Hobby's size limit. Lifespan warm-up in app.api.main loads them at boot.

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.cache/huggingface \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Railway injects PORT
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
