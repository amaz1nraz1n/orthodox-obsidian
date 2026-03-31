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

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _write(path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Generated: %s", path)
