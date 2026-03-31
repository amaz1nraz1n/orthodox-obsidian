"""
Domain exceptions for vault_builder.

Raised by domain aggregates and service layer. Prefer these over bare
ValueError/KeyError so callers can distinguish domain errors from
programming errors.
"""


class VaultDomainError(Exception):
    """Base class for all domain-layer errors."""


class DuplicateVerseError(VaultDomainError):
    """Raised when add_verse() is called with a verse number already present."""

    def __init__(self, book: str, chapter: int, verse: int) -> None:
        super().__init__(f"Duplicate verse {book} {chapter}:{verse}")
        self.book = book
        self.chapter = chapter
        self.verse = verse


class DuplicateChapterError(VaultDomainError):
    """Raised when add_chapter() is called with a chapter number already present."""

    def __init__(self, book: str, chapter: int) -> None:
        super().__init__(f"Duplicate chapter {book}:{chapter}")
        self.book = book
        self.chapter = chapter


class UnknownBookError(VaultDomainError):
    """Raised when a book name is not found in the canon registry."""

    def __init__(self, book: str) -> None:
        super().__init__(f"Unknown book: {book!r}")
        self.book = book


class MissingSourceError(VaultDomainError):
    """Raised when a required source file or path is not available."""

    def __init__(self, source: str, path: str = "") -> None:
        msg = f"Missing source: {source!r}"
        if path:
            msg += f" (expected at {path})"
        super().__init__(msg)
        self.source = source
        self.path = path
