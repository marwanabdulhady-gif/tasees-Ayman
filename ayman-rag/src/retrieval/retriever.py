"""Stage 2 — find the chunks that best match a question.

BM25 is classic keyword search (it is roughly what search engines used before
neural networks). It is written out by hand here, about 25 lines, so you can
see there is no magic: a chunk scores high when it contains the question's
words, especially rare words, without being padded with everything else.
The `rank_bm25` package does the same thing.

Stage 3 adds VectorRetriever (search by meaning) next to it.
"""

import math
from collections import Counter

from src.chunking.chunker import Chunk
from src.utils.helpers import tokenize


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(c.text)) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(len(self.lengths), 1)
        # Document frequency: in how many chunks does each word appear?
        df = Counter(word for d in self.docs for word in d)
        n = len(self.docs)
        # IDF: rare words ("المسيري") count far more than common ones ("يعني").
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def score(self, query_words: list[str], i: int) -> float:
        doc, length = self.docs[i], self.lengths[i]
        total = 0.0
        for w in query_words:
            tf = doc.get(w, 0)
            if tf:
                norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
                total += self.idf[w] * norm
        return total

    def search(self, question: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        words = tokenize(question)
        scored = [(self.score(words, i), i) for i in range(len(self.chunks))]
        scored.sort(reverse=True)
        return [(self.chunks[i], s) for s, i in scored[:top_k] if s > 0]


class VectorRetriever:
    """Stage 3 — search by meaning. Wire up Embedder + VectorStore here."""

    def __init__(self, chunks, embedder, store):
        self.chunks, self.embedder, self.store = chunks, embedder, store

    def search(self, question: str, top_k: int = 5):
        query = self.embedder.embed([question])[0]
        return [(self.chunks[i], s) for i, s in self.store.search(query, top_k)]
