"""
Port: VaultRenderer

Defines the interface all vault output adapters must implement.
The application layer depends only on this abstraction — never on a
specific output format (Obsidian Markdown, HTML, etc.).
"""

from abc import ABC, abstractmethod

from vault_builder.domain.models import Chapter, ChapterFathers, ChapterNotes


class VaultRenderer(ABC):

    @abstractmethod
    def render_hub(
        self,
        chapter: Chapter,
        max_chapter: int,
        intro_link: str | None = None,
        has_fathers: bool = False,
    ) -> str:
        """Render the hub file content for a single chapter.

        Args:
            chapter: The fully-populated Chapter domain object.
            max_chapter: The highest chapter number in this book (used for
                         generating prev/next navigation links).
            intro_link: Optional wikilink to a per-book introduction file,
                        included only in chapter-1 hubs (e.g. "[[John — OSB Intro]]").
        """

    @abstractmethod
    def render_text_companion(
        self,
        chapter: Chapter,
        source: str,
        notes_suffix: str | None = None,
        has_fathers: bool = False,
    ) -> str:
        """Render a parallel text layer (e.g. Lexham, EOB, NET) as a companion file.

        Args:
            chapter: The fully-populated Chapter domain object.
            source: Display name for this text layer (e.g. "Lexham", "EOB").
            notes_suffix: Suffix for the companion notes link (e.g. "EOB Notes").
                          Pass None to suppress the link. When omitted, concrete
                          implementations default to f"{source} Notes".
            has_fathers: When True, include a Fathers companion link for the
                         current chapter after NET Notes.
        """

    @abstractmethod
    def render_notes(self, notes: ChapterNotes, has_fathers: bool = False) -> str:
        """Render a study notes companion file for a chapter.

        Args:
            notes: The ChapterNotes domain object for one chapter/source pair.
            has_fathers: When True, include a Fathers companion link for the
                         current chapter after NET Notes.
        """

    @abstractmethod
    def render_net_notes(
        self,
        notes: ChapterNotes,
        pericopes: dict[int, str] | None = None,
        has_fathers: bool = False,
    ) -> str:
        """Render a NET Bible notes companion with tn/tc/sn callouts.

        Args:
            notes: The ChapterNotes domain object.
            pericopes: Optional mapping of verse number → pericope heading text,
                       used to insert section headers within the notes file.
            has_fathers: When True, include a Fathers companion link after the
                         NET text link in the scoped nav.
        """

    @abstractmethod
    def render_book_intro(self, book: str, content: str) -> str:
        """Render a per-book introduction companion file.

        Args:
            book: Canonical book name (e.g. "John").
            content: Pre-rendered Markdown body from the source adapter.
        """

    @abstractmethod
    def render_fathers(self, fathers: ChapterFathers) -> str:
        """Render a Patristic catena companion file for a Scripture chapter.

        Args:
            fathers: The ChapterFathers domain object for one chapter/source pair.
        """

    @abstractmethod
    def render_patristic_chapter(
        self,
        chapter: Chapter,
        notes: ChapterNotes,
        max_chapter: int,
    ) -> str:
        """Render an Apostolic Fathers chapter as a single self-contained file.

        Combines verse text and footnotes inline — unlike Scripture hub+companion
        pairs, patristic chapters render as one unified document per chapter.

        Args:
            chapter: The fully-populated Chapter domain object.
            notes: Footnotes and annotations for the chapter.
            max_chapter: Highest chapter in this document (for prev/next nav).
        """
