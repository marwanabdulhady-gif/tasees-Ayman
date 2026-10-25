#!/usr/bin/env bash
# Download all transcripts on your own computer (needs Python 3.10+).
set -e
cd "$(dirname "$0")"
python3 -m pip install --upgrade -r scripts/requirements.txt
python3 scripts/fetch_transcripts.py
echo "Done. Transcripts are in the transcripts folder."
