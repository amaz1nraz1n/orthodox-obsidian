"""
Composition root: build a configured ExtractionService from a source name.

All concrete dependency construction lives here. Scripts and tests override
defaults by passing fake/alternative implementations.

Usage (script):
    service = bootstrap("osb")
    result  = service.extract()
    print(result.summary())

Usage (test):
    service = bootstrap("osb", source=FakeScriptureSource(...), writer=FakeVaultWriter())
    result  = service.extract()
"""

from __future__ import annotations

from typing import Optional

import yaml

from vault_builder.adapters.obsidian.renderer import ObsidianRenderer
from vault_builder.adapters.obsidian.writer import ObsidianWriter
from vault_builder.ports.parallel_source import ParallelSource
from vault_builder.ports.patristic_source import PatristicSource
from vault_builder.ports.renderer import VaultRenderer
from vault_builder.ports.source import ScriptureSource
from vault_builder.ports.writer import VaultWriter
from vault_builder.service_layer.extraction import ExtractionMode, ExtractionService

_SOURCES_YAML = "sources.yaml"

# Shared sample envelope used to flag Fathers companions in sample runs.
# This mirrors the representative chapters exercised by the current source
# adapters, plus the few outliers used by NOAB and the Lexham notes script.
FATHERS_SAMPLE_CHAPTERS: set[tuple[str, int]] = {
    ("Genesis", 1),
    ("Genesis", 2),
    ("Exodus", 20),
    ("Leviticus", 1),
    ("Numbers", 6),
    ("Deuteronomy", 6),
    ("Joshua", 1),
    ("I Kingdoms", 1),
    ("Psalms", 1),
    ("Psalms", 50),
    ("Psalms", 151),
    ("Job", 3),
    ("Proverbs", 8),
    ("Song of Solomon", 1),
    ("Sirach", 1),
    ("Tobit", 1),
    ("Wisdom of Solomon", 1),
    ("I Maccabees", 1),
    ("Isaiah", 7),
    ("Isaiah", 53),
    ("Jeremiah", 1),
    ("Ezekiel", 1),
    ("Ezra", 1),
    ("Nehemiah", 1),
    ("Daniel", 3),
    ("Matthew", 1),
    ("Matthew", 5),
    ("Matthew", 18),
    ("John", 1),
    ("John", 14),
    ("Acts", 15),
    ("Romans", 8),
    ("I Corinthians", 13),
    ("Luke", 9),
    ("Luke", 18),
    ("James", 1),
    ("Revelation", 1),
}

_OSB_SAMPLE: set[tuple[str, int]] = {
    ("Genesis",           1),
    ("Exodus",           20),
    ("Leviticus",         1),
    ("I Kingdoms",        1),
    ("I Maccabees",       1),
    ("Ezra",              1),
    ("Nehemiah",          1),
    ("Psalms",            1),
    ("Psalms",           50),
    ("Psalms",          151),
    ("Job",               3),
    ("Proverbs",          8),
    ("Song of Solomon",   1),
    ("Sirach",            1),
    ("Wisdom of Solomon", 1),
    ("Lamentations",      1),
    ("Isaiah",            7),
    ("Isaiah",           53),
    ("Jeremiah",          1),
    ("Ezekiel",           1),
    ("Daniel",            3),
    ("John",              1),
    ("Matthew",           1),
    ("Matthew",           5),
    ("Matthew",          18),
    ("Acts",             15),
    ("Romans",            8),
    ("I Corinthians",    13),
    ("Luke",              9),
    ("Luke",             18),
    ("John",             14),
    ("James",             1),
    ("Revelation",        1),
}

_LEXHAM_SAMPLE: set[tuple[str, int]] = {
    ("Genesis",          1),
    ("Exodus",          20),
    ("Leviticus",        1),
    ("I Kingdoms",       1),
    ("Psalms",           1),
    ("Psalms",          50),
    ("Job",              3),
    ("Proverbs",         8),
    ("Song of Solomon",  1),
    ("Sirach",           1),
    ("I Maccabees",      1),
    ("Lamentations",     1),
    ("Isaiah",           7),
    ("Isaiah",          53),
    ("Jeremiah",         1),
    ("Ezekiel",          1),
    ("Ezra",             1),
    ("Nehemiah",         1),
}

_EOB_SAMPLE: set[tuple[str, int]] = {
    ("Matthew",        1),
    ("Matthew",        5),
    ("Matthew",       18),
    ("John",           1),
    ("John",          14),
    ("Acts",          15),
    ("Romans",         8),
    ("I Corinthians", 13),
    ("Luke",           9),
    ("Luke",          18),
    ("James",          1),
    ("Revelation",     1),
}

