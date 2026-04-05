"""
Adapter: ObsidianWriter

Resolves file paths and writes rendered content to disk, following the
vault folder/naming conventions defined in vault_builder.domain.canon.
"""

import logging
import os
from pathlib import Path

from vault_builder.domain.canon import book_file_prefix, book_folder_path
from vault_builder.domain.models import Chapter, ChapterNotes
from vault_builder.ports.writer import VaultWriter

logger = logging.getLogger(__name__)


class ObsidianWriter(VaultWriter):

    def __init__(self, output_root: str = "Scripture"):
        self.output_root = output_root

    # ── Hub files ─────────────────────────────────────────────────────────────

    def write_hub(self, chapter: Chapter, content: str) -> Path:
        """Write hub content to disk. Returns the path written."""
        path = self._hub_path(chapter.book, chapter.number)
        self._write(path, content)
        return Path(path)

    def _chapter_dir(self, book: str, chapter: int) -> str:
        book_dir = os.path.join(self.output_root, book_folder_path(book))
        ch_dir = os.path.join(book_dir, f"Chapter {chapter:02d}")
        os.makedirs(ch_dir, exist_ok=True)
        return ch_dir

    def _hub_path(self, book: str, chapter: int) -> str:
        ch_dir = self._chapter_dir(book, chapter)
        return os.path.join(ch_dir, f"{book_file_prefix(book)} {chapter}.md")

    # ── Text companion files ──────────────────────────────────────────────────

    def write_text_companion(self, chapter: Chapter, source: str, content: str) -> Path:
        """Write a parallel text layer companion. Returns the path written."""
        path = self._text_companion_path(chapter.book, chapter.number, source)
        self._write(path, content)
        return Path(path)

    def _text_companion_path(self, book: str, chapter: int, source: str) -> str:
        ch_dir = self._chapter_dir(book, chapter)
        return os.path.join(ch_dir, f"{book_file_prefix(book)} {chapter} \u2014 {source}.md")

    # ── Notes companion files ─────────────────────────────────────────────────

    def write_notes(self, notes: ChapterNotes, content: str) -> Path:
        """Write companion notes content to disk. Returns the path written."""
        path = self._notes_path(notes.book, notes.chapter, notes.source)
        self._write(path, content)
        return Path(path)

    def _notes_path(self, book: str, chapter: int, source: str) -> str:
        ch_dir = self._chapter_dir(book, chapter)
        return os.path.join(ch_dir, f"{book_file_prefix(book)} {chapter} \u2014 {source} Notes.md")

    # ── Book intro files ──────────────────────────────────────────────────────

    def write_book_intro(self, book: str, content: str) -> Path:
        """Write a per-book intro companion. Returns the path written."""
        path = self._book_intro_path(book)
        self._write(path, content)
        return Path(path)

    def _book_intro_path(self, book: str) -> str:
        book_dir = os.path.join(self.output_root, book_folder_path(book))
        os.makedirs(book_dir, exist_ok=True)
        return os.path.join(book_dir, f"{book_file_prefix(book)} \u2014 OSB Intro.md")

    # ── Patristic catena files ────────────────────────────────────────────────

    def write_fathers(self, book: str, chapter: int, content: str) -> Path:
        """Write a Patristic catena companion. Returns the path written."""
        path = self._fathers_path(book, chapter)
        self._write(path, content)
        return Path(path)

    def _fathers_path(self, book: str, chapter: int) -> str:
        ch_dir = self._chapter_dir(book, chapter)
        return os.path.join(ch_dir, f"{book_file_prefix(book)} {chapter} \u2014 Fathers.md")

    # ── Parallel passages files ───────────────────────────────────────────────

    def write_parallels(self, book: str, chapter: int, content: str) -> Path:
        """Write a parallel passages companion. Returns the path written."""
        path = self._parallels_path(book, chapter)
        self._write(path, content)
        return Path(path)

    def _parallels_path(self, book: str, chapter: int) -> str:
        ch_dir = self._chapter_dir(book, chapter)
        return os.path.join(ch_dir, f"{book_file_prefix(book)} {chapter} \u2014 Parallels.md")

    # ── Translations hub ──────────────────────────────────────────────────────

    # Canonical order for all known text companions.
    # (file_suffix, display_label) — suffix None = hub file itself (OSB).
    _TEXT_COMPANION_SLOTS: list[tuple[str | None, str]] = [
        (None,        "OSB"),
        ("EOB",       "EOB"),
        ("Lexham",    "Lexham"),
        ("Greek NT",  "Greek NT"),
        ("LXX",       "LXX"),
        ("NET",       "NET"),
        ("Alter",     "Alter"),
        ("DBH",       "DBH"),
        ("NETS",      "NETS"),
        ("NOAB RSV",  "RSV"),
    ]

    def has_fathers_companion(self, book: str, chapter: int) -> bool:
        return os.path.exists(self._fathers_path(book, chapter))

    def write_translations_hub(self, book: str, chapter: int, content: str) -> Path:
        """Write a per-chapter translations index. Returns the path written."""
        path = self._translations_hub_path(book, chapter)
        self._write(path, content)
        return Path(path)

    def _translations_hub_path(self, book: str, chapter: int) -> str:
        ch_dir = self._chapter_dir(book, chapter)
        return os.path.join(ch_dir, f"{book_file_prefix(book)} {chapter} \u2014 Translations.md")

    def list_text_companions(self, book: str, chapter: int) -> list[tuple[str, str | None]]:
        """Return (display_label, file_suffix) pairs for text companions that exist on disk."""
        pfx = book_file_prefix(book)
        ch_dir = os.path.join(self.output_root, book_folder_path(book), f"Chapter {chapter:02d}")
        results: list[tuple[str, str | None]] = []
        for suffix, label in self._TEXT_COMPANION_SLOTS:
            if suffix is None:
                fname = f"{pfx} {chapter}.md"
            else:
                fname = f"{pfx} {chapter} \u2014 {suffix}.md"
            if os.path.exists(os.path.join(ch_dir, fname)):
                results.append((label, suffix))
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _write(path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Generated: %s", path)
