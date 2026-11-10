# Ayman transcript search — offline foundation

This is an **early offline RAG prototype**, not a finished assistant. The default index covers 173 imported Drive text files locally with Python's SQLite FTS5. An optional separate psychology index combines the 11 Drive psychology files and the 10 existing timestamped psychology Markdown files, keeping every edition separate. A third, optional **unified playlist catalogue** now covers all 11 registered playlists (240 files, including the 15 PDF-derived «أين الطريق؟» steps) plus the 173 Drive files, with 15 overlapping paths represented once: 398 checksum-verified sources in total. The optional answer command invokes a trusted local llama.cpp CLI and a user-provided local GGUF model; it does not call an API or download models. Neither retrieval nor generation establishes that passages are factually correct, spoken by a verified speaker, or approved course content.

## Two parts, one folder

| Part | What it is | Start here |
|---|---|---|
| `ayman_rag/` (this folder) | Offline search catalogue for the agents who build the playlist courses: 398 checksum-verified sources, SQLite FTS5, optional local llama.cpp answers | **Run** below |
| [`ayman_rag/lab/`](lab/README.md) | The owner's learning project: the RAG pipeline built by hand, stage by stage (chunking, BM25, embeddings, generation), with a 15-question evaluation | [`lab/README.md`](lab/README.md) |

The two parts don't import each other. Their tests run separately: `python3 -m unittest discover -s ayman_rag/tests` here, `cd ayman_rag/lab && python3 -m unittest discover tests` for the lab.

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

### All registered playlists: one optional unified index

Build a separate catalogue and index; the default Drive index and the psychology-only index remain unchanged:

```sh
python3 ayman_rag/build_playlist_catalog.py --check
python3 ayman_rag/search.py build --catalog ayman_rag/playlist_inventory.json --index .cache/ayman-rag/playlists.sqlite3
python3 ayman_rag/search.py search 'اللغة والاحتلال العقلي' --catalog ayman_rag/playlist_inventory.json --index .cache/ayman-rag/playlists.sqlite3 --playlist cognitive-foundation-1 --json
python3 ayman_rag/search.py search 'ما الذي يجعلنا نثق بالتاريخ' --catalog ayman_rag/playlist_inventory.json --index .cache/ayman-rag/playlists.sqlite3 --playlist q100-history
python3 ayman_rag/evaluate.py --cases ayman_rag/playlist_eval_cases.json --catalog ayman_rag/playlist_inventory.json --index .cache/ayman-rag/playlists.sqlite3
```

`playlist_inventory.json` is checked in; `.cache/ayman-rag/playlists.sqlite3` is not. The catalogue records one path-based ID, current SHA-256, source folder, playlist slug, episode number, citation kind, voice policy and unverified metadata for every source. `--playlist` is an exact slug filter; `--folder`, `--source-id` and `--match` still apply, and all filters combine. Pass `--playlist` to `answer.py` too. Search results include the playlist slug, episode, citation kind and voice policy.

Episode numbers follow the deterministic file ordering, `episode:` front matter, or numbered raw-text filenames used by `check_lesson.py`; they are **not** recording times. The legacy `playlists.json` `n` field can differ or repeat (notably `ayman-tasees`, where two files share `n = 16`), so the catalogue also keeps `registry_episode` and `registry_sha`. Non-Ayman playlists (`q100-history`, `rihlat-alyaqeen`, `ayn-al-tariq`) stay separate, are labeled `owner-decision`, and are not written in Ayman voice; the owner has recorded a neutral-named-guide Q1 decision. The owner has also approved publication in the repository, but the catalogue does not independently verify an official course map, recording, speaker, reference, or transcription.

[`playlist_eval_cases.json`](playlist_eval_cases.json) has eleven manually selected known-source query/line pairs, one per playlist. On the current unified index, all eleven selected locations were recovered in the top five (ten at rank 1 and one at rank 4). The queries heavily echo their source lines; the sample is tiny, selected with knowledge of the sources, and other retrieved passages are unjudged. It does not measure semantic relevance, medical correctness, or answer correctness. No generated answers were assessed.

### Deterministic retrieval audit

[`audit_playlist_retrieval.py`](audit_playlist_retrieval.py) writes [`playlist_retrieval_audit.json`](playlist_retrieval_audit.json) and [`playlist_retrieval_audit.md`](playlist_retrieval_audit.md). It verifies all 398 source hashes and catalogue counts, then checks exact `--playlist` isolation for one probe per playlist, absence of cross-playlist leakage when the same query is filtered to a different playlist, an unknown-slug control, a nonsense-token negative control and the eleven known-location probes. It builds a temporary unified index by default; `--index` can reuse an existing one. On the current catalogue all checks pass and the eleven selected locations are recovered in the top five.

```sh
python3 ayman_rag/audit_playlist_retrieval.py --check
python3 ayman_rag/audit_playlist_retrieval.py --index .cache/ayman-rag/playlists.sqlite3
```

**PASS is a plumbing/bytes check only.** It does not mean retrieved passages are relevant, that answers are correct, that transcripts or speakers are verified, or that references are reviewed. The owner's approval is a recorded administrative decision, not an automated verification. The default Drive and psychology-only indexes remain unchanged. The all-playlist course shelf links to this report from its [approval board](../08_دورات_القوائم/10_مسودات_القوائم/03_لوحة_المراجعة/index.html).

For experimental local answer drafting, separately install a trusted `llama-cli` and place a compatible GGUF model on the machine. With both already present, and after building the index:

```sh
python3 ayman_rag/answer.py 'ما المقصود بالشك المنهجي؟' --model /path/to/local-model.gguf
# Optional: --llama-cli /path/to/llama-cli --folder 'exact folder name'
# Optional retrieval filters: --source-id drive-... --playlist cognitive-foundation-1 --match all
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
