"""
Port: VaultWriter

Defines the interface all vault write adapters must implement.
Separating this from VaultRenderer allows the writer to be swapped
independently (e.g. dry-run, in-memory, alternative vault layout).
"""

from abc import ABC, abstractmethod
from pathlib import Path

from vault_builder.domain.models import Chapter, ChapterNotes


class VaultWriter(ABC):

    @abstractmethod
    def write_hub(self, chapter: Chapter, content: str) -> Path:
        """Write hub file content. Returns the path written."""

    @abstractmethod
    def write_text_companion(self, chapter: Chapter, source: str, content: str) -> Path:
        """Write a parallel text layer companion. Returns the path written."""

    @abstractmethod
    def write_notes(self, notes: ChapterNotes, content: str) -> Path:
        """Write companion notes content. Returns the path written."""

    @abstractmethod
    def write_book_intro(self, book: str, content: str) -> Path:
        """Write a per-book introduction companion. Returns the path written."""

    @abstractmethod
    def write_fathers(self, book: str, chapter: int, content: str) -> Path:
        """Write a Patristic catena companion. Returns the path written."""
