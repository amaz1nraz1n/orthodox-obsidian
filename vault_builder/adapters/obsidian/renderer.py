"""
Adapter: ObsidianRenderer

Renders domain objects (Chapter, ChapterNotes) into Obsidian-flavoured
Markdown strings.  No file I/O — pure string generation.
"""

import re

_UNSET = object()

from vault_builder.domain.canon import (
    BOOK_ABBREVIATIONS,
    BOOK_CHAPTER_COUNT,
    BOOK_GENRE,
    BOOK_TESTAMENT,
    LXX_TO_MT,
    PSALM_KATHISMA,
    book_file_prefix,
)
from vault_builder.domain.models import Chapter, ChapterFathers, ChapterNotes, NoteType, PatristicType, StudyNote
from vault_builder.ports.renderer import VaultRenderer

# ── Scripture cross-reference → wikilink injection ───────────────────────────

def _build_scripture_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, abbr in BOOK_ABBREVIATIONS.items():
        lookup[canonical.lower()] = canonical
        lookup[abbr.lower()] = canonical
    # Common NET-style alternates not covered by BOOK_ABBREVIATIONS
    lookup.update({
        "matt": "Matthew",
        "exod": "Exodus",
        "isa": "Isaiah",
        "eze": "Ezekiel",
        "philem": "Philemon",
        "1 john": "I John", "2 john": "II John", "3 john": "III John",
        "1 peter": "I Peter", "2 peter": "II Peter",
        "1 sam": "I Kingdoms", "2 sam": "II Kingdoms",
        "1 kgs": "III Kingdoms", "2 kgs": "IV Kingdoms",
        "1 chr": "I Chronicles", "2 chr": "II Chronicles",
        "1 mac": "I Maccabees", "2 mac": "II Maccabees",
        "song": "Song of Solomon",
        "ps": "Psalms",
    })
    return lookup

_SCRIPTURE_LOOKUP: dict[str, str] = _build_scripture_lookup()
_BOOK_KEYS: list[str] = sorted(_SCRIPTURE_LOOKUP.keys(), key=len, reverse=True)
_BOOK_PAT: str = "|".join(re.escape(k) for k in _BOOK_KEYS)
# Matches "John 10:30", "Gen 1:1", "1 Cor 15:3", etc. — not already inside [[
_FULL_REF_RE: re.Pattern[str] = re.compile(
    rf'(?<!\[)(?<!\w)({_BOOK_PAT})\s+(\d{{1,3}}):(\d{{1,3}})(?!\w)(?!\])',
    re.IGNORECASE,
)

_CALLOUT: dict[NoteType, str] = {
    NoteType.FOOTNOTE:    "[!note]",
    NoteType.VARIANT:     "[!info]",
    NoteType.CROSS_REF:   "[!quote]",
    NoteType.LITURGICAL:  "[!liturgy]",
    NoteType.CITATION:    "[!cite]",
    NoteType.TRANSLATOR:  "[!tn]",
    NoteType.ALTERNATIVE: "[!alt]",
    NoteType.BACKGROUND:  "[!bg]",
    NoteType.PARALLEL:    "[!parallel]",
}


