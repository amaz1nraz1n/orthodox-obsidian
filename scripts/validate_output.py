#!/usr/bin/env python3
"""Generated-Markdown validator for the Orthodox Obsidian vault."""

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml

from vault_builder.domain.canon import (
    BOOK_FOLDER, BOOK_CHAPTER_COUNT, BOOK_TESTAMENT,
    book_file_prefix, canonical_book_name,
)

SCRIPTURE_ROOT_DEFAULT = Path(__file__).parent / "Scripture"

VALID_TESTAMENTS = {"OT", "NT", "Deuterocanon"}

HUB_REQUIRED_FIELDS = ["testament", "genre", "book_id", "aliases", "up", "prev", "next"]
CMP_REQUIRED_FIELDS = ["hub", "source"]

RE_HUB_FILENAME = re.compile(r"^(.+?) (\d+)\.md$")
RE_CMP_FILENAME = re.compile(r"^(.+?) (\d+) \u2014 (.+?) Notes\.md$")
RE_TEXT_CMP_FILENAME = re.compile(r"^(.+?) (\d+) \u2014 (.+?)\.md$")
RE_H6_ANCHOR = re.compile(r"^###### (.+)$")
RE_VERSE_ANCHOR = re.compile(r"^###### v(\d+)$")
RE_VERSE_BODY = re.compile(r'^<span class="vn">(\d+)</span> .+ \^v(\d+)$')
RE_BLOCK_ID = re.compile(r'\^v(\d+)\s*$')
RE_WIKILINK = re.compile(r'\[\[([^\]]*)\]\]')
RE_ANCHOR_LINK = re.compile(r'\[\[([^#\]]+)#v(\d+)\|([^\]]*)\]\]')
RE_NOTE_HEADING = re.compile(r'^### \[\[.+?#v(\d+)\|.+?\]\]')
RE_RANGE_DISPLAY = re.compile(r'\[\[.+?#v(\d+)\|[^:]+:(\d+)-(\d+)\]\]')
RE_FOLDER_NUM = re.compile(r'^(\d+) - .+$')


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    line: Optional[int]
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    suggestion: Optional[str] = None


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root.parent))
    except ValueError:
        return str(path)


