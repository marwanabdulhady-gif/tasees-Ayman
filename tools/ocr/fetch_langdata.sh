#!/usr/bin/env bash
# Fetch Arabic + English LSTM models from the official Tesseract tessdata_fast
# repository through the GitHub API (no CDN, no runtime network dependency).
# The resulting .traineddata.gz files stay local to tools/ocr/lang-data/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p lang-data
for lang in ara eng; do
  if [ ! -s "lang-data/${lang}.traineddata" ]; then
    echo "fetching ${lang}.traineddata..."
    curl -fsSL -H "Accept: application/vnd.github.raw+json" \
      -o "lang-data/${lang}.traineddata" \
      "https://api.github.com/repos/tesseract-ocr/tessdata_fast/contents/${lang}.traineddata"
  fi
  gzip -kfc "lang-data/${lang}.traineddata" > "lang-data/${lang}.traineddata.gz"
done
ls -lh lang-data/
