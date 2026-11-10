"""Stage 3 — store chunk vectors and find the nearest ones to a question.

This starts as the simplest possible store: one numpy array on disk and a
dot product. With ~500 chunks that is instant. Later you can swap in FAISS,
Chroma, or a Supabase table with pgvector, behind the same two methods.
"""

from pathlib import Path

import numpy as np


class NumpyVectorStore:
    def __init__(self, vectors: np.ndarray):
        self.vectors = vectors

    @classmethod
    def load(cls, path: Path) -> "NumpyVectorStore":
        return cls(np.load(path))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, self.vectors)

    def search(self, query: np.ndarray, top_k: int = 5) -> list[tuple[int, float]]:
        scores = self.vectors @ query
        best = np.argsort(-scores)[:top_k]
        return [(int(i), float(scores[i])) for i in best]
