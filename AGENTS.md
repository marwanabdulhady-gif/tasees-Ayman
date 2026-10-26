# Instructions for every AI agent in this repository

> **START HERE: [`00_مهام_الوكلاء.md`](00_مهام_الوكلاء.md)** — the only task list. Pick the first ready task, follow its card step by step, run `python3 07_الهوية_البصرية_والتفاعل/tools/check_all.py` (must print `PASS`), open a pull request, never merge.

Before you change anything visual or interactive, read
**[`07_الهوية_البصرية_والتفاعل/04_تعليمات_وكلاء_الذكاء_الاصطناعي.md`](07_الهوية_البصرية_والتفاعل/04_تعليمات_وكلاء_الذكاء_الاصطناعي.md)**
from top to bottom (English summary in its §6).

The short version:

1. Take the first ready task in `00_مهام_الوكلاء.md` (not §4 of the instructions file — that is reference only). One task, one branch, one pull request.
2. No faces of prophets, companions or any real person (Ayman Abdulrahim included). No text, letters or numbers inside generated images.
3. Never change course wording or add facts. The scripts in `02_الوحدات_التعليمية/*/01_الأصول_النصية/` are the source.
4. Colours and fonts come only from `07_الهوية_البصرية_والتفاعل/templates/tokens.json`.
5. Never delete an old file; new versions sit next to old ones. Never hand-edit generated files.
6. Run the checks in §3, open a pull request, never merge it yourself, and end with the report in §5.

Two new task families: the six atlases inside the course (patterns P19/P20, tasks A0 and A5) and one short course per playlist in `08_دورات_القوائم/` (tasks D0–D4; check with `08_دورات_القوائم/tools/check_playlist_course.py <slug>`).

Build order and parallel lanes (P11 weeks first, who owns which file): `07_الهوية_البصرية_والتفاعل/07_خطة_البناء_B_والأصول.md`. Transcripts of every Ayman course beyond the five playlists: `09_تفريغات_أيمن/00_خطة_التفريغ.md` (tasks T0–T6).

The owner is still editing the course. Run `07_الهوية_البصرية_والتفاعل/tools/check_drift.py <your weeks>` before you start and before you commit; if your week drifted, report it and move on.

If something is unclear or a step fails, stop and report it. Do not guess.
