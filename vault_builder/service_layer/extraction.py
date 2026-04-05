"""
Service layer: ExtractionService

Orchestrates the extract → render → write pipeline for a single source.
Accepts abstract ports so it can be tested with fakes (no real EPUB/PDF).

Two modes:
  HUB       — produces hub files (canonical text) + notes companions.
              Used by OSB.
  COMPANION — produces text companion files + notes companions.
              Used by Lexham, EOB, Greek NT/LXX.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from vault_builder.domain.canon import book_file_prefix
from vault_builder.domain.models import ChapterFathers
from vault_builder.ports.parallel_source import ParallelSource
from vault_builder.ports.patristic_source import PatristicSource
from vault_builder.ports.renderer import VaultRenderer
from vault_builder.ports.source import ScriptureSource
from vault_builder.ports.writer import VaultWriter

logger = logging.getLogger(__name__)


class ExtractionMode(Enum):
    HUB = "hub"
    COMPANION = "companion"


@dataclass
class ExtractionResult:
    hubs_written: int = 0
    companions_written: int = 0
    notes_written: int = 0
    intros_written: int = 0
    fathers_written: int = 0
    parallels_written: int = 0
    translations_written: int = 0
    errors: int = 0
    error_log: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = []
        if self.hubs_written:
            parts.append(f"{self.hubs_written} hubs")
        if self.companions_written:
            parts.append(f"{self.companions_written} companions")
        if self.notes_written:
            parts.append(f"{self.notes_written} notes")
        if self.intros_written:
            parts.append(f"{self.intros_written} intros")
        if self.fathers_written:
            parts.append(f"{self.fathers_written} fathers")
        if self.parallels_written:
            parts.append(f"{self.parallels_written} parallels")
        if self.translations_written:
            parts.append(f"{self.translations_written} translations")
        total = ", ".join(parts) or "0 files"
        err = f" ({self.errors} errors)" if self.errors else ""
        return f"{total} written{err}"


class ExtractionService:
    """
    Runs the full extract → render → write pipeline for one source.

    Args:
        source:       Implements ScriptureSource (real adapter or fake).
        renderer:     Implements VaultRenderer.
        writer:       Implements VaultWriter.
        mode:         HUB (OSB-style) or COMPANION (Lexham/EOB-style).
        source_label: Display name for companion files (e.g. "Lexham").
                      Required when mode=COMPANION.
    """

    def __init__(
        self,
        source: ScriptureSource,
        renderer: VaultRenderer,
        writer: VaultWriter,
        mode: ExtractionMode = ExtractionMode.HUB,
        source_label: str = "",
        patristic_source: PatristicSource | None = None,
        parallel_source: ParallelSource | None = None,
        fathers_chapters: set[tuple[str, int]] | None = None,
    ) -> None:
        self._source = source
        self._renderer = renderer
        self._writer = writer
        self._mode = mode
        self._source_label = source_label
        self._patristic_source = patristic_source
        self._parallel_source = parallel_source
        self._fathers_chapters = set(fathers_chapters or set())

    def extract(self) -> ExtractionResult:
        result = ExtractionResult()
        fathers_items: list[ChapterFathers] = []

        # 0. Patristic sources are optionally preloaded so downstream renderers
        # can know which chapters have Fathers companions before chapter files
        # are rendered.
        if self._patristic_source is not None:
            fathers_items = list(self._patristic_source.read_fathers())
            self._fathers_chapters.update(
                {(fathers.book, fathers.chapter) for fathers in fathers_items}
            )

        # 1. Book introductions (optional — most sources yield nothing)
        books_with_intros: set[str] = set()
        for intro in self._source.read_intros():
            try:
                content = self._renderer.render_book_intro(intro.book, intro.content)
                self._writer.write_book_intro(intro.book, content)
                books_with_intros.add(intro.book)
                result.intros_written += 1
            except Exception as exc:
                msg = f"intro {intro.book}: {exc}"
                logger.error(msg)
                result.errors += 1
                result.error_log.append(msg)

        # 2. Chapter text
        for book in self._source.read_text():
            max_ch = book.max_chapter()
            for chapter in sorted(book.chapters.values(), key=lambda c: c.number):
                try:
                    has_fathers = (chapter.book, chapter.number) in self._fathers_chapters
                    if self._mode is ExtractionMode.HUB:
                        intro_link = (
                            f"[[{book_file_prefix(chapter.book)} — OSB Intro]]"
                            if chapter.number == 1 and chapter.book in books_with_intros
                            else None
                        )
                        content = self._renderer.render_hub(
                            chapter, max_ch, intro_link=intro_link, has_fathers=has_fathers
                        )
                        self._writer.write_hub(chapter, content)
                        result.hubs_written += 1
                    else:
                        content = self._renderer.render_text_companion(
                            chapter,
                            self._source_label,
                            has_fathers=has_fathers,
                        )
                        self._writer.write_text_companion(
                            chapter, self._source_label, content
                        )
                        result.companions_written += 1
                    self._update_translations_hub(chapter.book, chapter.number, result)
                except Exception as exc:
                    msg = f"text {chapter.book} {chapter.number}: {exc}"
                    logger.error(msg)
                    result.errors += 1
                    result.error_log.append(msg)

        # 3. Notes companions
        for notes in self._source.read_notes():
            try:
                has_fathers = (notes.book, notes.chapter) in self._fathers_chapters
                content = self._renderer.render_notes(notes, has_fathers=has_fathers)
                self._writer.write_notes(notes, content)
                result.notes_written += 1
            except Exception as exc:
                msg = f"notes {notes.book} {notes.chapter}: {exc}"
                logger.error(msg)
                result.errors += 1
                result.error_log.append(msg)

        # 4. Patristic catena companions (optional)
        for fathers in fathers_items:
            try:
                content = self._renderer.render_fathers(fathers)
                self._writer.write_fathers(fathers.book, fathers.chapter, content)
                result.fathers_written += 1
            except Exception as exc:
                msg = f"fathers {fathers.book} {fathers.chapter}: {exc}"
                logger.error(msg)
                result.errors += 1
                result.error_log.append(msg)

        # 5. Parallel passage companions (optional)
        if self._parallel_source is not None:
            for cn in self._parallel_source.read_parallels():
                try:
                    has_fathers = (cn.book, cn.chapter) in self._fathers_chapters
                    content = self._renderer.render_notes(cn, has_fathers=has_fathers)
                    self._writer.write_parallels(cn.book, cn.chapter, content)
                    result.parallels_written += 1
                except Exception as exc:
                    msg = f"parallels {cn.book} {cn.chapter}: {exc}"
                    logger.error(msg)
                    result.errors += 1
                    result.error_log.append(msg)

        logger.info("Extraction complete: %s", result.summary())
        return result

    def _update_translations_hub(self, book: str, chapter: int, result: ExtractionResult) -> None:
        try:
            sources = self._writer.list_text_companions(book, chapter)
            if sources:
                content = self._renderer.render_translations_hub(book, chapter, sources)
                self._writer.write_translations_hub(book, chapter, content)
                result.translations_written += 1
        except Exception as exc:
            msg = f"translations hub {book} {chapter}: {exc}"
            logger.error(msg)
            result.errors += 1
            result.error_log.append(msg)
