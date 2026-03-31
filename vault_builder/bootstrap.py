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
from vault_builder.ports.renderer import VaultRenderer
from vault_builder.ports.source import ScriptureSource
from vault_builder.ports.writer import VaultWriter
from vault_builder.service_layer.extraction import ExtractionMode, ExtractionService

_SOURCES_YAML = "sources.yaml"

# Sample chapters per source — used when sample_only=True.
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
    ("Acts",             15),
    ("Romans",            8),
    ("I Corinthians",    13),
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
    ("John",           1),
    ("Acts",          15),
    ("Romans",         8),
    ("I Corinthians", 13),
    ("James",          1),
    ("Revelation",     1),
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
    ("John",           1),
    ("Acts",          15),
    ("Romans",         8),
    ("I Corinthians", 13),
    ("James",          1),
    ("Revelation",     1),
}

# Maps source short-name → (adapter class import path, ExtractionMode, label, sample_chapters)
_SOURCE_CONFIG: dict[str, tuple[str, ExtractionMode, str, set[tuple[str, int]]]] = {
    "osb":      ("vault_builder.adapters.sources.osb_epub:OsbEpubSource",     ExtractionMode.HUB,       "OSB",       _OSB_SAMPLE),
    "lexham":   ("vault_builder.adapters.sources.lexham_epub:LexhamEpubSource", ExtractionMode.COMPANION, "Lexham",    _LEXHAM_SAMPLE),
    "eob":      ("vault_builder.adapters.sources.eob_epub:EobEpubSource",      ExtractionMode.COMPANION, "EOB",       _EOB_SAMPLE),
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

    return ExtractionService(
        source=resolved_source,
        renderer=resolved_renderer,
        writer=resolved_writer,
        mode=mode,
        source_label=label,
    )
