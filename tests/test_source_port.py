"""Tests for vault_builder.ports.source — Phase 2 port interface update."""

from typing import Iterator

from vault_builder.domain.models import Book, BookIntro, ChapterNotes
from vault_builder.ports.source import ScriptureSource


# ── Minimal concrete subclass for testing ────────────────────────────────────

class _MinimalSource(ScriptureSource):
    def read_text(self) -> Iterator[Book]:
        return iter([])

    def read_notes(self) -> Iterator[ChapterNotes]:
        return iter([])


class _IntroSource(ScriptureSource):
    """Adapter that overrides read_intros."""
    def read_text(self) -> Iterator[Book]:
        return iter([])

    def read_notes(self) -> Iterator[ChapterNotes]:
        return iter([])

    def read_intros(self) -> Iterator[BookIntro]:
        yield BookIntro(book="Genesis", source="TestSource", content="# Genesis\n\nIntro.")
        yield BookIntro(book="John", source="TestSource", content="# John\n\nIntro.")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_default_read_intros_returns_empty_iterator():
    source = _MinimalSource()
    result = list(source.read_intros())
    assert result == []


def test_default_read_intros_is_iterable():
    source = _MinimalSource()
    it = source.read_intros()
    assert hasattr(it, '__iter__')
    assert hasattr(it, '__next__')


def test_adapter_can_override_read_intros():
    source = _IntroSource()
    intros = list(source.read_intros())
    assert len(intros) == 2
    assert intros[0].book == "Genesis"
    assert intros[1].book == "John"


def test_overriding_read_intros_yields_book_intro_objects():
    source = _IntroSource()
    for intro in source.read_intros():
        assert isinstance(intro, BookIntro)


def test_minimal_source_still_satisfies_abstract_contract():
    source = _MinimalSource()
    assert list(source.read_text()) == []
    assert list(source.read_notes()) == []
    assert list(source.read_intros()) == []
