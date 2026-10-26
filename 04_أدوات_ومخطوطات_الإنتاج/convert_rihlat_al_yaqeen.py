#!/usr/bin/env python3
"""Convert the supplied رحلة اليقين PDF transcripts into Markdown files."""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

FOLDER_URL = "https://drive.google.com/drive/u/0/folders/1CF4lGOnc_PGKvvtU8yRi7h_fPYdd24ZY"
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
NUMBER_PREFIX = re.compile(r"^(\d+)-")
MULTI_BLANK = re.compile(r"\n{3,}")


def clean_filename(value: str) -> str:
    value = INVALID_FILENAME.sub("_", value).strip().rstrip(". ")
    return value[:180] or "untitled"


def sort_key(path: Path) -> tuple[int, str]:
    match = NUMBER_PREFIX.match(path.name)
    return (int(match.group(1)) if match else 10_000, path.name.casefold())


def clean_text(value: str) -> str:
    """Retain the transcription while removing extraction-only artifacts."""
    value = unicodedata.normalize("NFC", value).replace("\r\n", "\n")
    value = value.replace("\uf0cb", "•").replace("\uf0db", "•")
    lines: list[str] = []
    for line in value.splitlines():
        line = line.strip()
        # Page-number lines are not part of the transcript itself.
        if line.isascii() and line.isdigit() and len(line) <= 3:
            continue
        lines.append(line)
    return MULTI_BLANK.sub("\n\n", "\n".join(lines)).strip()


def write_markdown(pdf: Path, destination: Path) -> tuple[bool, str, int]:
    title = pdf.stem
    try:
        reader = PdfReader(str(pdf))
        text = clean_text("\n\n".join(page.extract_text() or "" for page in reader.pages))
        if not text:
            raise ValueError("No extractable text was found in the PDF.")
        converted_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        content = "\n".join(
            [
                "---",
                f'title: "{title.replace(chr(34), chr(92) + chr(34))}"',
                'series: "رحلة اليقين"',
                f'source_folder: "{FOLDER_URL}"',
                f'source_file: "{pdf.name.replace(chr(34), chr(92) + chr(34))}"',
                f'converted_at_utc: "{converted_at}"',
                "---",
                "",
                f"# {title}",
                "",
                "## التفريغ",
                "",
                text,
                "",
            ]
        )
        destination.write_text(content, encoding="utf-8")
        return True, "", len(text)
    except Exception as error:
        content = f"# {title}\n\n## تعذر استخراج النص\n\n> {error}\n"
        destination.write_text(content, encoding="utf-8")
        return False, str(error), 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert رحلة اليقين PDF transcripts to Markdown.")
    parser.add_argument("source_dir", type=Path, help="Folder containing the downloaded PDF files")
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("rihlat_al_yaqeen_transcripts")
    )
    args = parser.parse_args()

    pdfs = sorted(args.source_dir.glob("*.pdf"), key=sort_key)
    if not pdfs:
        parser.error(f"No PDF files found in {args.source_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for sequence, pdf in enumerate(pdfs, start=1):
        destination = args.output_dir / f"{sequence:02d} - {clean_filename(pdf.stem)}.md"
        success, message, characters = write_markdown(pdf, destination)
        rows.append(
            {
                "sequence": sequence,
                "source_file": pdf.name,
                "markdown_file": destination.name,
                "status": "saved" if success else "unavailable",
                "characters": characters,
                "message": message,
            }
        )
        print(f"[{sequence}/{len(pdfs)}] {'saved' if success else 'unavailable'}: {pdf.name}")

    with (args.output_dir / "_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Done: {sum(row['status'] == 'saved' for row in rows)}/{len(rows)} saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
