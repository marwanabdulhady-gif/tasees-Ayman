# Ayman RAG

A learning project: build a question-answering assistant over the lecture transcripts of م. أيمن عبدالرحيم, one stage at a time, to understand how RAG (retrieval-augmented generation) and language models work.

**For personal learning only.** The assistant never speaks as Ayman, refuses religious rulings, and cites the lecture (with a timestamped YouTube link) for every answer.

> **Not the same as `../ayman_rag/`** (underscore). That folder is another agent's offline search catalogue used to build the playlist courses (SQLite FTS5, 398 sources). This one is the owner's step-by-step learning project.

## The data

The transcripts come from `../transcripts/` in this repository: 6 playlists, 91 lectures, about 980,000 words of YouTube auto-captions in Egyptian Arabic. They are read in place, not copied.

## Quick start

```bash
cd ayman-rag
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py ingest                       # transcripts -> data/chunks.jsonl (~3,000 chunks)
python main.py stats                        # look at what you built
python main.py search "ما هو الوعي اللغوي"   # keyword search, top 5 with video links
python -m unittest discover tests           # run the tests
```

## How a question gets answered

```
transcripts/*.md ─▶ ingestion ─▶ chunking ─▶ embeddings ─▶ vectordb
                                                              │
        question ─────────────────────────────▶ retrieval ◀───┘
                                                    │ top 5 chunks
                                     prompts ─▶ llm ─▶ answer + sources
```

## Project structure

| Path | What it does | Stage | Status |
|---|---|---|---|
| `README.md` | This file | | |
| `requirements.txt` | Python packages, grouped by stage | | |
| `.env.example` | Copy to `.env` and add your API key. `.env` is never committed | 4 | |
| `.gitignore` | Keeps secrets, generated data and logs out of Git | | |
| `config.yaml` | Chunk size, models, top-k: everything you experiment with | | |
| `src/ingestion/loader.py` | Reads each transcript into a `Lecture` with timestamped paragraphs | 1 | working |
| `src/chunking/chunker.py` | Splits lectures into ~400-word overlapping chunks, each with its video link | 1 | working |
| `src/retrieval/retriever.py` | BM25 keyword search (written by hand so you can read it), plus the vector retriever | 2 · 3 | BM25 working |
| `src/embeddings/embedder.py` | Turns text into meaning vectors with `bge-m3` | 3 | ready to try |
| `src/vectordb/vector_store.py` | Stores vectors and finds the nearest ones (numpy now; FAISS or Supabase later) | 3 | ready to try |
| `src/prompts/prompt_templates.py` | The Arabic system prompt that keeps answers grounded and cited | 4 | ready to try |
| `src/llm/llm_client.py` | Calls Claude or a local Ollama model | 4 | ready to try |
| `src/api/routes.py` | FastAPI endpoint so a web page can call the search | later | ready to try |
| `src/utils/helpers.py` | Config, logging, Arabic normalisation | | working |
| `tests/test_app.py` | Unit tests for loading, chunking, normalising and searching | | working |
| `tests/eval_questions.jsonl` | 15 test questions with the lecture(s) that answer each | 2 | |
| `src/retrieval/evaluate.py` | Scores a retriever: Hit@5 and MRR, split by direct vs paraphrase | 2 | working |
| `logs/` | `app.log` is written here | | |
| `data/` | Generated chunks and vectors (not committed) | | |
| `main.py` | Entry point: `ingest`, `stats`, `search`, `eval`, `embed`, `ask` | | |

## Stages

1. **Clean and chunk.** `python main.py ingest`, then `stats`. Try `chunk_words: 200` and `800` in `config.yaml`.
2. **Keyword search.** `python main.py search "..."`, then `python main.py eval` to score it on the 15 test questions in `tests/eval_questions.jsonl`.

   Baseline (BM25, 400-word chunks): **Hit@5 80% (12/15), MRR 0.69.** Direct questions 9/9; paraphrased questions only 3/6. Search by meaning in Stage 3 should close that gap.
3. **Search by meaning.** `pip install sentence-transformers`, `python main.py embed`, set `retrieval.method: vector` and compare against your BM25 score.
4. **Generate.** Put your key in `.env` (or set `provider: ollama`), then `python main.py ask "..."`.
5. **Train a tiny GPT** on the same text in Google Colab (separate notebook, coming later).

### Things to notice as you go

- The captions are machine-made: `المحاضره` instead of `المحاضرة`, cut-off words, spoken dialect. `normalize_arabic()` makes your typed questions match that spelling.
- Every lecture opens with the same introduction ("شيخ العمود واهل العلم احياء…"). Watch how often it shows up in search results, and think about how to filter it out.
- Common words like `يعني` and `ايه` appear everywhere. BM25's IDF weighting is what keeps them from dominating.
