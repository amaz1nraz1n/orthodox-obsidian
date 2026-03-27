"""
Port: ScriptureSource

Defines the interface all scripture source adapters must implement.
The application layer depends only on this abstraction — never on a
specific format (EPUB, plain text, API, etc.).
"""

from abc import ABC, abstractmethod
from typing import Iterator

from vault_builder.domain.models import Book, BookIntro, ChapterNotes


class ScriptureSource(ABC):

    @abstractmethod
    def read_text(self) -> Iterator[Book]:
        """Yield fully-populated Book objects with all chapters and verses."""

    @abstractmethod
    def read_notes(self) -> Iterator[ChapterNotes]:
        """Yield ChapterNotes objects for every chapter that has study content."""

    def read_intros(self) -> Iterator[BookIntro]:
        """Yield BookIntro objects for each book that has an introduction.

        Non-abstract — default yields nothing. Adapters without intro content
        need not override this method.
        """
        return iter([])
