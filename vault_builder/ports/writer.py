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

    @abstractmethod
    def write_parallels(self, book: str, chapter: int, content: str) -> Path:
        """Write a parallel passages companion. Returns the path written."""

    @abstractmethod
    def write_translations_hub(self, book: str, chapter: int, content: str) -> Path:
        """Write a per-chapter translations index. Returns the path written."""

    @abstractmethod
    def has_fathers_companion(self, book: str, chapter: int) -> bool:
        """Return True if a Fathers companion file exists for this chapter."""

    @abstractmethod
    def list_text_companions(self, book: str, chapter: int) -> list[tuple[str, str | None]]:
        """Return (display_label, file_suffix) pairs for text companions that exist.

        suffix=None means the entry is the hub file itself (OSB).
        Results are in canonical nav order.
        """

    @abstractmethod
    def write_book_index(self, book: str, content: str) -> Path:
        """Write a per-book chapter index file. Returns the path written."""
