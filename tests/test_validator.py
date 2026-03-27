"""
Fixture-based regression tests for validate_output.py.

The fixture tree at tests/fixtures/Scripture/ contains representative chapters
spanning Torah, Psalter, prophecy, Deuterocanon, Gospel, epistle, and apocalypse,
plus EOB text companion fixtures for the Phase 1 EOB NT fixture matrix.
The validator must report 0 errors against this tree.

Rule-specific unit tests use synthetic files in tmp_path to verify that each
error code fires correctly on invalid input.
"""

import textwrap
from pathlib import Path

import pytest

from validate_output import (
    Finding,
    collect_files,
    validate_companion,
    validate_hub,
)
from vault_builder.domain.canon import book_file_prefix

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "Scripture"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == "ERROR"]


def _codes(findings: list[Finding]) -> list[str]:
    return [f.code for f in findings]


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def _hub(tmp: Path, book: str, chapter: int, fm_extra: str = "", body: str = "") -> Path:
    top = "02 - New Testament" if book in ("John", "Romans", "Revelation") else "01 - Old Testament"
    orders = {"Genesis": 1, "Psalms": 24, "Isaiah": 31, "John": 4, "Romans": 6, "Revelation": 27}
    order = orders.get(book, 1)
    path = tmp / top / f"{order:02d} - {book}" / f"{book} {chapter}.md"
    testament = "NT" if top == "02 - New Testament" else "OT"
    genre = "Gospel" if book == "John" else "Epistle" if book == "Romans" else "Prose"
    book_id = book[:3].upper()
    default_body = (
        '###### v1\n<span class="vn">1</span> Verse one text. ^v1\n\n'
        '###### v2\n<span class="vn">2</span> Verse two text. ^v2\n'
    )
    content = f"""\
        ---
        testament: "{testament}"
        genre: "{genre}"
        book_id: "{book_id}"
        aliases: ["{book_id} {chapter}"]
        up: "[[{book}]]"
        prev: ""
        next: "[[{book} {chapter + 1}]]"
        {fm_extra}
        ---
        {body or default_body}
    """
    return _write(path, content)


def _companion(tmp: Path, book: str, chapter: int, source: str = "OSB") -> Path:
    top = "02 - New Testament" if book in ("John", "Romans") else "01 - Old Testament"
    orders = {"Genesis": 1, "John": 4, "Romans": 6}
    order = orders.get(book, 1)
    suffix = "Notes" if source in ("OSB", "NET") else source
    name = f"{book} {chapter} \u2014 {suffix}.md" if source in ("OSB", "NET") else f"{book} {chapter} \u2014 {source}.md"
    path = tmp / top / f"{order:02d} - {book}" / name
    content = f"""\
        ---
        hub: "[[{book} {chapter}]]"
        source: "{source}"
        ---

        ### [[{book} {chapter}#v1|{chapter}:1]]
        Some note content.
    """
    return _write(path, content)


# ── Fixture tree: 0 errors ────────────────────────────────────────────────────


def test_fixture_tree_passes_validator():
    """Full validator sweep of the fixture tree must produce 0 errors."""
    hub_paths, cmp_paths, text_cmp_paths = collect_files(FIXTURE_ROOT)
    assert hub_paths, "No hub files found in fixture tree"

    errors: list[Finding] = []
    for hub in hub_paths:
        findings, _ = validate_hub(hub, FIXTURE_ROOT)
        errors.extend(_errors(findings))
    for cmp in cmp_paths + text_cmp_paths:
        findings = validate_companion(cmp, FIXTURE_ROOT)
        errors.extend(_errors(findings))

    assert errors == [], (
        "Validator errors in fixture tree:\n"
        + "\n".join(f"  {e.code} {e.path}:{e.line} — {e.message}" for e in errors)
    )


