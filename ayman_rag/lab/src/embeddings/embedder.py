"""Stage 3 — turn text into vectors (lists of numbers) that capture meaning.

Two chunks about the same idea get vectors pointing in nearly the same
direction, even when they share no words. That is what lets a question about
"الوعي" find a passage that says "واعٍ".

Install first:  pip install sentence-transformers
"""


class Embedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # imported here: heavy, Stage 3 only
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]):
        # normalize_embeddings=True makes a dot product equal cosine similarity.
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=len(texts) > 20)
