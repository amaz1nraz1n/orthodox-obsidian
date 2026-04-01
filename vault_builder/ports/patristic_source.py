"""
Port: PatristicSource

Defines the interface for sources that yield Patristic content keyed to
Scripture chapters (e.g. Apostolic Fathers citations, OSB Patristic notes).
Separate from ScriptureSource — not every source has Patristic content.
"""

from abc import ABC, abstractmethod
from typing import Iterator

from vault_builder.domain.models import ChapterFathers


class PatristicSource(ABC):

    @abstractmethod
    def read_fathers(self) -> Iterator[ChapterFathers]:
        """Yield one ChapterFathers per (book, chapter) with Patristic content."""