@pytest.mark.parametrize(
    "book, chapter, min_verses",
    [
        ("Genesis", 1, 31),
        ("Psalms", 1, 6),
        ("Isaiah", 53, 12),
        ("Sirach", 1, 27),
        ("I Maccabees", 1, 64),
        ("John", 1, 51),
        ("Romans", 8, 39),
        ("Revelation", 1, 20),
    ],
)
def test_hub_verse_count(book: str, chapter: int, min_verses: int) -> None:
    """Each fixture hub must contain at least the expected verse count."""
    from vault_builder.domain.canon import BOOK_FOLDER

    top_folder, order = BOOK_FOLDER[book]
    path = FIXTURE_ROOT / top_folder / f"{order:02d} - {book}" / f"{book_file_prefix(book)} {chapter}.md"
    assert path.exists(), f"Fixture hub missing: {path.relative_to(FIXTURE_ROOT)}"
    _, verse_count = validate_hub(path, FIXTURE_ROOT)
    assert verse_count >= min_verses, (
        f"{book} {chapter}: expected >= {min_verses} verses, got {verse_count}"
    )


@pytest.mark.parametrize(
    "book, chapter, source, min_verses",
    [
        ("Matthew", 1, "EOB", 25),
        ("John", 1, "EOB", 51),
        ("Romans", 8, "EOB", 39),
        ("James", 1, "EOB", 27),
    ],
)
def test_eob_companion_verse_count(book: str, chapter: int, source: str, min_verses: int) -> None:
    """Each EOB text companion fixture must contain at least the expected verse count."""
    from vault_builder.domain.canon import BOOK_FOLDER

    top_folder, order = BOOK_FOLDER[book]
    path = FIXTURE_ROOT / top_folder / f"{order:02d} - {book}" / f"{book} {chapter} \u2014 {source}.md"
    assert path.exists(), f"EOB fixture companion missing: {path.relative_to(FIXTURE_ROOT)}"
    count = sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("###### v"))
    assert count >= min_verses, (
        f"{book} {chapter} — {source}: expected >= {min_verses} verse anchors, got {count}"
    )


@pytest.mark.parametrize(
    "book, chapter",
    [
        ("John", 1),
        ("Romans", 8),
        ("Psalms", 1),
        ("Acts", 15),
    ],
)
def test_net_notes_contain_typed_callouts(book: str, chapter: int) -> None:
    """Each NET Notes fixture must contain at least one typed callout (tn, sn, tc, or map)."""
    from vault_builder.domain.canon import BOOK_FOLDER

    top_folder, order = BOOK_FOLDER[book]
    path = FIXTURE_ROOT / top_folder / f"{order:02d} - {book}" / f"{book_file_prefix(book)} {chapter} \u2014 NET Notes.md"
    assert path.exists(), f"NET Notes fixture missing: {path.relative_to(FIXTURE_ROOT)}"
    text = path.read_text(encoding="utf-8")
    typed = [ln for ln in text.splitlines() if ln.startswith("> [!tn]") or ln.startswith("> [!sn]")
             or ln.startswith("> [!tc]") or ln.startswith("> [!map]")]
    assert typed, f"{book} {chapter} — NET Notes: no typed callouts (tn/sn/tc/map) found"


@pytest.mark.parametrize(
    "book, chapter, min_notes",
    [
        ("John", 1, 5),
    ],
)
def test_eob_notes_companion_has_verse_notes(book: str, chapter: int, min_notes: int) -> None:
    """EOB Notes fixture must contain verse-heading entries with note content."""
    from vault_builder.domain.canon import BOOK_FOLDER

    top_folder, order = BOOK_FOLDER[book]
    path = FIXTURE_ROOT / top_folder / f"{order:02d} - {book}" / f"{book} {chapter} \u2014 EOB Notes.md"
    assert path.exists(), f"EOB Notes fixture missing: {path.relative_to(FIXTURE_ROOT)}"
    text = path.read_text(encoding="utf-8")
    headings = [ln for ln in text.splitlines() if ln.startswith("### [[")]
    assert len(headings) >= min_notes, (
        f"{book} {chapter} — EOB Notes: expected >= {min_notes} verse note headings, got {len(headings)}"
    )


# ── HUB rule unit tests ───────────────────────────────────────────────────────


def test_HUB001_missing_frontmatter(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1.md",
        "No frontmatter here\n###### v1\ntext ^v1\n",
    )
    findings, _ = validate_hub(path, tmp_path)
    assert "HUB001" in _codes(findings)


def test_HUB001_missing_required_field(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1.md",
        '---\ntestament: "NT"\n---\n###### v1\n<span class="vn">1</span> text ^v1\n',
    )
    findings, _ = validate_hub(path, tmp_path)
    assert "HUB001" in _codes(findings)


