"""
In-memory fake ports for unit testing without real EPUB/PDF files.

Usage:
    source = FakeScriptureSource(books=[...], notes=[...])
    writer = FakeVaultWriter()
    # pass to ExtractionService or renderer tests
"""
from pathlib import Path
from typing import Iterator

from vault_builder.domain.models import Book, BookIntro, Chapter, ChapterFathers, ChapterNotes
from vault_builder.ports.parallel_source import ParallelSource
from vault_builder.ports.patristic_source import PatristicSource
from vault_builder.ports.source import ScriptureSource
from vault_builder.ports.writer import VaultWriter


class FakeParallelSource(ParallelSource):
    """In-memory ParallelSource for unit tests."""

    def __init__(self, parallels: list[ChapterNotes] | None = None) -> None:
        self._parallels = parallels or []

    def read_parallels(self):
        return iter(self._parallels)


class FakePatristicSource(PatristicSource):
    """In-memory PatristicSource for unit tests."""

    def __init__(self, fathers: list[ChapterFathers] | None = None) -> None:
        self._fathers = fathers or []

    def read_fathers(self):
        return iter(self._fathers)


class FakeScriptureSource(ScriptureSource):
    """In-memory ScriptureSource for unit tests."""

    def __init__(
        self,
        books: list[Book] | None = None,
        notes: list[ChapterNotes] | None = None,
        intros: list[BookIntro] | None = None,
    ) -> None:
        self._books = books or []
        self._notes = notes or []
        self._intros = intros or []

    def read_text(self) -> Iterator[Book]:
        return iter(self._books)

    def read_notes(self) -> Iterator[ChapterNotes]:
        return iter(self._notes)

    def read_intros(self) -> Iterator[BookIntro]:
        return iter(self._intros)


class FakeVaultWriter(VaultWriter):
    """Captures write calls in memory instead of touching disk."""

    def __init__(self) -> None:
        self.written_hubs: dict[tuple[str, int], str] = {}
        self.written_notes: dict[tuple[str, int, str], str] = {}
        self.written_companions: dict[tuple[str, int, str], str] = {}
        self.written_intros: dict[str, str] = {}
        self.written_fathers: dict[tuple[str, int], str] = {}
        self.written_parallels: dict[tuple[str, int], str] = {}
        self.written_translations: dict[tuple[str, int], str] = {}

    def write_hub(self, chapter: Chapter, content: str) -> Path:
        self.written_hubs[(chapter.book, chapter.number)] = content
        return Path(f"fake/{chapter.book}/{chapter.number}.md")

    def write_notes(self, notes: ChapterNotes, content: str) -> Path:
        self.written_notes[(notes.book, notes.chapter, notes.source)] = content
        return Path(f"fake/{notes.book}/{notes.chapter} — {notes.source} Notes.md")

    def write_text_companion(self, chapter: Chapter, source: str, content: str) -> Path:
        self.written_companions[(chapter.book, chapter.number, source)] = content
        return Path(f"fake/{chapter.book}/{chapter.number} — {source}.md")

    def write_book_intro(self, book: str, content: str) -> Path:
        self.written_intros[book] = content
        return Path(f"fake/{book} — Intro.md")

    def write_fathers(self, book: str, chapter: int, content: str) -> Path:
        self.written_fathers[(book, chapter)] = content
        return Path(f"fake/{book}/{chapter} — Fathers.md")

    def write_parallels(self, book: str, chapter: int, content: str) -> Path:
        self.written_parallels[(book, chapter)] = content
        return Path(f"fake/{book}/{chapter} — Parallels.md")

    def write_translations_hub(self, book: str, chapter: int, content: str) -> Path:
        self.written_translations[(book, chapter)] = content
        return Path(f"fake/{book}/{chapter} — Translations.md")

    def list_text_companions(self, book: str, chapter: int) -> list[tuple[str, str | None]]:
        results: list[tuple[str, str | None]] = []
        if (book, chapter) in self.written_hubs:
            results.append(("OSB", None))
        for (b, c, source) in self.written_companions:
            if b == book and c == chapter:
                label = "RSV" if source == "NOAB RSV" else source
                results.append((label, source))
        return results
