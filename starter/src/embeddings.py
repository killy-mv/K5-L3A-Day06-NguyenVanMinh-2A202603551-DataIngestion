"""Real local dense embeddings from a pinned Hugging Face SentenceTransformer."""
from __future__ import annotations

import math
import os
from typing import Protocol

DEFAULT_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DEFAULT_REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'

class Embedder(Protocol):
    model_name: str
    dimensions: int
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, question: str) -> list[float]: ...

class MyEmbedder:
    """Same SentenceTransformer encode recipe for documents and questions.

    CPU for reproducibility; normalized vectors; no mock or API fallback.
    """
    def __init__(self, model_name: str = DEFAULT_MODEL, *, revision: str | None = None) -> None:
        if not model_name or not model_name.strip():
            raise ValueError('Embedding model name cannot be empty')
        from sentence_transformers import SentenceTransformer
        import torch
        os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
        torch.set_num_threads(min(4, os.cpu_count() or 1))
        self.model_name = model_name
        self.revision = revision if revision is not None else (DEFAULT_REVISION if model_name == DEFAULT_MODEL else None)
        self.device = 'cpu'
        self.model = SentenceTransformer(model_name, revision=self.revision, device=self.device)
        self.dimensions = int(self.model.get_embedding_dimension())
        self.max_seq_length = int(self.model.max_seq_length)
        if self.dimensions <= 0:
            raise RuntimeError('Embedding model reports invalid output dimensions')

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(t, str) or not t.strip() for t in texts):
            raise ValueError('Cannot embed empty or non-string text')
        vectors = self.model.encode(texts, batch_size=32, normalize_embeddings=True,
                                    convert_to_numpy=True, show_progress_bar=False)
        output = vectors.tolist()
        if len(output) != len(texts):
            raise RuntimeError('Embedding provider returned mismatched vector count')
        for vector in output:
            if len(vector) != self.dimensions or not all(math.isfinite(v) for v in vector):
                raise RuntimeError('Invalid real embedding from model')
        return output

    def embed_query(self, question: str) -> list[float]:
        return self.embed_documents([question])[0]
