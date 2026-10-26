#!/usr/bin/env bash
# Download all transcripts on your own computer (needs Python 3.10+).
set -e
cd "$(dirname "$0")"
if python3 -m pip install --upgrade -r scripts/requirements.txt; then
  PY=python3
else
  echo "System pip is restricted (PEP 668) — creating a local .venv instead."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade -r scripts/requirements.txt
  PY=.venv/bin/python
fi
"$PY" scripts/fetch_transcripts.py
echo "Done. Transcripts are in the transcripts folder."
