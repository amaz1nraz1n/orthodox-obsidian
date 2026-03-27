"""
Adapter: ObsidianWriter

Resolves file paths and writes rendered content to disk, following the
vault folder/naming conventions defined in vault_builder.domain.canon.
"""

import logging
import os

from vault_builder.domain.canon import book_file_prefix, book_folder_path
from vault_builder.domain.models import Chapter, ChapterNotes

logger = logging.getLogger(__name__)


class ObsidianWriter:

    def __init__(self, output_root: str = "Scripture"):
        self.output_root = output_root

    # ── Hub files ─────────────────────────────────────────────────────────────

    def write_hub(self, chapter: Chapter, content: str) -> str:
        """Write hub content to disk. Returns the path written."""
        path = self._hub_path(chapter.book, chapter.number)
        self._write(path, content)
        return path

    def _hub_path(self, book: str, chapter: int) -> str:
        book_dir = os.path.join(self.output_root, book_folder_path(book))
        os.makedirs(book_dir, exist_ok=True)
        return os.path.join(book_dir, f"{book_file_prefix(book)} {chapter}.md")

    # ── Text companion files ──────────────────────────────────────────────────

    def write_text_companion(self, chapter: "Chapter", source: str, content: str) -> str:
        """Write a parallel text layer companion. Returns the path written."""
        path = self._text_companion_path(chapter.book, chapter.number, source)
        self._write(path, content)
        return path

    def _text_companion_path(self, book: str, chapter: int, source: str) -> str:
        book_dir = os.path.join(self.output_root, book_folder_path(book))
        os.makedirs(book_dir, exist_ok=True)
        return os.path.join(book_dir, f"{book_file_prefix(book)} {chapter} \u2014 {source}.md")

    # ── Notes companion files ─────────────────────────────────────────────────

    def write_notes(self, notes: ChapterNotes, content: str) -> str:
        """Write companion notes content to disk. Returns the path written."""
        path = self._notes_path(notes.book, notes.chapter, notes.source)
        self._write(path, content)
        return path

    def _notes_path(self, book: str, chapter: int, source: str) -> str:
        book_dir = os.path.join(self.output_root, book_folder_path(book))
        os.makedirs(book_dir, exist_ok=True)
        return os.path.join(book_dir, f"{book_file_prefix(book)} {chapter} \u2014 {source} Notes.md")

    # ── Book intro files ──────────────────────────────────────────────────────

    def write_book_intro(self, book: str, content: str) -> str:
        """Write a per-book intro companion. Returns the path written."""
        path = self._book_intro_path(book)
        self._write(path, content)
        return path

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
