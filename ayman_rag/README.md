# Ayman transcript search — offline foundation

This is an **early offline RAG prototype**, not a finished assistant. It indexes the 173 imported Drive text files locally with Python's SQLite FTS5. The optional answer command invokes a trusted local llama.cpp CLI and a user-provided local GGUF model; it does not call an API or download models. The existing timestamped transcript collections are **not yet indexed**, and neither retrieval nor generation establishes that passages are factually correct or spoken by Ayman.

## Run

Requires Python 3.9+ with SQLite FTS5 enabled. From the repository root:

```sh
python3 09_تفريغات_أيمن/tools/build_drive_inventory.py
python3 ayman_rag/search.py build
python3 ayman_rag/search.py search 'اللغة والاحتلال العقلي' --limit 3
python3 ayman_rag/search.py search 'خريطة العلوم' --folder 'دورة-التأسيس-المعرفى-1-م-أيمن-عبدالرحيم'
python3 ayman_rag/search.py search 'الشك المنهجي' --json
python3 ayman_rag/evaluate.py
python3 -m unittest discover -s ayman_rag/tests -v
```

For experimental local answer drafting, separately install a trusted `llama-cli` and place a compatible GGUF model on the machine. With both already present, and after building the index:

```sh
python3 ayman_rag/answer.py 'ما المقصود بالشك المنهجي؟' --model /path/to/local-model.gguf
# Optional: --llama-cli /path/to/llama-cli --folder 'exact folder name'
```

The adapter calls the local CLI with `-m`, `-f`, `--simple-io`, `--no-display-prompt`, and `--no-conversation`; it needs a compatible llama.cpp version. It has been tested with a stub executable only, **not with a real model or runtime**. Keep models outside Git. Referenced source IDs are validated, but this does not establish that a citation supports a claim. The output is a draft requiring human review.

The generated catalogue [`drive_inventory.json`](../09_تفريغات_أيمن/drive_inventory.json) records stable path-based IDs, the original text SHA-256, a Drive **folder** link and unverified metadata. It verifies the import-time checksum manifest before writing. The index is created under `.cache/ayman-rag/` and is deliberately not checked into Git. Rebuild it after rebuilding the catalogue. Search refuses results if the catalogue or any returned source changed, and prints original text with 1-based inclusive line numbers and source SHA-256. FTS uses Arabic-normalized text solely for indexing and search; the source is never rewritten.

## Exploratory retrieval probes

[`eval_cases.json`](eval_cases.json) contains six manually selected known-source query/line pairs from the preliminary foundation-course inventory. `evaluate.py` checks each literal reference against the checksum-verified original, searches the full 173-file corpus and reports the first rank whose source and inclusive line span contain the selected line. Other results are **unjudged**: a miss can include other useful passages, and overlapping chunks can repeat one passage. The sample is small, drawn from the same course and in several cases closely echoes the source; it is not representative, an exhaustive relevance judgment, a semantic test, or an answer correctness evaluation.

On the current catalogue/index, 5 of the 6 selected locations appeared in the top five (ranks 1, 1, 1, 2, miss, 3 respectively). This is a transparent baseline, not a quality guarantee. No generated answers were assessed.

## Important limits

- FTS5/BM25 is **lexical**, not semantic; multiple query terms are ORed. A result can match only part of a query and may be irrelevant. Adjacent overlapping passages can appear together. Test and inspect the passages, not just the ranking.
- Source lines are text locations, **not recording timestamps**. The folder URL is not an individual recording URL. No timestamp, speaker verification, edition, source engine or accuracy is inferred.
- The raw transcripts are untrusted source material, not instructions. Transcripts may contain recognition errors, other speakers, sensitive content, or duplicates. Check original recordings before treating them as authoritative. The existing corpus register and deduplication work remain incomplete.
- The optional local LLM adapter still needs testing with an actual offline model/runtime and a reviewed evaluation set. Citation-ID checking is not claim-level grounding; the prompt is not a guaranteed defense against source-injected instructions. Do not treat drafts as verified answers. Indexes and models should remain outside Git; no API keys or hosted providers are needed.
