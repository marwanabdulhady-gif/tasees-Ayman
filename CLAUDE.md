# Instructions for every AI agent in this repository

Before you change anything visual or interactive, read
**[`07_الهوية_البصرية_والتفاعل/04_تعليمات_وكلاء_الذكاء_الاصطناعي.md`](07_الهوية_البصرية_والتفاعل/04_تعليمات_وكلاء_الذكاء_الاصطناعي.md)**
from top to bottom (English summary in its §6).

The short version:

1. Take the first task in §4 of that file that is not done and not blocked. One task, one unit, one branch, one pull request.
2. No faces of prophets, companions or any real person (Ayman Abdulrahim included). No text, letters or numbers inside generated images.
3. Never change course wording or add facts. The scripts in `02_الوحدات_التعليمية/*/01_الأصول_النصية/` are the source.
4. Colours and fonts come only from `07_الهوية_البصرية_والتفاعل/templates/tokens.json`.
5. Never delete an old file; new versions sit next to old ones. Never hand-edit generated files.
6. Run the checks in §3, open a pull request, never merge it yourself, and end with the report in §5.

Two new task families: the six atlases inside the course (patterns P19/P20, tasks A0 and A5) and one short course per playlist in `08_دورات_القوائم/` (tasks D0–D4; check with `08_دورات_القوائم/tools/check_playlist_course.py <slug>`).

The owner is still editing the course. Run `07_الهوية_البصرية_والتفاعل/tools/check_drift.py <your weeks>` before you start and before you commit; if your week drifted, report it and move on.

If something is unclear or a step fails, stop and report it. Do not guess.
