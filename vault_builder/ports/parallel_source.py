"""
Port: ParallelSource

Defines the interface for sources that yield ChapterNotes containing
NoteType.PARALLEL notes (synoptic/typological parallel passage links).
"""

from abc import ABC, abstractmethod
from typing import Iterator

from vault_builder.domain.models import ChapterNotes


class ParallelSource(ABC):

    @abstractmethod
    def read_parallels(self) -> Iterator[ChapterNotes]:
        """Yield ChapterNotes objects populated with NoteType.PARALLEL notes.

        Each ChapterNotes covers one book/chapter pair and may contain
        multiple PARALLEL notes, one per verse that has known parallels.
        """
