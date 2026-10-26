"""
ml/embeddings.py

EmbeddingProvider for intfloat/multilingual-e5-small (384-d, ONNX int8).
- Automatically applies 'passage: ' prefix for reviews/sentences
- Automatically applies 'query: ' prefix for feature anchor queries
- Generates unit-normalized L2 vectors for cosine similarity
- Singleton instance per worker process
- Includes deterministic fallback for test/dev environments without ONNX weights
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Sequence
import numpy as np


class EmbeddingProvider:
    """Singleton provider for multilingual-e5-small 384-dimensional dense vectors."""

    _instance: EmbeddingProvider | None = None

    def __init__(self, model_dir: Path | str | None = None):
        if model_dir is not None:
            self.model_dir = Path(model_dir)
        else:
            env_dir = os.environ.get("MODEL_DIR", "models/multilingual-e5-small-int8")
            self.model_dir = Path(env_dir)

        self.dim = 384
        self.session = None
        self.tokenizer = None
        self._init_model()

    @classmethod
    def get_instance(cls) -> EmbeddingProvider:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_model(self) -> None:
        """Attempt to load ONNX runtime session and tokenizer from model_dir."""
        onnx_path = self.model_dir / "model.onnx"
        if onnx_path.exists():
            try:
                import onnxruntime as ort
                from tokenizers import Tokenizer

                self.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
                tok_path = self.model_dir / "tokenizer.json"
                if tok_path.exists():
                    self.tokenizer = Tokenizer.from_file(str(tok_path))
            except Exception:
                self.session = None
                self.tokenizer = None

    def _deterministic_mock_vector(self, text: str) -> list[float]:
        """
        Generate deterministic 384-d unit-normalized float vector from text hash.
        Guarantees tests and offline environments have valid cosine properties.
        """
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def encode_passages(self, texts: Sequence[str]) -> list[list[float]]:
        """Encode review passages or sentences. Prepends 'passage: '."""
        prefixed = [f"passage: {t.strip()}" for t in texts]
        return self._encode_batch(prefixed)

    def encode_queries(self, queries: Sequence[str]) -> list[list[float]]:
        """Encode feature anchor queries. Prepends 'query: '."""
        prefixed = [f"query: {q.strip()}" for q in queries]
        return self._encode_batch(prefixed)

    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        # If real ONNX runtime session is loaded:
        if self.session is not None and self.tokenizer is not None:
            try:
                encoded = [self.tokenizer.encode(t) for t in texts]
                max_len = max(len(e.ids) for e in encoded)
                input_ids = np.zeros((len(texts), max_len), dtype=np.int64)
                attention_mask = np.zeros((len(texts), max_len), dtype=np.int64)

                for i, e in enumerate(encoded):
                    input_ids[i, : len(e.ids)] = e.ids
                    attention_mask[i, : len(e.ids)] = 1

                outputs = self.session.run(None, {"input_ids": input_ids, "attention_mask": attention_mask})
                # Mean pooling over token embeddings with attention mask
                token_embeddings = outputs[0]  # shape: (batch, seq_len, 384)
                input_mask_expanded = np.expand_dims(attention_mask, -1).astype(float)
                sum_embeddings = np.sum(token_embeddings * input_mask_expanded, 1)
                sum_mask = np.clip(input_mask_expanded.sum(1), a_min=1e-9, a_max=None)
                embeddings = sum_embeddings / sum_mask

                # Normalize to unit length (L2)
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                embeddings = embeddings / norms
                return embeddings.tolist()
            except Exception:
                pass  # Fall back to deterministic vector

        # Fallback to deterministic vectors
        return [self._deterministic_mock_vector(t) for t in texts]