def _parse_frontmatter(text: str) -> tuple[Optional[dict], str, int]:
    """Return (fm_dict, body, body_start_line). body_start_line is 1-based."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, 1
    end = None
    for i, ln in enumerate(lines[1:], start=1):
        if ln.strip() == "---":
            end = i
            break
    if end is None:
        return None, text, 1
    fm_text = "\n".join(lines[1:end])
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    body = "\n".join(lines[end + 1:])
    return fm, body, end + 2


def _book_from_hub_path(path: Path) -> Optional[str]:
    m = RE_HUB_FILENAME.match(path.name)
    if not m:
        return None
    return canonical_book_name(m.group(1))


def _chapter_from_hub_path(path: Path) -> Optional[int]:
    m = RE_HUB_FILENAME.match(path.name)
    if not m:
        return None
    return int(m.group(2))


def _book_from_cmp_path(path: Path) -> Optional[str]:
    m = RE_CMP_FILENAME.match(path.name)
    if not m:
        return None
    return canonical_book_name(m.group(1))


def _chapter_from_cmp_path(path: Path) -> Optional[int]:
    m = RE_CMP_FILENAME.match(path.name)
    if not m:
        return None
    return int(m.group(2))


def _folder_order(path: Path, scripture_root: Path) -> Optional[int]:
    try:
        rel = path.relative_to(scripture_root)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2:
        return None
    m = RE_FOLDER_NUM.match(parts[1])
    if not m:
        return None
    return int(m.group(1))


def validate_hub(path: Path, scripture_root: Path) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    rel = _rel(path, scripture_root)
    text = path.read_text(encoding="utf-8")
    fm, body, body_start = _parse_frontmatter(text)

    book = _book_from_hub_path(path)
    chapter = _chapter_from_hub_path(path)

    if fm is None:
        findings.append(Finding("ERROR", "HUB001", rel, 1, "Missing or unparseable frontmatter"))
        return findings, 0

    missing = [f for f in HUB_REQUIRED_FIELDS if f not in fm]
    if missing:
        findings.append(Finding(
            "ERROR", "HUB001", rel, 1,
            f"Missing required frontmatter fields: {', '.join(missing)}",
            expected=", ".join(HUB_REQUIRED_FIELDS),
        ))

    if "aliases" in fm and not isinstance(fm["aliases"], list):
        findings.append(Finding(
            "ERROR", "HUB002", rel, 1,
            "'aliases' must be a YAML list",
            expected="list", actual=type(fm["aliases"]).__name__,
        ))
    if "testament" in fm and fm["testament"] not in VALID_TESTAMENTS:
        findings.append(Finding(
            "ERROR", "HUB002", rel, 1,
            f"'testament' value '{fm['testament']}' not in {VALID_TESTAMENTS}",
            expected=str(VALID_TESTAMENTS), actual=str(fm["testament"]),
        ))

    if book and book != "Psalms":
        for ref_field in ("mt_ref", "lxx_ref"):
            if ref_field in fm:
                findings.append(Finding(
                    "ERROR", "HUB003", rel, 1,
                    f"'{ref_field}' may only appear on Psalms hubs",
                    suggestion="Remove this field or restrict it to Psalms chapters",
                ))

    if book and book in BOOK_FOLDER:
        top_folder, canonical_order = BOOK_FOLDER[book]
        testament_val = fm.get("testament", "")

        try:
            rel_parts = path.relative_to(scripture_root).parts
            actual_top = rel_parts[0] if rel_parts else ""
        except ValueError:
            actual_top = ""

        if testament_val in ("OT", "Deuterocanon"):
            if actual_top != "01 - Old Testament":
                findings.append(Finding(
                    "ERROR", "HUB004", rel, None,
                    f"OT/Deuterocanon book must be under '01 - Old Testament/', found under '{actual_top}'",
                    expected="01 - Old Testament", actual=actual_top,
                    suggestion="Move file to 01 - Old Testament/",
                ))
        elif testament_val == "NT":
            if actual_top != "02 - New Testament":
                findings.append(Finding(
                    "ERROR", "HUB004", rel, None,
                    f"NT book must be under '02 - New Testament/', found under '{actual_top}'",
                    expected="02 - New Testament", actual=actual_top,
                ))

        actual_order = _folder_order(path, scripture_root)
        if actual_order is not None and actual_order != canonical_order:
            findings.append(Finding(
                "ERROR", "HUB005", rel, None,
                f"Folder order {actual_order:02d} does not match canonical order {canonical_order:02d} for '{book}'",
                expected=f"{canonical_order:02d}", actual=f"{actual_order:02d}",
            ))

    body_lines = body.splitlines()
    verse_anchors: list[tuple[int, int]] = []
    h6_issues: list[tuple[int, str]] = []

    for i, ln in enumerate(body_lines, start=body_start):
        m = RE_H6_ANCHOR.match(ln)
        if m:
            heading_text = m.group(1)
            vm = re.match(r'^v(\d+)$', heading_text)
            if not vm:
                h6_issues.append((i, heading_text))
            else:
                verse_anchors.append((i, int(vm.group(1))))

    for line_no, heading_text in h6_issues:
        findings.append(Finding(
            "ERROR", "HUB006", rel, line_no,
            f"Malformed H6 heading: '###### {heading_text}' — expected '###### vN'",
        ))

    if verse_anchors:
        nums = [v for _, v in verse_anchors]
        if nums[0] != 1:
            findings.append(Finding(
                "WARN", "HUB007", rel, verse_anchors[0][0],
                f"Verse anchors do not start at 1 (first is v{nums[0]})",
                expected="v1", actual=f"v{nums[0]}",
            ))
        for i in range(1, len(nums)):
            if nums[i] != nums[i - 1] + 1:
                findings.append(Finding(
                    "WARN", "HUB007", rel, verse_anchors[i][0],
                    f"Verse anchor gap: v{nums[i - 1]} followed by v{nums[i]}",
                    expected=f"v{nums[i - 1] + 1}", actual=f"v{nums[i]}",
                ))

    anchor_line_map: dict[int, int] = {v: ln for ln, v in verse_anchors}

    for anchor_line, verse_num in verse_anchors:
        body_idx = anchor_line - body_start
        next_idx = body_idx + 1
        body_line = body_lines[next_idx].strip() if next_idx < len(body_lines) else ""

        if not body_line:
            findings.append(Finding(
                "ERROR", "HUB008", rel, anchor_line + 1,
                f"Verse anchor v{verse_num} has no body content on the following line",
            ))
            continue

        vm = RE_VERSE_BODY.match(body_line)
        if not vm:
            findings.append(Finding(
                "ERROR", "HUB011", rel, anchor_line + 1,
                f"Verse body for v{verse_num} does not match inline-vn pattern",
                expected='<span class="vn">N</span> text ^vN',
                actual=body_line[:80],
                suggestion="Ensure renderer emits inline span+block-id format",
            ))
        else:
            span_num = int(vm.group(1))
            block_id_num = int(vm.group(2))
            if block_id_num != verse_num:
                findings.append(Finding(
                    "ERROR", "HUB012", rel, anchor_line + 1,
                    f"Block ID ^v{block_id_num} does not match anchor v{verse_num}",
                    expected=f"^v{verse_num}", actual=f"^v{block_id_num}",
                ))

    if book and "testament" in fm:
        expected_testament = BOOK_TESTAMENT.get(book)
        if expected_testament and fm["testament"] != expected_testament:
            findings.append(Finding(
                "ERROR", "HUB010", rel, 1,
                f"'testament' value '{fm['testament']}' does not match canon ({expected_testament}) for '{book}'",
                expected=expected_testament, actual=fm["testament"],
            ))

    if chapter is not None and book in BOOK_CHAPTER_COUNT:
        max_ch = BOOK_CHAPTER_COUNT[book]
        prev_val = fm.get("prev", "")
        next_val = fm.get("next", "")
        if chapter == 1 and prev_val not in ("", None):
            findings.append(Finding(
                "WARN", "HUB009", rel, 1,
                f"Chapter 1 should have empty 'prev', found '{prev_val}'",
                expected="", actual=str(prev_val),
            ))
        if chapter == max_ch and next_val not in ("", None):
            findings.append(Finding(
                "WARN", "HUB009", rel, 1,
                f"Last chapter ({max_ch}) should have empty 'next', found '{next_val}'",
                expected="", actual=str(next_val),
            ))

    total_verses = len(verse_anchors)
    return findings, total_verses


def _hub_verse_set(hub_path: Path) -> set[int]:
    if not hub_path.exists():
        return set()
    text = hub_path.read_text(encoding="utf-8")
    _, body, _ = _parse_frontmatter(text)
    result = set()
    for ln in body.splitlines():
        m = RE_VERSE_ANCHOR.match(ln)
        if m:
            result.add(int(m.group(1)))
    return result


def _resolve_hub_path(hub_field: str, scripture_root: Path) -> Optional[Path]:
    m = re.match(r'^\[\[(.+?)\]\]$', hub_field.strip())
    if not m:
        return None
    link_target = m.group(1)
    book_ch = link_target.strip()
    bm = re.match(r'^(.+?) (\d+)$', book_ch)
    if not bm:
        return None
    book = canonical_book_name(bm.group(1))
    chapter = int(bm.group(2))
    if book not in BOOK_FOLDER:
        return None
    top_folder, order = BOOK_FOLDER[book]
    pfx = book_file_prefix(book)
    return scripture_root / top_folder / f"{order:02d} - {book}" / f"{pfx} {chapter}.md"


def validate_companion(path: Path, scripture_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    rel = _rel(path, scripture_root)
    text = path.read_text(encoding="utf-8")
    fm, body, body_start = _parse_frontmatter(text)

    if fm is None:
        findings.append(Finding("ERROR", "CMP001", rel, 1, "Missing or unparseable frontmatter"))
        return findings

    missing = [f for f in CMP_REQUIRED_FIELDS if f not in fm]
    if missing:
        findings.append(Finding(
            "ERROR", "CMP001", rel, 1,
            f"Missing required companion frontmatter fields: {', '.join(missing)}",
        ))

    hub_path: Optional[Path] = None
    hub_verses: set[int] = set()

    if "hub" in fm:
        hub_path = _resolve_hub_path(str(fm["hub"]), scripture_root)
        if hub_path is None or not hub_path.exists():
            findings.append(Finding(
                "WARN", "CMP002", rel, 1,
                f"Hub file not found for hub='{fm['hub']}'",
                suggestion="Check hub frontmatter matches an existing chapter hub",
            ))
        else:
            hub_verses = _hub_verse_set(hub_path)

    body_lines = body.splitlines()
    note_verse_nums: list[tuple[int, int]] = []
    seen_headings: dict[str, int] = {}

    for i, ln in enumerate(body_lines, start=body_start):
        m_note = RE_NOTE_HEADING.match(ln)
        if m_note:
            verse_num = int(m_note.group(1))
            note_verse_nums.append((i, verse_num))

            if hub_verses and verse_num not in hub_verses:
                findings.append(Finding(
                    "WARN", "CMP005", rel, i,
                    f"Note heading references v{verse_num} which does not exist in hub (max={max(hub_verses) if hub_verses else '?'})",
                    suggestion="Check for cross-chapter range collapse",
                ))

        heading_stripped = ln.strip()
        if heading_stripped.startswith("### ") or heading_stripped.startswith("## "):
            if heading_stripped in seen_headings:
                findings.append(Finding(
                    "WARN", "CMP006", rel, i,
                    f"Duplicate heading: '{heading_stripped[:60]}'",
                    expected="unique headings",
                ))
            else:
                seen_headings[heading_stripped] = i

        for m_range in RE_RANGE_DISPLAY.finditer(ln):
            anchor_v = int(m_range.group(1))
            range_start = int(m_range.group(2))
            range_end = int(m_range.group(3))
            if range_end < range_start:
                findings.append(Finding(
                    "WARN", "CMP004", rel, i,
                    f"Malformed range display: anchor v{anchor_v}, range {range_start}-{range_end} (end < start)",
                    suggestion="Likely a cross-chapter range collapsed into same-chapter display",
                ))

        for m_wl in RE_WIKILINK.finditer(ln):
            target = m_wl.group(1)
            if not target or not target.strip():
                findings.append(Finding(
                    "WARN", "CMP007", rel, i,
                    "Empty wikilink target [[]]",
                ))
                continue
            if target.strip().startswith("|") or "||" in target:
                findings.append(Finding(
                    "WARN", "CMP007", rel, i,
                    f"Malformed wikilink: '[[{target}]]'",
                ))
                continue
            anchor_m = re.match(r'^.+?#v(\d+)', target)
            if anchor_m and hub_verses:
                anchor_v = int(anchor_m.group(1))
                link_book_ch = target.split("#")[0].strip()
                bm = re.match(r'^(.+?) (\d+)$', link_book_ch)
                if bm:
                    link_book = bm.group(1)
                    link_ch = int(bm.group(2))
                    if hub_path and hub_path.exists():
                        hub_book = _book_from_hub_path(hub_path)
                        hub_ch = _chapter_from_hub_path(hub_path)
                        if link_book == hub_book and link_ch == hub_ch:
                            if anchor_v not in hub_verses:
                                findings.append(Finding(
                                    "WARN", "CMP003", rel, i,
                                    f"Anchor [[{link_book_ch}#v{anchor_v}|...]] not found in hub",
                                    suggestion=f"v{anchor_v} does not exist in {hub_path.name}",
                                ))

    if note_verse_nums:
        nums = [v for _, v in note_verse_nums]
        for idx in range(1, len(nums)):
            if nums[idx] < nums[idx - 1]:
                findings.append(Finding(
                    "ERROR", "CMP008", rel, note_verse_nums[idx][0],
                    f"Note heading v{nums[idx]} appears after v{nums[idx - 1]} — out of order",
                    expected=f">= v{nums[idx - 1]}", actual=f"v{nums[idx]}",
                    suggestion="Render companion entries in verse/pericope order",
                ))

    return findings


def check_run_coverage(
    hub_paths: list[Path],
    cmp_paths: list[Path],
    scripture_root: Path,
) -> list[Finding]:
    findings: list[Finding] = []
    hub_set = {p.parent / p.stem for p in hub_paths}
    cmp_books_chapters: set[tuple[str, int]] = set()

    for p in cmp_paths:
        book = _book_from_cmp_path(p)
        ch = _chapter_from_cmp_path(p)
        if book and ch:
            cmp_books_chapters.add((book, ch))

    for hub in hub_paths:
        book = _book_from_hub_path(hub)
        ch = _chapter_from_hub_path(hub)
        if book and ch and (book, ch) not in cmp_books_chapters:
            findings.append(Finding(
                "WARN", "RUN001", _rel(hub, scripture_root), None,
                f"No companion file found for hub '{hub.name}'",
                suggestion="Run extraction to generate companion notes",
            ))

    return findings


def check_canon_completeness(
    hub_paths: list[Path],
    cmp_paths: list[Path],
    scripture_root: Path,
) -> list[Finding]:
    """Cross-check generated files against BOOK_CHAPTER_COUNT. Reports missing hubs and companions."""
    findings: list[Finding] = []

    generated_hubs: set[tuple[str, int]] = set()
    for p in hub_paths:
        book = _book_from_hub_path(p)
        ch = _chapter_from_hub_path(p)
        if book and ch:
            generated_hubs.add((book, ch))

    generated_cmps: set[tuple[str, int]] = set()
    for p in cmp_paths:
        book = _book_from_cmp_path(p)
        ch = _chapter_from_cmp_path(p)
        if book and ch:
            generated_cmps.add((book, ch))

    for book, chapter_count in sorted(BOOK_CHAPTER_COUNT.items()):
        for ch in range(1, chapter_count + 1):
            if (book, ch) not in generated_hubs:
                findings.append(Finding(
                    "ERROR", "RUN002",
                    f"{book}/{book} {ch}.md",
                    None,
                    f"Missing hub: {book} {ch} not found in Scripture tree",
                    expected=f"{book} {ch}.md",
                    suggestion="Run extract_osb.py --full to generate all chapters",
                ))
            elif (book, ch) not in generated_cmps:
                findings.append(Finding(
                    "WARN", "RUN003",
                    f"{book}/{book} {ch}.md",
                    None,
                    f"Missing OSB Notes companion for {book} {ch}",
                    expected=f"{book} {ch} \u2014 OSB Notes.md",
                    suggestion="OSB may have no study notes for this chapter",
                ))

    return findings


def collect_files(scripture_root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    hub_paths = []
    cmp_paths = []
    text_cmp_paths = []
    for p in scripture_root.rglob("*.md"):
        if RE_CMP_FILENAME.match(p.name):
            cmp_paths.append(p)
        elif RE_TEXT_CMP_FILENAME.match(p.name):
            text_cmp_paths.append(p)
        elif RE_HUB_FILENAME.match(p.name):
            hub_paths.append(p)
    return sorted(hub_paths), sorted(cmp_paths), sorted(text_cmp_paths)


def format_finding(f: Finding) -> str:
    loc = f":{f.line}" if f.line else ""
    parts = [f"  [{f.severity}] {f.code} {f.path}{loc}"]
    parts.append(f"    {f.message}")
    if f.expected:
        parts.append(f"    expected: {f.expected}")
    if f.actual:
        parts.append(f"    actual:   {f.actual}")
    if f.suggestion:
        parts.append(f"    hint:     {f.suggestion}")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    full_osb = "--full-osb" in args
    args = [a for a in args if a != "--full-osb"]
    scripture_root = Path(args[0]) if args else SCRIPTURE_ROOT_DEFAULT
    scripture_root = scripture_root.resolve()

    if not scripture_root.exists():
        print(f"ERROR: Scripture root not found: {scripture_root}", file=sys.stderr)
        return 1

    hub_paths, cmp_paths, text_cmp_paths = collect_files(scripture_root)

    all_findings: list[Finding] = []
    total_verses = 0

    findings_by_file: dict[str, list[Finding]] = {}

    for hub in hub_paths:
        rel = _rel(hub, scripture_root)
        hub_findings, verse_count = validate_hub(hub, scripture_root)
        total_verses += verse_count
        if hub_findings:
            findings_by_file.setdefault(rel, []).extend(hub_findings)
            all_findings.extend(hub_findings)

    for cmp in cmp_paths:
        rel = _rel(cmp, scripture_root)
        cmp_findings = validate_companion(cmp, scripture_root)
        if cmp_findings:
            findings_by_file.setdefault(rel, []).extend(cmp_findings)
            all_findings.extend(cmp_findings)

    for tcmp in text_cmp_paths:
        rel = _rel(tcmp, scripture_root)
        tcmp_findings = validate_companion(tcmp, scripture_root)
        if tcmp_findings:
            findings_by_file.setdefault(rel, []).extend(tcmp_findings)
            all_findings.extend(tcmp_findings)

    run_findings = check_run_coverage(hub_paths, cmp_paths, scripture_root)
    for f in run_findings:
        findings_by_file.setdefault(f.path, []).append(f)
    all_findings.extend(run_findings)

    if full_osb:
        completeness_findings = check_canon_completeness(hub_paths, cmp_paths, scripture_root)
        for f in completeness_findings:
            findings_by_file.setdefault(f.path, []).append(f)
        all_findings.extend(completeness_findings)

    error_count = sum(1 for f in all_findings if f.severity == "ERROR")
    warn_count = sum(1 for f in all_findings if f.severity == "WARN")
    info_count = sum(1 for f in all_findings if f.severity == "INFO")

    if findings_by_file:
        for file_path in sorted(findings_by_file):
            print(f"\n{file_path}")
            for f in findings_by_file[file_path]:
                print(format_finding(f))

    print()
    print("=" * 60)
    print("SUMMARY")
    print(f"  Hubs:        {len(hub_paths)}")
    print(f"  Companions:  {len(cmp_paths)}")
    print(f"  Text layers: {len(text_cmp_paths)}")
    print(f"  Total verses:{total_verses}")
    print(f"  ERRORs:      {error_count}")
    print(f"  WARNs:       {warn_count}")
    print(f"  INFOs:       {info_count}")
    print("=" * 60)

    if error_count == 0:
        print("PASS")
    else:
        print(f"FAIL  ({error_count} error(s))")

    report = {
        "scripture_root": str(scripture_root),
        "hub_count": len(hub_paths),
        "companion_count": len(cmp_paths),
        "text_layer_count": len(text_cmp_paths),
        "total_verses": total_verses,
        "error_count": error_count,
        "warn_count": warn_count,
        "info_count": info_count,
        "verdict": "PASS" if error_count == 0 else "FAIL",
        "findings": [asdict(f) for f in all_findings],
    }
    report_path = Path(__file__).parent / "validation-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
