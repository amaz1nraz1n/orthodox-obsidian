"""
Adapter: ParallelPassageSource

Reads data/parallel_passages.yaml and yields ChapterNotes objects
containing NoteType.PARALLEL notes for each verse that has known
synoptic or typological parallels.

For each parallel group, the adapter emits bidirectional links: every
passage in the group receives a note pointing to all other passages in
the group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import yaml

from vault_builder.domain.canon import book_file_prefix
from vault_builder.domain.models import ChapterNotes, NoteType, StudyNote
from vault_builder.ports.parallel_source import ParallelSource

_DEFAULT_DATA = Path(__file__).parents[3] / "data" / "parallel_passages.yaml"


def _ref_link(book: str, chapter: int, verse_start: int, verse_end: int | None) -> str:
    """Build a wikilink for a single passage reference."""
    pfx = book_file_prefix(book)
    if verse_end and verse_end != verse_start:
        label = f"{book} {chapter}:{verse_start}-{verse_end}"
    else:
        label = f"{book} {chapter}:{verse_start}"
    return f"[[{pfx} {chapter}#v{verse_start}|{label}]]"


class ParallelPassageSource(ParallelSource):
    """
    Emits bidirectional NoteType.PARALLEL notes from a YAML parallel table.

    One ChapterNotes per (book, chapter) pair; one StudyNote per pericope
    entry that falls in that chapter.
    """

    def __init__(self, data_path: Path | str = _DEFAULT_DATA) -> None:
        self.data_path = Path(data_path)

    def read_parallels(self) -> Iterator[ChapterNotes]:
        """Yield ChapterNotes for every chapter that has parallel notes."""
        with open(self.data_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Accumulate notes: (book, chapter) → list of StudyNote
        chapter_notes: dict[tuple[str, int], list[StudyNote]] = {}

        for group in data.get("parallels", []):
            passages = group["passages"]
            if len(passages) < 2:
                continue

            for i, primary in enumerate(passages):
                book = primary["book"]
                chapter = primary["chapter"]
                verse_start = primary["verse_start"]
                verse_end = primary.get("verse_end")

                others = [p for j, p in enumerate(passages) if j != i]
                link_parts = [
                    _ref_link(p["book"], p["chapter"], p["verse_start"], p.get("verse_end"))
                    for p in others
                ]
                content = " · ".join(link_parts)

                if verse_end and verse_end != verse_start:
                    ref_str = f"{chapter}:{verse_start}-{verse_end}"
                else:
                    ref_str = f"{chapter}:{verse_start}"

                note = StudyNote(
                    verse_number=verse_start,
                    verse_end=verse_end,
                    ref_str=ref_str,
                    content=content,
                )
                chapter_notes.setdefault((book, chapter), []).append(note)

        for (book, chapter), notes in sorted(chapter_notes.items()):
            cn = ChapterNotes(book=book, chapter=chapter, source="Parallels")
            for note in notes:
                cn.add_note(NoteType.PARALLEL, note)
            yield cn
