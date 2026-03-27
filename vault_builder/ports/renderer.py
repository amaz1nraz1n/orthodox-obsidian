"""
Port: VaultRenderer

Defines the interface all vault output adapters must implement.
The application layer depends only on this abstraction — never on a
specific output format (Obsidian Markdown, HTML, etc.).
"""

from abc import ABC, abstractmethod

from vault_builder.domain.models import Chapter, ChapterNotes


class VaultRenderer(ABC):

    @abstractmethod
    def render_hub(self, chapter: Chapter, max_chapter: int) -> str:
        """Render the hub file content for a single chapter.

        Args:
            chapter: The fully-populated Chapter domain object.
            max_chapter: The highest chapter number in this book (used for
                         generating prev/next navigation links).

        Returns:
            Complete file content as a string (UTF-8).
        """

    @abstractmethod
    def render_notes(self, notes: ChapterNotes) -> str:
        """Render the companion notes file content for a chapter.

        Args:
            notes: The ChapterNotes domain object for one chapter/source pair.

        Returns:
            Complete file content as a string (UTF-8).
        """