def _blockquote_lines(text: str) -> list[str]:
    """Split multiline callout content into quoted Markdown lines."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    return [f"> {line}" if line else ">" for line in lines]



class ObsidianRenderer(VaultRenderer):

    # ── Hub file ──────────────────────────────────────────────────────────────

    def render_hub(self, chapter: Chapter, max_chapter: int, intro_link: str | None = None, has_fathers: bool = False) -> str:
        parts = [
            self._hub_frontmatter(chapter, max_chapter, intro_link=intro_link),
            self._nav_callout(chapter.book, chapter.number, show_fathers=has_fathers),
            "",
        ]
        for verse in chapter.sorted_verses():
            if verse.text:
                if verse.number in chapter.pericopes:
                    parts.append(f"*{chapter.pericopes[verse.number]}*")
                parts.append(f'###### v{verse.number}\n<span class="vn">{verse.number}</span> {verse.text} ^v{verse.number}\n')
                for marker in chapter.after_markers.get(verse.number, []):
                    parts.append(f"*{marker}*\n")
        return "\n".join(parts)

    def _hub_frontmatter(self, chapter: Chapter, max_chapter: int, intro_link: str | None = None) -> str:
        book = chapter.book
        ch = chapter.number
        abbr = BOOK_ABBREVIATIONS.get(book, book[:3])
        canonical_max = BOOK_CHAPTER_COUNT.get(book, max_chapter)
        pfx = book_file_prefix(book)
        prev_link = f"[[{pfx} {ch - 1}]]" if ch > 1 else ""
        next_link = f"[[{pfx} {ch + 1}]]" if ch < canonical_max else ""
        testament = BOOK_TESTAMENT.get(book, "OT")
        genre = BOOK_GENRE.get(book, "")

        psalm_fields = ""
        aliases = [f'"{abbr} {ch}"']
        css_list = ["scripture-hub"]
        if book == "Psalms":
            mt_num = LXX_TO_MT.get(ch)
            lxx_ref_line = f'lxx_ref: "{book} {ch}"\n'
            mt_ref_line = f'mt_ref: "{book} {mt_num}"\n' if mt_num is not None else ""
            psalm_fields = lxx_ref_line + mt_ref_line
            kath_data = PSALM_KATHISMA.get(ch)
            if kath_data:
                kathisma, stasis = kath_data
                psalm_fields += f'kathisma: {kathisma}\n'
                if stasis:
                    psalm_fields += f'stasis: {stasis}\n'
            css_list.append("psalter")
            if mt_num is not None and mt_num != ch:
                aliases.append(f'"{abbr} {mt_num}"')
        cssclasses = f'cssclasses: [{", ".join(css_list)}]\n'
        aliases_yaml = f'aliases: [{", ".join(aliases)}]'

        intro_field = f'intro: "{intro_link}"\n' if intro_link else ""
        return (
            f"---\n"
            f"{psalm_fields}"
            f"{cssclasses}"
            f'testament: "{testament}"\n'
            f'genre: "{genre}"\n'
            f'book_id: "{abbr}"\n'
            f'{aliases_yaml}\n'
            f'up: "[[{book}]]"\n'
            f'prev: "{prev_link}"\n'
            f'next: "{next_link}"\n'
            f"{intro_field}"
            f"---"
        )

    def _companion_nav(
        self,
        book: str,
        chapter: int,
        own_notes_suffix: str | None = None,
        own_text_suffix: str | None = None,
        net_text_link: bool = False,
        show_fathers: bool = False,
    ) -> str:
        """Scoped nav for companion files: Hub · [own notes or text] · NET Notes · Fathers.

        own_notes_suffix: notes file for text companions (e.g. "EOB Notes", "Lexham Notes").
                          Pass None when there is no notes companion (e.g. Greek NT, LXX).
        own_text_suffix: text file for notes companions (e.g. "NETS", "EOB", "Lexham").
                         Pass None when there is no text companion (e.g. OSB Notes).
        net_text_link: True for NET Notes only — replaces NET Notes link with NET text link.
        show_fathers: True when a Fathers companion exists for this chapter.
        """
        pfx = book_file_prefix(book)
        parts = [f"[[{pfx} {chapter}|Hub]]"]
        if own_notes_suffix:
            parts.append(f"[[{pfx} {chapter} \u2014 {own_notes_suffix}|{own_notes_suffix}]]")
        if own_text_suffix:
            parts.append(f"[[{pfx} {chapter} \u2014 {own_text_suffix}|{own_text_suffix}]]")
        if net_text_link:
            parts.append(f"[[{pfx} {chapter} \u2014 NET|NET text]]")
        else:
            parts.append(f"[[{pfx} {chapter} \u2014 NET Notes|NET Notes]]")
        if show_fathers:
            parts.append(f"[[{pfx} {chapter} \u2014 Fathers|Fathers]]")
        return f"> **Nav:** {' \u00b7 '.join(parts)}"

    def _inject_scripture_links(self, text: str, current_book: str) -> str:
        """Convert plain Scripture refs (Book Ch:V) in note content to wikilinks."""
        def replace(m: re.Match[str]) -> str:
            canonical = _SCRIPTURE_LOOKUP.get(m.group(1).lower())
            if canonical is None:
                return m.group(0)
            pfx = book_file_prefix(canonical)
            return f"[[{pfx} {int(m.group(2))}#v{int(m.group(3))}|{m.group(0)}]]"
        return _FULL_REF_RE.sub(replace, text)

    def _nav_callout(
        self,
        book: str,
        chapter: int,
        notes_suffix: str | None = "OSB Notes",
        show_source_notes: bool = True,
        show_greek: bool = True,
        show_fathers: bool = False,
    ) -> str:
        """Hub modes nav. Order: OSB · EOB/Lexham · Greek · NET Notes · + · source notes · Study Notes · Fathers.

        notes_suffix: suffix for the Study Notes link (e.g. "OSB Notes"). Pass None to suppress.
        show_source_notes: when True, insert EOB Notes (NT) or Lexham Notes (OT).
        show_greek: when False, omit the Greek NT / LXX link (e.g. viewing from the Greek companion).
        show_fathers: when True, append the Fathers companion link.
        """
        is_ot = BOOK_TESTAMENT.get(book) == "OT"
        pfx = book_file_prefix(book)
        source_notes_label = "Lexham Notes" if is_ot else "EOB Notes"

        parts: list[str] = [f"[[{pfx} {chapter}|OSB]]"]

        if is_ot:
            parts.append(f"[[{pfx} {chapter} \u2014 Lexham|Lexham]]")
        else:
            parts.append(f"[[{pfx} {chapter} \u2014 EOB|EOB]]")

        if show_greek:
            if is_ot:
                parts.append(f"[[{pfx} {chapter} \u2014 LXX|LXX]]")
            else:
                parts.append(f"[[{pfx} {chapter} \u2014 Greek NT|Greek NT]]")

        parts.append(f"[[{pfx} {chapter} \u2014 NET|NET]]")
        parts.append(f"[[{pfx} {chapter} \u2014 NET Notes|NET Notes]]")
        parts.append(f"[[{pfx} {chapter} \u2014 Translations|+]]")

        if show_source_notes:
            parts.append(f"[[{pfx} {chapter} \u2014 {source_notes_label}|{source_notes_label}]]")

        if notes_suffix:
            parts.append(f"[[{pfx} {chapter} \u2014 {notes_suffix}|Study Notes]]")

        if show_fathers:
            parts.append(f"[[{pfx} {chapter} \u2014 Fathers|Fathers]]")

        return f"> **Modes:** {' \u00b7 '.join(parts)}"

    # ── Text companion file ───────────────────────────────────────────────────

    def render_text_companion(
        self,
        chapter: Chapter,
        source: str,
        notes_suffix: object = _UNSET,
        has_fathers: bool = False,
    ) -> str:
        """Render a parallel text layer (e.g. Lexham, EOB) as a chapter companion.

        notes_suffix: suffix for the Study Notes link (e.g. "EOB Notes").
                      Defaults to f"{source} Notes". Pass None to suppress the link.
        has_fathers: when True, include a Fathers companion link after NET Notes.
        """
        book, ch = chapter.book, chapter.number
        abbr = BOOK_ABBREVIATIONS.get(book, book[:3])
        resolved_notes_suffix: str | None = (
            f"{source} Notes" if notes_suffix is _UNSET else notes_suffix  # type: ignore[assignment]
        )
        parts = [
            f'---\ncssclasses: [scripture-hub]\nhub: "[[{book_file_prefix(book)} {ch}]]"\nsource: "{source}"\n---',
            "",
            self._companion_nav(
                book,
                ch,
                own_notes_suffix=resolved_notes_suffix,
                show_fathers=has_fathers,
            ),
            "",
        ]
        for verse in chapter.sorted_verses():
            if verse.text:
                if verse.number in chapter.pericopes:
                    parts.append(f"*{chapter.pericopes[verse.number]}*")
                parts.append(
                    f'###### v{verse.number}\n'
                    f'<span class="vn">{verse.number}</span> {verse.text} ^v{verse.number}\n'
                )
                for marker in chapter.after_markers.get(verse.number, []):
                    parts.append(f"*{marker}*\n")
        return "\n".join(parts)

    # ── Notes companion file ──────────────────────────────────────────────────

    def render_net_notes(
        self,
        notes: ChapterNotes,
        pericopes: dict[int, str] | None = None,
        has_fathers: bool = False,
    ) -> str:
        """Render a NET Bible notes companion with unified callouts ([!tn], [!info], [!note], [!bg])."""
        book, ch = notes.book, notes.chapter
        abbr = BOOK_ABBREVIATIONS.get(book, book[:3])
        lines = [
            f'---\nhub: "[[{book_file_prefix(book)} {ch}]]"\nsource: "{notes.source}"\n---',
            "",
            self._companion_nav(book, ch, net_text_link=True, show_fathers=has_fathers),
            "",
        ]

        tagged: list[tuple[NoteType, StudyNote]] = []
        for note_type in (NoteType.FOOTNOTE, NoteType.VARIANT, NoteType.TRANSLATOR, NoteType.BACKGROUND):
            for note in notes.sorted_notes(note_type):
                tagged.append((note_type, note))

        tagged.sort(key=lambda x: (x[1].verse_number, x[1].sort_key))

        pfx = book_file_prefix(book)
        i = 0
        while i < len(tagged):
            verse_num = tagged[i][1].verse_number
            if verse_num == 0:
                lines.append("### Introduction")
            else:
                if pericopes and verse_num in pericopes:
                    lines.append(f"*{pericopes[verse_num]}*")
                text_target = f"{pfx} {ch} \u2014 {notes.source}"
                lines.append(f"### [[{text_target}#v{verse_num}|{abbr} {ch}:{verse_num}]]")
                lines.append(f"^v{verse_num}")
            while i < len(tagged) and tagged[i][1].verse_number == verse_num:
                family, note = tagged[i]
                callout = _CALLOUT[family]
                block_id = f" ^{note.anchor_id}" if note.anchor_id else ""
                lines.append("")
                lines.append(f"> {callout} {note.ref_str}{block_id}")
                lines.extend(_blockquote_lines(self._inject_scripture_links(note.content, book)))
                i += 1
            lines.append("")

        return "\n".join(lines)

    def render_notes(self, notes: ChapterNotes, has_fathers: bool = False) -> str:
        book, ch, source = notes.book, notes.chapter, notes.source
        pfx = book_file_prefix(book)
        lines = [
            f'---\nhub: "[[{pfx} {ch}]]"\nsource: "{source}"\n---',
            "",
            self._companion_nav(
                book, ch,
                own_text_suffix=source if source != "OSB" else None,
                show_fathers=has_fathers,
            ),
            "",
        ]

        for article in notes.articles:
            lines.append(article.content)
            lines.append("")

        tagged: list[tuple[NoteType, StudyNote]] = []
        for note_type in NoteType:
            for note in notes.sorted_notes(note_type):
                tagged.append((note_type, note))

        tagged.sort(key=lambda x: (x[1].verse_number, x[1].sort_key))

        text_target = (
            f"{pfx} {ch} \u2014 {source}"
            if source in ("EOB", "Lexham", "NETS")
            else f"{pfx} {ch}"
        )
        i = 0
        while i < len(tagged):
            verse_num = tagged[i][1].verse_number
            heading_ref = re.sub(r'(?<=[0-9])[a-z]$', '', tagged[i][1].ref_str)
            # For cross-chapter pericopes (e.g. "1:24-3", end < start), strip the
            # range suffix from the wikilink display — the heading links to the start
            # verse only; the full range string still appears in the callout body.
            m_cross = re.match(r'^(\d+:\d+)-(\d+)$', heading_ref)
            if m_cross and int(m_cross.group(2)) < int(m_cross.group(1).split(':')[1]):
                heading_ref = m_cross.group(1)
            lines.append(f"### [[{text_target}#v{verse_num}|{heading_ref}]]")
            lines.append(f"^v{verse_num}")
            first_in_group = True
            while i < len(tagged) and tagged[i][1].verse_number == verse_num:
                family, note = tagged[i]
                callout = _CALLOUT[family]
                if not first_in_group:
                    lines.append("")
                if callout:
                    block_id = f" ^{note.anchor_id}" if (callout and note.anchor_id) else ""
                    lines.append(f"> {callout} {note.ref_str}{block_id}")
                    lines.extend(_blockquote_lines(note.content))
                else:
                    lines.append(note.content)
                first_in_group = False
                i += 1
            lines.append("")

        return "\n".join(lines)

    # ── Book intro file ───────────────────────────────────────────────────

    def render_book_intro(self, book: str, content: str) -> str:
        """Render a per-book OSB intro companion."""
        return (
            f"---\n"
            f'cssclasses: [osb-intro]\n'
            f'book: "{book}"\n'
            f'source: "OSB"\n'
            f'up: "[[{book}]]"\n'
            f"---\n\n"
            f"{content}\n"
        )

    # ── Translations hub ──────────────────────────────────────────────────

    def render_translations_hub(
        self,
        book: str,
        chapter: int,
        sources: list[tuple[str, str | None]],
    ) -> str:
        """Render a per-chapter index of all available text translations.

        sources: list of (display_label, file_suffix) pairs.
                 suffix=None links to the hub itself (OSB).
                 suffix="EOB" links to [[{pfx} {ch} — EOB|EOB]], etc.
        """
        pfx = book_file_prefix(book)
        lines = [
            f'---\nhub: "[[{pfx} {chapter}]]"\ncssclasses: [translations-index]\n---',
            "",
            f"> **Nav:** [[{pfx} {chapter}|Hub]]",
            "",
        ]
        for label, suffix in sources:
            if suffix is None:
                lines.append(f"- [[{pfx} {chapter}|{label}]]")
            else:
                lines.append(f"- [[{pfx} {chapter} \u2014 {suffix}|{label}]]")
        return "\n".join(lines)

    # ── Patristic catena companion ────────────────────────────────────────

    def render_fathers(self, fathers: ChapterFathers) -> str:
        """Render a Patristic catena companion for a Scripture chapter.

        Each pericope/verse group is a ### heading linking to the hub verse anchor,
        followed by [!cite] callouts — one per excerpt — with attribution in
        the callout title and excerpt body below.
        """
        book, ch = fathers.book, fathers.chapter
        abbr = BOOK_ABBREVIATIONS.get(book, book[:3])
        pfx = book_file_prefix(book)
        lines = [
            f'---\nhub: "[[{pfx} {ch}]]"\nsource: "{fathers.source}"\n---',
            "",
            self._companion_nav(book, ch),
            "",
        ]

        i = 0
        excerpts = fathers.sorted_excerpts()
        while i < len(excerpts):
            ptype, exc = excerpts[i]
            verse_start = exc.verse_start
            # Heading: link to first verse of the pericope
            ref = f"{abbr} {ch}:{verse_start}"
            lines.append(f"### [[{pfx} {ch}#v{verse_start}|{ref}]]")
            lines.append(f"^v{verse_start}")
            while i < len(excerpts) and excerpts[i][1].verse_start == verse_start:
                _, exc = excerpts[i]
                attribution = exc.work
                if exc.section:
                    attribution += f", {exc.section}"
                lines.append("")
                lines.append(f"> [!cite] {exc.father} — {attribution}")
                lines.extend(_blockquote_lines(exc.content))
                i += 1
            lines.append("")

        return "\n".join(lines)

    # ── Apostolic Fathers chapter file ────────────────────────────────────

    def render_patristic_chapter(
        self,
        chapter: Chapter,
        notes: ChapterNotes,
        max_chapter: int,
    ) -> str:
        """
        Render an Apostolic Fathers chapter as a single self-contained file.

        Verse text and footnotes are combined: each verse block is followed
        immediately by any footnote fragments for that verse as plain
        blockquotes.  Scripture cross-references in footnotes are expected
        to have been pre-converted to vault wikilinks by the source adapter.

        Block IDs use ^{chapter}-{verse} to avoid collisions with Scripture
        hub block IDs (which use ^v{verse}).
        """
        doc   = chapter.book
        ch    = chapter.number
        prev  = f"[[{doc} {ch - 1}]]" if ch > 1 else ""
        next_ = f"[[{doc} {ch + 1}]]" if ch < max_chapter else ""

        lines = [
            "---",
            "cssclasses: [patristic-hub]",
            f'document: "{doc}"',
            f"chapter: {ch}",
            f'up: "[[{doc}]]"',
            f'prev: "{prev}"',
            f'next: "{next_}"',
            "---",
            "",
        ]

        note_map: dict[int, list[str]] = {}
        for note in notes.footnotes:
            note_map.setdefault(note.verse_number, []).append(note.content)

        for verse in chapter.sorted_verses():
            if not verse.text:
                continue
            lines.append(f"###### {ch}.{verse.number}")
            lines.append(
                f'<span class="vn">{verse.number}</span> {verse.text} '
                f"^{ch}-{verse.number}"
            )
            for frag in note_map.get(verse.number, []):
                lines.append("")
                lines.append(f"> {frag}")
            lines.append("")

        return "\n".join(lines)