_DBH_SAMPLE: set[tuple[str, int]] = {
    ("Matthew",        1),
    ("Matthew",        5),
    ("Matthew",       18),
    ("John",           1),
    ("John",          14),
    ("Acts",          15),
    ("Romans",         8),
    ("I Corinthians", 13),
    ("Luke",           9),
    ("Luke",          18),
    ("James",          1),
    ("Revelation",     1),
}

_NETS_SAMPLE: set[tuple[str, int]] = {
    ("Genesis",          1),
    ("Exodus",          20),
    ("Leviticus",        1),
    ("Psalms",           1),
    ("Psalms",          50),
    ("Job",              3),
    ("Proverbs",         8),
    ("Song of Songs",    1),
    ("Sirach",           1),
    ("Wisdom of Solomon", 1),
    ("1 Maccabees",      1),
    ("Lamentations",     1),
    ("Isaiah",           7),
    ("Isaiah",          53),
    ("Jeremiah",         1),
    ("Ezekiel",          1),
    ("Tobit",            1),
    ("Judith",           1),
}

_GREEK_LXX_SAMPLE: set[tuple[str, int]] = {
    ("Genesis",           1),
    ("Psalms",           50),
    ("Psalms",          151),
    ("Isaiah",            7),
    ("Wisdom of Solomon", 1),
    ("I Maccabees",       1),
    ("Sirach",            1),
    ("Daniel",            3),
}

_GREEK_NT_SAMPLE: set[tuple[str, int]] = {
    ("Matthew",        1),
    ("Matthew",        5),
    ("Matthew",       18),
    ("John",           1),
    ("John",          14),
    ("Acts",          15),
    ("Romans",         8),
    ("I Corinthians", 13),
    ("Luke",           9),
    ("Luke",          18),
    ("James",          1),
    ("Revelation",     1),
}

# Maps source short-name → (adapter class import path, ExtractionMode, label, sample_chapters)
_ALTER_SAMPLE: set[tuple[str, int]] = {
    ("Genesis",      1),
    ("Genesis",      2),
    ("Exodus",      20),
    ("Isaiah",       7),
    ("Isaiah",      53),
    ("Ruth",         1),
    ("Job",          3),
    ("Proverbs",     8),
    ("Jeremiah",     1),
    ("Ezekiel",      1),
}

_SOURCE_CONFIG: dict[str, tuple[str, ExtractionMode, str, set[tuple[str, int]]]] = {
    "osb":      ("vault_builder.adapters.sources.osb_epub:OsbEpubSource",     ExtractionMode.HUB,       "OSB",       _OSB_SAMPLE),
    "manley":   ("vault_builder.adapters.sources.manley_archive:ManleyArchiveSource", ExtractionMode.HUB, "Manley", FATHERS_SAMPLE_CHAPTERS),
    "lexham":   ("vault_builder.adapters.sources.lexham_epub:LexhamEpubSource", ExtractionMode.COMPANION, "Lexham",    _LEXHAM_SAMPLE),
    "eob":      ("vault_builder.adapters.sources.eob_epub:EobEpubSource",      ExtractionMode.COMPANION, "EOB",       _EOB_SAMPLE),
    "dbh":      ("vault_builder.adapters.sources.dbh_epub:DbhEpubSource",      ExtractionMode.COMPANION, "DBH",       _DBH_SAMPLE),
    "nets":     ("vault_builder.adapters.sources.nets_epub:NetsEpubSource",    ExtractionMode.COMPANION, "NETS",      _NETS_SAMPLE),
    "alter":    ("vault_builder.adapters.sources.alter_epub:AlterEpubSource",  ExtractionMode.COMPANION, "Alter",     _ALTER_SAMPLE),
    "greek_lxx":("vault_builder.adapters.sources.greek_lxx_csv:GreekLxxCsvSource", ExtractionMode.COMPANION, "Greek LXX", _GREEK_LXX_SAMPLE),
    "greek_nt": ("vault_builder.adapters.sources.goarch_greek_nt:GoarchGreekNtSource", ExtractionMode.COMPANION, "Greek NT", _GREEK_NT_SAMPLE),
}


def _load_source_path(source_name: str) -> str:
    with open(_SOURCES_YAML, encoding="utf-8") as f:
        registry = yaml.safe_load(f)
    entry = registry.get("sources", {}).get(source_name)
    if not entry:
        raise ValueError(f"Unknown source '{source_name}' in {_SOURCES_YAML}")
    return entry["path"]


def _build_source(
    source_name: str,
    adapter_spec: str,
    full_run: bool,
    sample_chapters: Optional[set[tuple[str, int]]] = None,
) -> ScriptureSource:
    module_path, class_name = adapter_spec.rsplit(":", 1)
    import importlib
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    path = _load_source_path(source_name)
    kwargs: dict = {"sample_only": not full_run}
    if sample_chapters is not None:
        kwargs["sample_chapters"] = sample_chapters
    return cls(path, **kwargs)


