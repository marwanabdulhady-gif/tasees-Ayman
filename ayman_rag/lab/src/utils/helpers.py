"""Small shared helpers: config loading, logging, Arabic normalisation."""

import logging
import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path = PROJECT_ROOT / "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(path: str) -> Path:
    """Paths in config.yaml are relative to the project folder."""
    return (PROJECT_ROOT / path).resolve()


def get_logger(config: dict) -> logging.Logger:
    log_file = resolve(config["logging"]["file"])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=config["logging"]["level"],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger("ayman-rag")


# Arabic letters that mean the same thing for search but are typed differently.
_TASHKEEL = re.compile(r"[ً-ْٰـ]")  # harakat, dagger alef, tatweel
_ALEF = re.compile("[أإآٱ]")


def normalize_arabic(text: str) -> str:
    """Make 'الإسلام', 'الاسلام' and 'الإِسْلَام' look identical to the search.

    The transcripts are YouTube auto-captions, so they already write ة as ه
    (e.g. 'المحاضره'). We do the same so a typed question matches them.
    """
    text = _TASHKEEL.sub("", text)
    text = _ALEF.sub("ا", text)
    text = text.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    """Split normalised text into words, dropping punctuation."""
    return re.findall(r"[\w]+", normalize_arabic(text))


def format_timestamp(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
