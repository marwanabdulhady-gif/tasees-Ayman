"""Later — expose the pipeline over HTTP so a web page (React, Supabase, n8n) can call it.

Install:  pip install fastapi uvicorn
Run:      uvicorn src.api.routes:app --reload
Try:      http://127.0.0.1:8000/search?q=الوعي اللغوي
"""

from fastapi import FastAPI

from src.chunking.chunker import load_chunks
from src.retrieval.retriever import BM25Retriever
from src.utils.helpers import load_config, resolve

config = load_config()
retriever = BM25Retriever(load_chunks(resolve(config["data"]["chunks_file"])))
app = FastAPI(title="Ayman RAG")


@app.get("/search")
def search(q: str, k: int = 5):
    return [
        {"score": round(score, 2), "citation": c.citation(), "url": c.url, "text": c.text}
        for c, score in retriever.search(q, k)
    ]
