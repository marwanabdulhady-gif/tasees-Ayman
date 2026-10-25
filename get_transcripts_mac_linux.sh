#!/usr/bin/env bash
# Double-click this file on macOS, or run ./get_transcripts_mac_linux.sh in a terminal,
# to download every transcript on your own computer (needs Python 3.10+).
set -u
cd "$(dirname "$0")" || exit 1

finish() {
    echo
    if [ -t 0 ]; then
        read -r -p "Press Enter to close this window…" _ || true
    fi
}

fail() {
    echo
    echo "$1"
    finish
    exit 1
}

command -v python3 >/dev/null 2>&1 \
    || fail "Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again."

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    || fail "Python 3.10 or newer is required (this computer has $(python3 -V 2>&1))."

if [ ! -x .venv/bin/python ]; then
    echo "Setting up the Python environment (first run only)…"
    python3 -m venv .venv || fail "Could not create the .venv folder. Install Python from python.org and try again."
fi

./.venv/bin/python -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
./.venv/bin/python -m pip install --quiet --upgrade -r scripts/requirements.txt \
    || fail "Could not install the required packages. Check your internet connection and try again."

echo
echo "Downloading transcripts. You can stop at any time — run this again to continue."
echo
./.venv/bin/python scripts/fetch_transcripts.py "$@"
status=$?

echo
if [ "$status" -eq 0 ]; then
    echo "Done. The transcripts are in the transcripts folder."
    echo "If any episode is missing, run this again — it carries on from where it stopped."
else
    echo "The run ended with an error — see the messages above."
    echo "The full log is in transcripts/_last_run.log"
fi
finish
exit "$status"