def test_HUB002_bad_testament_value(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1.md",
        textwrap.dedent("""\
            ---
            testament: "INVALID"
            genre: "Gospel"
            book_id: "Jn"
            aliases: ["Jn 1"]
            up: "[[John]]"
            prev: ""
            next: "[[John 2]]"
            ---
            ###### v1
            <span class="vn">1</span> text ^v1
        """),
    )
    findings, _ = validate_hub(path, tmp_path)
    assert "HUB002" in _codes(findings)


def test_HUB004_ot_book_in_nt_folder(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "01 - Genesis" / "Genesis 1.md",
        textwrap.dedent("""\
            ---
            testament: "OT"
            genre: "Torah"
            book_id: "Gen"
            aliases: ["Gen 1"]
            up: "[[Genesis]]"
            prev: ""
            next: "[[Genesis 2]]"
            ---
            ###### v1
            <span class="vn">1</span> text ^v1
        """),
    )
    findings, _ = validate_hub(path, tmp_path)
    assert "HUB004" in _codes(findings)


def test_HUB007_verse_anchor_gap(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1.md",
        textwrap.dedent("""\
            ---
            testament: "NT"
            genre: "Gospel"
            book_id: "Jn"
            aliases: ["Jn 1"]
            up: "[[John]]"
            prev: ""
            next: "[[John 2]]"
            ---
            ###### v1
            <span class="vn">1</span> text ^v1

            ###### v3
            <span class="vn">3</span> text ^v3
        """),
    )
    findings, _ = validate_hub(path, tmp_path)
    assert "HUB007" in _codes(findings)


def test_HUB007_verse_anchor_does_not_start_at_1(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1.md",
        textwrap.dedent("""\
            ---
            testament: "NT"
            genre: "Gospel"
            book_id: "Jn"
            aliases: ["Jn 1"]
            up: "[[John]]"
            prev: ""
            next: "[[John 2]]"
            ---
            ###### v2
            <span class="vn">2</span> text ^v2
        """),
    )
    findings, _ = validate_hub(path, tmp_path)
    assert "HUB007" in _codes(findings)


def test_HUB009_chapter1_nonempty_prev(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1.md",
        textwrap.dedent("""\
            ---
            testament: "NT"
            genre: "Gospel"
            book_id: "Jn"
            aliases: ["Jn 1"]
            up: "[[John]]"
            prev: "[[John 0]]"
            next: "[[John 2]]"
            ---
            ###### v1
            <span class="vn">1</span> text ^v1
        """),
    )
    findings, _ = validate_hub(path, tmp_path)
    assert "HUB009" in _codes(findings)


# ── CMP rule unit tests ───────────────────────────────────────────────────────


def test_CMP001_missing_hub_field(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1 \u2014 OSB Notes.md",
        '---\nsource: "OSB"\n---\n### [[John 1#v1|1:1]]\ntext\n',
    )
    findings = validate_companion(path, tmp_path)
    assert "CMP001" in _codes(findings)


def test_CMP002_hub_not_found(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1 \u2014 OSB Notes.md",
        textwrap.dedent("""\
            ---
            hub: "[[John 1]]"
            source: "OSB"
            ---
            ### [[John 1#v1|1:1]]
            text
        """),
    )
    findings = validate_companion(path, tmp_path)
    assert "CMP002" in _codes(findings)


def test_CMP002_absent_when_hub_exists(tmp_path: Path) -> None:
    _hub(tmp_path, "John", 1)
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1 \u2014 OSB Notes.md",
        textwrap.dedent("""\
            ---
            hub: "[[John 1]]"
            source: "OSB"
            ---
            ### [[John 1#v1|1:1]]
            text
        """),
    )
    findings = validate_companion(path, tmp_path)
    assert "CMP002" not in _codes(findings)


def test_CMP008_out_of_order_notes(tmp_path: Path) -> None:
    _hub(tmp_path, "John", 1)
    path = _write(
        tmp_path / "02 - New Testament" / "04 - John" / "John 1 \u2014 OSB Notes.md",
        textwrap.dedent("""\
            ---
            hub: "[[John 1]]"
            source: "OSB"
            ---
            ### [[John 1#v2|1:2]]
            note for verse 2

            ### [[John 1#v1|1:1]]
            note for verse 1 — out of order
        """),
    )
    findings = validate_companion(path, tmp_path)
    assert "CMP008" in _codes(findings)
