"""
Tests for OSB patristic citation promotion into the Fathers layer.
"""

from __future__ import annotations

import os

import pytest
import yaml

from tests.fakes import FakeScriptureSource, FakeVaultWriter
from vault_builder.adapters.sources.osb_epub import (
    OsbEpubSource,
    _infer_osb_patristic_attribution,
)
from vault_builder.bootstrap import bootstrap
from vault_builder.domain.models import ChapterFathers, PatristicExcerpt, PatristicType
from vault_builder.ports.patristic_source import PatristicSource

_SOURCES_YAML = os.path.join(os.path.dirname(__file__), "..", "sources.yaml")


def _osb_epub_path() -> str:
    with open(_SOURCES_YAML) as f:
        return yaml.safe_load(f)["sources"]["osb"]["path"]


_osb_present = pytest.mark.skipif(
    not os.path.exists(_osb_epub_path()),
    reason="OSB EPUB not present on disk",
)


def test_osb_patristic_attribution_helper_parses_known_markers():
    assert _infer_osb_patristic_attribution(
        "St. John Chrysostom teaches that not only the saints, but all people have guardian angels.",
        "Matthew",
    ) == ("John Chrysostom", "Homilies on Matthew")

    assert _infer_osb_patristic_attribution(
        "Theophylact sees John's comment as a regret (Theoph).",
        "Luke",
    ) == ("Theophylact of Ohrid", "Commentary on Luke")

    assert _infer_osb_patristic_attribution(
        "Where the Church is, there is the Holy Spirit and the fullness of grace (Iren).",
        "John",
    ) == ("Irenaeus of Lyons", "Against Heresies")


@_osb_present
def test_real_epub_promotes_patristic_citations_to_fathers():
    src = OsbEpubSource(
        _osb_epub_path(),
        sample_only=True,
        sample_chapters={
            ("Matthew", 18),
            ("Luke", 9),
            ("Luke", 18),
            ("John", 14),
        },
    )
    fathers = { (f.book, f.chapter): f for f in src.read_fathers() }

    assert set(fathers) == {
        ("Matthew", 18),
        ("Luke", 9),
        ("Luke", 18),
        ("John", 14),
    }

    mat18 = fathers[("Matthew", 18)]
    assert mat18.source == "OSB Citations"
    assert any(
        exc.father == "John Chrysostom" and exc.work == "Homilies on Matthew"
        for _ptype, exc in mat18.sorted_excerpts()
    )

    luke9 = fathers[("Luke", 9)]
    assert any(
        exc.father == "Theophylact of Ohrid" and exc.work == "Commentary on Luke"
        for _ptype, exc in luke9.sorted_excerpts()
    )

    john14 = fathers[("John", 14)]
    assert any(
        exc.father == "Irenaeus of Lyons" and exc.work == "Against Heresies"
        for _ptype, exc in john14.sorted_excerpts()
    )


@_osb_present
def test_real_epub_citations_become_brief_fathers_references_in_notes():
    src = OsbEpubSource(
        _osb_epub_path(),
        sample_only=True,
        sample_chapters={("John", 14)},
    )
    john14 = next(
        (n for n in src.read_notes() if n.book == "John" and n.chapter == 14),
        None,
    )
    assert john14 is not None
    note = next(note for note in john14.citations if note.ref_str == "14:26")
    assert note.content.startswith("**Helper**: See note at [[John 14#v16|14:16]].")
    assert "Where the Church is, there is the Holy Spirit and the fullness of grace" in note.content
    assert note.content.strip().endswith("See [[John 14 — Fathers#v26|Fathers]]")


class _CombinedOsbFakeSource(FakeScriptureSource, PatristicSource):
    """Minimal fake that exercises bootstrap() auto-wiring for PatristicSource."""

    def __init__(self, fathers: list[ChapterFathers] | None = None) -> None:
        super().__init__()
        self._fathers = fathers or []

    def read_fathers(self):
        return iter(self._fathers)


def test_bootstrap_wires_osb_source_into_fathers_pipeline():
    fathers = ChapterFathers(book="John", chapter=1, source="OSB Citations")
    fathers.add_excerpt(
        PatristicType.COMMENTARY,
        PatristicExcerpt(
            father="John Chrysostom",
            work="Homilies on John",
            content="The Word is God.",
            verse_start=1,
        ),
    )

    writer = FakeVaultWriter()
    svc = bootstrap(
        "osb",
        source=_CombinedOsbFakeSource(fathers=[fathers]),
        writer=writer,
    )

    result = svc.extract()

    assert result.fathers_written == 1
    assert ("John", 1) in writer.written_fathers
    assert "John Chrysostom" in writer.written_fathers[("John", 1)]
