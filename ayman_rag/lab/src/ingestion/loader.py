"""Stage 1a — read Ayman's transcript files into Python objects.

Each transcript file looks like this:

    # دورة علم النفس أيمن عبدالرحيم  المحاضرة الأولي
    - الحلقة: 1
    - الرابط: https://www.youtube.com/watch?v=jmcCEitwVvc
    ---
    **[00:18](https://www.youtube.com/watch?v=...&t=18s)** النص ...
    **[01:23](https://www.youtube.com/watch?v=...&t=83s)** النص ...

We keep every timestamped paragraph separately, so a search result can later
link straight to the second in the video where Ayman says it.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

_PARAGRAPH = re.compile(r"^\*\*\[[\d:]+\]\(([^)]*)\)\*\*\s*(.+)$")
_SECONDS = re.compile(r"[?&]t=(\d+)s?")


@dataclass
class Paragraph:
    start_seconds: int
    text: str


@dataclass
class Lecture:
    course: str          # playlist folder, e.g. "03-psychology"
    number: int          # episode number within the playlist
    title: str
    url: str
    paragraphs: list[Paragraph] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(len(p.text.split()) for p in self.paragraphs)


def parse_transcript(path: Path, course: str) -> Lecture:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), path.stem)
    title = re.sub(r"\s+", " ", title)
    url = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("- الرابط:")), "")
    number_line = next((l for l in lines if l.startswith("- الحلقة:")), "")
    number = int(re.sub(r"\D", "", number_line) or 0)

    lecture = Lecture(course=course, number=number, title=title, url=url)
    for line in lines:
        m = _PARAGRAPH.match(line.strip())
        if not m:
            continue
        seconds = _SECONDS.search(m.group(1))
        lecture.paragraphs.append(Paragraph(int(seconds.group(1)) if seconds else 0, m.group(2).strip()))
    return lecture


def load_lectures(transcripts_dir: Path) -> list[Lecture]:
    """Read every lecture in every playlist folder. Skips the README index files."""
    lectures = []
    for course_dir in sorted(p for p in transcripts_dir.iterdir() if p.is_dir()):
        for path in sorted(course_dir.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            lecture = parse_transcript(path, course_dir.name)
            if lecture.paragraphs:
                lectures.append(lecture)
    return lectures
