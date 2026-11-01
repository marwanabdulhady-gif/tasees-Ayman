# Ayman transcript search — offline foundation

This is an **early offline RAG prototype**, not a finished assistant. The default index covers 173 imported Drive text files locally with Python's SQLite FTS5. An optional separate psychology index combines the 11 Drive psychology files and the 10 existing timestamped psychology Markdown files, keeping every edition separate. Other existing timestamped collections are **not yet indexed**. The optional answer command invokes a trusted local llama.cpp CLI and a user-provided local GGUF model; it does not call an API or download models. Neither retrieval nor generation establishes that passages are factually correct or spoken by Ayman.

## Run

Requires Python 3.9+ with SQLite FTS5 enabled. From the repository root:

```sh
python3 09_تفريغات_أيمن/tools/build_drive_inventory.py
python3 ayman_rag/search.py build
python3 ayman_rag/search.py search 'اللغة والاحتلال العقلي' --limit 3
python3 ayman_rag/search.py search 'خريطة العلوم' --folder 'دورة-التأسيس-المعرفى-1-م-أيمن-عبدالرحيم'
python3 ayman_rag/search.py search 'الشك المنهجي' --json
python3 ayman_rag/search.py search 'اللغة والاحتلال العقلي' --match all
python3 ayman_rag/search.py search 'الأفكار الإدارة' --source-id drive-9b6f5de831f98b66eda9
python3 ayman_rag/evaluate.py
python3 ayman_rag/evaluate.py --match all
python3 -m unittest discover -s ayman_rag/tests -v
```

### Psychology: both transcript editions

Build a separate catalogue and index; the default Drive index remains unchanged:

```sh
python3 09_تفريغات_أيمن/tools/build_drive_inventory.py
python3 ayman_rag/build_psychology_catalog.py
python3 ayman_rag/search.py build --catalog ayman_rag/psychology_inventory.json --index .cache/ayman-rag/psychology.sqlite3
python3 ayman_rag/search.py search 'الشك المنهجي' --catalog ayman_rag/psychology_inventory.json --index .cache/ayman-rag/psychology.sqlite3 --json
python3 ayman_rag/evaluate.py --cases ayman_rag/psychology_eval_cases.json --catalog ayman_rag/psychology_inventory.json --index .cache/ayman-rag/psychology.sqlite3
```

Pass the same `--catalog` and `--index` to `answer.py` to retrieve from that index. The separate `--folder 03-psychology` filter restricts to the ten older files; use the exact Drive folder for imported text. The 21-file catalogue includes SHA-256 for the current bytes, and recording links and transcription methods **as claimed by the older files' headers**; timestamps and recordings are not verified. Legacy hashes are not independent evidence of authenticity, and similarities between editions do not prove they derive from the same recording. Rebuild the catalogue only after reviewing source changes, then rebuild its index. Do not infer a recording link or a timestamp for Drive text.

For experimental local answer drafting, separately install a trusted `llama-cli` and place a compatible GGUF model on the machine. With both already present, and after building the index:

```sh
python3 ayman_rag/answer.py 'ما المقصود بالشك المنهجي؟' --model /path/to/local-model.gguf
# Optional: --llama-cli /path/to/llama-cli --folder 'exact folder name'
# Optional retrieval filters: --source-id drive-... --match all
```

The adapter calls the local CLI with `-m`, `-f`, `--simple-io`, `--no-display-prompt`, and `--no-conversation`; it needs a compatible llama.cpp version. It has been tested with a stub executable only, **not with a real model or runtime**. Keep models outside Git. It requires valid retrieved IDs and a reference in each punctuation/newline-delimited output segment, or the exact abstention message; outputs that do not meet this conservative formatting rule are rejected. This is not an Arabic sentence parser: it can reject harmless formatting and cannot guarantee that every claim is cited or that a cited passage supports it. The output is a draft requiring human review.