def bootstrap_fathers(
    source_name: str,
    *,
    output_dir: str = "output/Scripture",
    patristic_source: PatristicSource | None = None,
    renderer: VaultRenderer | None = None,
    writer: VaultWriter | None = None,
) -> ExtractionService:
    """
    Build an ExtractionService wired for Patristic catena output only.

    The service has no ScriptureSource (text/notes pass is a no-op) but
    will call read_fathers() on the PatristicSource and emit Fathers companions.

    Args:
        source_name:      Short label used in logging (e.g. "apostolic_fathers").
        output_dir:       Root directory for generated files.
        patristic_source: Override the PatristicSource (for testing).
        renderer:         Override the renderer (for testing).
        writer:           Override the writer (for testing).
    """
    from vault_builder.ports.source import ScriptureSource as _SS
    from vault_builder.domain.models import Book, BookIntro, ChapterNotes
    from typing import Iterator

    class _NullSource(_SS):
        def read_text(self) -> Iterator[Book]: return iter([])
        def read_notes(self) -> Iterator[ChapterNotes]: return iter([])
        def read_intros(self) -> Iterator[BookIntro]: return iter([])

    resolved_renderer = renderer or ObsidianRenderer()
    resolved_writer   = writer   or ObsidianWriter(output_root=output_dir)

    return ExtractionService(
        source=_NullSource(),
        renderer=resolved_renderer,
        writer=resolved_writer,
        mode=ExtractionMode.HUB,
        source_label=source_name,
        patristic_source=patristic_source,
    )


def bootstrap_parallels(
    *,
    output_dir: str = "output/Scripture",
    parallel_source: ParallelSource | None = None,
    renderer: VaultRenderer | None = None,
    writer: VaultWriter | None = None,
) -> ExtractionService:
    """
    Build an ExtractionService wired for parallel passage companion output only.

    The service has no ScriptureSource (text/notes pass is a no-op) but
    will call read_parallels() on the ParallelSource and emit Parallels companions.

    Args:
        output_dir:      Root directory for generated files.
        parallel_source: Override the ParallelSource (for testing).
        renderer:        Override the renderer (for testing).
        writer:          Override the writer (for testing).
    """
    from vault_builder.ports.source import ScriptureSource as _SS
    from vault_builder.domain.models import Book, BookIntro, ChapterNotes
    from typing import Iterator

    class _NullSource(_SS):
        def read_text(self) -> Iterator[Book]: return iter([])
        def read_notes(self) -> Iterator[ChapterNotes]: return iter([])
        def read_intros(self) -> Iterator[BookIntro]: return iter([])

    resolved_renderer = renderer or ObsidianRenderer()
    resolved_writer   = writer   or ObsidianWriter(output_root=output_dir)

    return ExtractionService(
        source=_NullSource(),
        renderer=resolved_renderer,
        writer=resolved_writer,
        mode=ExtractionMode.HUB,
        parallel_source=parallel_source,
    )


def bootstrap(
    source_name: str,
    *,
    output_dir: str = "output/Scripture",
    full_run: bool = False,
    source: ScriptureSource | None = None,
    renderer: VaultRenderer | None = None,
    writer: VaultWriter | None = None,
) -> ExtractionService:
    """
    Build an ExtractionService for the named source.

    Args:
        source_name: Short name from sources.yaml (e.g. "osb", "lexham").
        output_dir:  Root directory for generated files.
        full_run:    If True, extract all chapters; otherwise sample mode.
        source:      Override the source adapter (for testing).
        renderer:    Override the renderer (for testing).
        writer:      Override the writer (for testing).

    Any source override that also implements PatristicSource is wired into the
    Fathers companion pipeline automatically.
    """
    if source_name not in _SOURCE_CONFIG:
        raise ValueError(
            f"No bootstrap config for '{source_name}'. "
            f"Known sources: {sorted(_SOURCE_CONFIG)}"
        )

    adapter_spec, mode, label, sample_chapters = _SOURCE_CONFIG[source_name]

    resolved_source   = source   or _build_source(source_name, adapter_spec, full_run, sample_chapters)
    resolved_renderer = renderer or ObsidianRenderer()
    resolved_writer   = writer   or ObsidianWriter(output_root=output_dir)
    resolved_patristic_source = (
        resolved_source if isinstance(resolved_source, PatristicSource) else None
    )

    return ExtractionService(
        source=resolved_source,
        renderer=resolved_renderer,
        writer=resolved_writer,
        mode=mode,
        source_label=label,
        patristic_source=resolved_patristic_source,
    )
