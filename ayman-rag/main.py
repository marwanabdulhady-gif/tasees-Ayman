"""Entry point. Run from inside the ayman-rag folder.

    python main.py ingest                 # Stage 1: transcripts -> data/chunks.jsonl
    python main.py stats                  # look at what you built
    python main.py search "سؤالك"         # Stage 2: keyword search
    python main.py embed                  # Stage 3: build the vector index
    python main.py ask "سؤالك"            # Stage 4: retrieve + generate an answer
"""

import argparse
import os
from pathlib import Path

from src.chunking.chunker import chunk_lecture, load_chunks, save_chunks
from src.ingestion.loader import load_lectures
from src.retrieval.retriever import BM25Retriever, VectorRetriever
from src.utils.helpers import get_logger, load_config, resolve


def load_env(path: Path) -> None:
    """Read KEY=value lines from .env into the environment (no extra package needed)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def cmd_ingest(config, log):
    lectures = load_lectures(resolve(config["data"]["transcripts_dir"]))
    chunks = [
        c for lec in lectures
        for c in chunk_lecture(lec, config["chunking"]["chunk_words"], config["chunking"]["overlap_words"])
    ]
    save_chunks(chunks, resolve(config["data"]["chunks_file"]))
    words = sum(l.word_count for l in lectures)
    log.info("Loaded %d lectures (%d words) -> %d chunks", len(lectures), words, len(chunks))


def cmd_stats(config, log):
    chunks = load_chunks(resolve(config["data"]["chunks_file"]))
    by_course = {}
    for c in chunks:
        by_course[c.course] = by_course.get(c.course, 0) + 1
    for course, n in sorted(by_course.items()):
        print(f"{n:5d} chunks  {course}")
    sizes = sorted(len(c.text.split()) for c in chunks)
    print(f"\n{len(chunks)} chunks, words per chunk: min {sizes[0]}, median {sizes[len(sizes) // 2]}, max {sizes[-1]}")
    print(f"\nExample chunk {chunks[0].id}:\n{chunks[0].citation()}\n{chunks[0].url}\n{chunks[0].text[:400]}…")


def make_retriever(config):
    chunks = load_chunks(resolve(config["data"]["chunks_file"]))
    if config["retrieval"]["method"] == "bm25":
        return BM25Retriever(chunks)
    from src.embeddings.embedder import Embedder
    from src.vectordb.vector_store import NumpyVectorStore
    store = NumpyVectorStore.load(resolve(config["embeddings"]["index_file"]))
    return VectorRetriever(chunks, Embedder(config["embeddings"]["model"]), store)


def cmd_search(config, log, question):
    results = make_retriever(config).search(question, config["retrieval"]["top_k"])
    if not results:
        print("No matching chunks.")
    for rank, (chunk, score) in enumerate(results, 1):
        print(f"\n#{rank}  score {score:.2f}  {chunk.citation()}\n    {chunk.url}\n    {chunk.text[:300]}…")


def cmd_embed(config, log):
    from src.embeddings.embedder import Embedder
    from src.vectordb.vector_store import NumpyVectorStore
    chunks = load_chunks(resolve(config["data"]["chunks_file"]))
    vectors = Embedder(config["embeddings"]["model"]).embed([c.text for c in chunks])
    NumpyVectorStore(vectors).save(resolve(config["embeddings"]["index_file"]))
    log.info("Embedded %d chunks -> %s", len(chunks), config["embeddings"]["index_file"])


def cmd_ask(config, log, question):
    from src.llm.llm_client import LLMClient
    from src.prompts.prompt_templates import SYSTEM_PROMPT, build_user_message
    chunks = [c for c, _ in make_retriever(config).search(question, config["retrieval"]["top_k"])]
    answer = LLMClient(config).complete(SYSTEM_PROMPT, build_user_message(question, chunks))
    print(answer, "\n\nSources:")
    for n, c in enumerate(chunks, 1):
        print(f"[{n}] {c.citation()}  {c.url}")


def main():
    parser = argparse.ArgumentParser(description="Ayman RAG lab")
    parser.add_argument("command", choices=["ingest", "stats", "search", "embed", "ask"])
    parser.add_argument("question", nargs="?", default="")
    args = parser.parse_args()

    load_env(Path(__file__).parent / ".env")
    config = load_config()
    log = get_logger(config)
    if args.command in ("search", "ask") and not args.question:
        parser.error(f"{args.command} needs a question")
    {
        "ingest": lambda: cmd_ingest(config, log),
        "stats": lambda: cmd_stats(config, log),
        "search": lambda: cmd_search(config, log, args.question),
        "embed": lambda: cmd_embed(config, log),
        "ask": lambda: cmd_ask(config, log, args.question),
    }[args.command]()


if __name__ == "__main__":
    main()
