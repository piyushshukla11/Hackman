# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

# System deps: WeasyPrint needs Pango/Cairo; ffmpeg for audio extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY backend/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir -e .

# ---- Bake multilingual-e5-small ONNX weights into image ----
# Download once at build time so workers start in <2 s and don't need internet at runtime
RUN python - <<'EOF'
from pathlib import Path
import urllib.request, os, sys

try:
    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id="intfloat/multilingual-e5-small",
        local_dir="/models/multilingual-e5-small",
        allow_patterns=["*.json", "*.txt", "sentencepiece.bpe.model", "*.onnx", "*.bin"],
        ignore_patterns=["*.msgpack", "*.h5", "flax_*", "tf_*"],
    )
    print("Model downloaded via huggingface_hub")
except Exception as e:
    print(f"huggingface_hub not available or failed: {e}")
    print("Model will be downloaded at first worker startup")
EOF

# Copy repository code (root context includes db/, ml/, backend/)
COPY . .

ENV PYTHONPATH="/app:/app/backend:${PYTHONPATH}"
WORKDIR /app/backend

# Default command: FastAPI API server
# Override CMD in render.yaml for the Workflows worker
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

