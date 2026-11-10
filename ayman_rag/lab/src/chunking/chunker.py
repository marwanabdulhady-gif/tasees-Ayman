"""Stage 1b — split lectures into chunks small enough to search and to show an LLM.

Why chunk at all? A whole lecture is ~10,000 words: too long to send as
context, and too broad to rank against one question. A chunk of ~400 words
is about one idea.

Why overlap? If an idea starts at the end of one chunk, the overlap repeats
it at the start of the next, so it is never cut in half.

We build chunks from whole paragraphs, so every chunk still knows the second
in the video where it starts.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.ingestion.loader import Lecture
from src.utils.helpers import format_timestamp


@dataclass
class Chunk:
    id: str              # e.g. "03-psychology/01#004"
    course: str
    lecture_number: int
    lecture_title: str
    start_seconds: int
    url: str             # opens the video at the moment this chunk starts
    text: str

    def citation(self) -> str:
        return f"{self.lecture_title} — {format_timestamp(self.start_seconds)}"


def _video_link(base_url: str, seconds: int) -> str:
    if not base_url:
        return ""
    return f"{base_url}{'&' if '?' in base_url else '?'}t={seconds}s"


def chunk_lecture(lecture: Lecture, chunk_words: int = 400, overlap_words: int = 50) -> list[Chunk]:
    chunks: list[Chunk] = []
    paras = lecture.paragraphs
    i = 0
    while i < len(paras):
        words, j = 0, i
        while j < len(paras) and (words < chunk_words or j == i):
            words += len(paras[j].text.split())
            j += 1
        text = " ".join(p.text for p in paras[i:j])
        start = paras[i].start_seconds
        chunks.append(Chunk(
            id=f"{lecture.course}/{lecture.number:02d}#{len(chunks):03d}",
            course=lecture.course,
            lecture_number=lecture.number,
            lecture_title=lecture.title,
            start_seconds=start,
            url=_video_link(lecture.url, start),
            text=text,
        ))
        if j >= len(paras):
            break
        # Step back far enough to repeat about `overlap_words` words.
        back, k = 0, j
        while k > i + 1 and back < overlap_words:
            k -= 1
            back += len(paras[k].text.split())
        i = k
    return chunks


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def load_chunks(path: Path) -> list[Chunk]:
    with open(path, encoding="utf-8") as f:
        return [Chunk(**json.loads(line)) for line in f if line.strip()]