The generated catalogue [`drive_inventory.json`](../09_تفريغات_أيمن/drive_inventory.json) records stable path-based IDs, the original text SHA-256, a Drive **folder** link and unverified metadata. It verifies the import-time checksum manifest before writing. The index is created under `.cache/ayman-rag/` and is deliberately not checked into Git. Rebuild it after rebuilding the catalogue. Search refuses results if the catalogue or any returned source changed, and prints original text with 1-based inclusive line numbers and source SHA-256. FTS uses Arabic-normalized text solely for indexing and search; the source is never rewritten.

## Offline two-source comparison

```sh
python3 ayman_rag/compare.py drive-57f2ce520d28eddf9f87 drive-8d691d57543232ceb069 --max-runs 10
python3 ayman_rag/compare.py SOURCE_ID_A SOURCE_ID_B --catalog ayman_rag/psychology_inventory.json
python3 08_دورات_القوائم/tools/build_foundation_overlap_report.py
```

`compare.py` verifies both catalogued paths and raw SHA-256 hashes before tokenizing, without an index, model, or network. It removes Markdown timestamp links and URLs, applies the search normalizer, and uses unique five-word shingles for Jaccard and smaller-set overlap. Ten bins count shingles in each segment that occur anywhere in the other source; they are **not** aligned time intervals. Runs require a series of shingles appearing exactly once in each source and contiguous in both. They omit repetitive matches, can split at small textual differences, and may overlap; only the requested longest runs are shown. Line numbers are inclusive original source lines; the previews are normalized and **not literal quotations**. The metrics are lexical set measures, not a percentage of identical recordings or proof of semantic agreement, attribution, accuracy, or completeness. See the [foundation overlap report](../08_دورات_القوائم/التأسيس_المعرفي/01_مقارنة_ملفي_المستوى_الثاني.md).

## Exploratory retrieval probes

[`eval_cases.json`](eval_cases.json) contains six manually selected known-source query/line pairs from the preliminary foundation-course inventory. `evaluate.py` checks each literal reference against the checksum-verified original, searches the full 173-file corpus and reports the first rank whose source and inclusive line span contain the selected line. Other results are **unjudged**: a miss can include other useful passages, and overlapping chunks can repeat one passage. The sample is small, drawn from the same course and in several cases closely echoes the source; it is not representative, an exhaustive relevance judgment, a semantic test, or an answer correctness evaluation.

On the current default catalogue/index, the default `any` mode found 5 of the 6 selected locations in the top five (ranks 1, 1, 1, 2, miss, 3); `all` found 4 of 6 (miss, 1, 1, 2, miss, 3). For example, the first target contains `بالتحسين`, not the query token `التحسين`, so requiring every token loses it. A separate set of six psychology probes in [`psychology_eval_cases.json`](psychology_eval_cases.json), chosen from manually inspected source locations and heavily echoing their wording, found 6/6 locations in the top five on the 21-source psychology index. These samples are tiny, selected with knowledge of the sources, and do not measure general relevance, medical correctness, or answer correctness. No generated answers were assessed.

## Important limits

- FTS5/BM25 is **lexical**, not semantic; by default up to 20 unique query terms are ORed. A result can match only part of a query and may be irrelevant. `--match all` requires every retained token in the same passage, without fallback; it can miss relevant passages because of spelling, wording or chunk boundaries. `--source-id` filters exactly to a known ID (unknown IDs error); combined folder and source filters both apply. These controls are not relevance or truth guarantees. Adjacent overlapping passages can appear together. Test and inspect the passages, not just the ranking.
- Source lines are text locations, **not recording timestamps**. The folder URL is not an individual recording URL. No timestamp, speaker verification, edition, source engine or accuracy is inferred.
- The raw transcripts are untrusted source material, not instructions. Transcripts may contain recognition errors, other speakers, sensitive content, or duplicates. Check original recordings before treating them as authoritative. The existing corpus register and deduplication work remain incomplete.
- The optional local LLM adapter still needs testing with an actual offline model/runtime and a reviewed evaluation set. Citation-ID checking is not claim-level grounding; the prompt is not a guaranteed defense against source-injected instructions. Do not treat drafts as verified answers. Indexes and models should remain outside Git; no API keys or hosted providers are needed.
