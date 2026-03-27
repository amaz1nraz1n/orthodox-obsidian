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
from vault_builder.domain.models import Chapter, ChapterNotes
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

_CALLOUT = {
    "footnote":         "",
    "variant":          "[!info]",
    "cross_reference":  "[!quote]",
    "liturgical":       "[!liturgy]",
    "citation":         "[!cite]",
    "translator_note":  "[!tn]",
    "alternative":      "[!alt]",
    "background_note":  "[!bg]",
    "parallel_passage": "[!parallel]",
}

# NET Bible note type → Obsidian callout label
_NET_CALLOUT = {
    "footnote":        "[!sn]",   # sn  = Study Note
    "variant":         "[!tc]",   # tc  = Text-critical Note
    "cross_reference": "[!map]",  # map = Map Note
    "translator_note": "[!tn]",   # tn  = Translator's Note
}


class ObsidianRenderer(VaultRenderer):

    # ── Hub file ──────────────────────────────────────────────────────────────

    def render_hub(self, chapter: Chapter, max_chapter: int, intro_link: str | None = None) -> str:
        parts = [
            self._hub_frontmatter(chapter, max_chapter, intro_link=intro_link),
            self._nav_callout(chapter.book, chapter.number),
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
        net_text_link: bool = False,
    ) -> str:
        """Scoped nav for companion files: Hub · [own notes] · NET Notes.

        own_notes_suffix: notes file for text companions (e.g. "EOB Notes", "Lexham Notes").
                          Pass None when there is no notes companion (e.g. Greek NT, LXX).
        net_text_link: True for NET Notes only — replaces NET Notes link with NET text link.
        """
        pfx = book_file_prefix(book)
        parts = [f"[[{pfx} {chapter}|Hub]]"]
        if own_notes_suffix:
            parts.append(f"[[{pfx} {chapter} \u2014 {own_notes_suffix}|{own_notes_suffix}]]")
        if net_text_link:
            parts.append(f"[[{pfx} {chapter} \u2014 NET|NET text]]")
        else:
            parts.append(f"[[{pfx} {chapter} \u2014 NET Notes|NET Notes]]")
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
        show_net: bool = True,
        show_noab_rsv: bool = True,
    ) -> str:
        """Shared modes nav used by all file types.

        notes_suffix: suffix for the Study Notes link (e.g. "OSB Notes", "Lexham Notes").
                      Pass None when the current file IS the notes layer.
        show_source_notes: when True, insert a link to EOB Notes (NT) or Lexham Notes (OT).
        show_greek: when True and NT, insert Greek NT link. Pass False from Greek companion.
        show_net: when True, insert NET text companion link. Pass False from NET companion.
        show_noab_rsv: when True, insert NOAB RSV text companion link.
        """
        is_ot = BOOK_TESTAMENT.get(book) == "OT"
        pfx = book_file_prefix(book)
        source_notes_label = "Lexham Notes" if is_ot else "EOB Notes"
        mid = (
            f"[[{pfx} {chapter} \u2014 Lexham|Lexham]] \u00b7 "
            if is_ot
            else f"[[{pfx} {chapter} \u2014 EOB|EOB]] \u00b7 "
        )
        net_link = (
            f"[[{pfx} {chapter} \u2014 NET|NET]] \u00b7 "
            if show_net
            else ""
        )
        if not show_greek:
            greek_link = ""
        elif is_ot:
            greek_link = f"[[{pfx} {chapter} \u2014 LXX|LXX]] \u00b7 "
        else:
            greek_link = f"[[{pfx} {chapter} \u2014 Greek NT|Greek NT]] \u00b7 "
        source_notes_link = (
            f"[[{pfx} {chapter} \u2014 {source_notes_label}|{source_notes_label}]] \u00b7 "
            if show_source_notes
            else ""
        )
        noab_rsv_link = (
            f"[[{pfx} {chapter} \u2014 NOAB RSV|RSV]] \u00b7 "
            if show_noab_rsv
            else ""
        )
        study = (
            f" \u00b7 [[{pfx} {chapter} \u2014 {notes_suffix}|Study Notes]]"
            if notes_suffix
            else ""
        )
        return (
            f"> **Modes:** "
            f"[[{pfx} {chapter}|OSB]] \u00b7 "
            f"{mid}"
            f"{net_link}"
            f"{greek_link}"
            f"{noab_rsv_link}"
            f"{source_notes_link}"
            f"[[{pfx} {chapter} \u2014 NET Notes|NET Notes]]"
            f"{study}"
        )

    # ── Text companion file ───────────────────────────────────────────────────

    def render_text_companion(
        self, chapter: Chapter, source: str, notes_suffix: object = _UNSET
    ) -> str:
        """Render a parallel text layer (e.g. Lexham, EOB) as a chapter companion.

        notes_suffix: suffix for the Study Notes link (e.g. "EOB Notes").
                      Defaults to f"{source} Notes". Pass None to suppress the link.
        """
        book, ch = chapter.book, chapter.number
        abbr = BOOK_ABBREVIATIONS.get(book, book[:3])
        resolved_notes_suffix: str | None = (
            f"{source} Notes" if notes_suffix is _UNSET else notes_suffix  # type: ignore[assignment]
        )
        parts = [
            f'---\ncssclasses: [scripture-hub]\nhub: "[[{book_file_prefix(book)} {ch}]]"\nsource: "{source}"\n---',
            "",
            self._companion_nav(book, ch, own_notes_suffix=resolved_notes_suffix),
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
    ) -> str:
        """Render a NET Bible notes companion with tn/tc/sn/map callouts."""
        book, ch = notes.book, notes.chapter
        abbr = BOOK_ABBREVIATIONS.get(book, book[:3])
        lines = [
            f'---\nhub: "[[{book_file_prefix(book)} {ch}]]"\nsource: "{notes.source}"\n---',
            "",
            self._companion_nav(book, ch, net_text_link=True),
            "",
        ]

        tagged = []
        for note in notes.footnotes:
            tagged.append(("footnote", note))
        for note in notes.variants:
            tagged.append(("variant", note))
        for note in notes.cross_references:
            tagged.append(("cross_reference", note))
        for note in notes.translator_notes:
            tagged.append(("translator_note", note))

        tagged.sort(key=lambda x: x[1].verse_number)

        pfx = book_file_prefix(book)
        i = 0
        while i < len(tagged):
            verse_num = tagged[i][1].verse_number
            if verse_num == 0:
                lines.append("### Introduction")
            else:
                if pericopes and verse_num in pericopes:
                    lines.append(f"*{pericopes[verse_num]}*")
                lines.append(f"### [[{pfx} {ch}#v{verse_num}|{abbr} {ch}:{verse_num}]]")
            while i < len(tagged) and tagged[i][1].verse_number == verse_num:
                family, note = tagged[i]
                callout = _NET_CALLOUT[family]
                lines.append("")
                lines.append(f"> {callout} {note.ref_str}")
                lines.append(f"> {self._inject_scripture_links(note.content, book)}")
                i += 1
            lines.append("")

        return "\n".join(lines)

    def render_notes(self, notes: ChapterNotes) -> str:
        book, ch, source = notes.book, notes.chapter, notes.source
        pfx = book_file_prefix(book)
        lines = [
            f'---\nhub: "[[{pfx} {ch}]]"\nsource: "{source}"\n---',
            "",
            self._companion_nav(book, ch),
            "",
        ]

        for article in notes.articles:
            lines.append(article.content)
            lines.append("")

        tagged = []
        for note in notes.sorted_footnotes():
            tagged.append(("footnote", note))
        for note in notes.sorted_variants():
            tagged.append(("variant", note))
        for note in notes.sorted_cross_references():
            tagged.append(("cross_reference", note))
        for note in notes.sorted_liturgical():
            tagged.append(("liturgical", note))
        for note in notes.sorted_citations():
            tagged.append(("citation", note))
        for note in notes.sorted_translator_notes():
            tagged.append(("translator_note", note))
        for note in notes.sorted_alternatives():
            tagged.append(("alternative", note))
        for note in notes.sorted_background_notes():
            tagged.append(("background_note", note))
        for note in notes.sorted_parallel_passages():
            tagged.append(("parallel_passage", note))

        tagged.sort(key=lambda x: x[1].verse_number)

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
            lines.append(f"### [[{pfx} {ch}#v{verse_num}|{heading_ref}]]")
            first_in_group = True
            while i < len(tagged) and tagged[i][1].verse_number == verse_num:
                family, note = tagged[i]
                callout = _CALLOUT[family]
                if not first_in_group:
                    lines.append("")
                if callout:
                    lines.append(f"> {callout} {note.ref_str}")
                    lines.append(f"> {note.content}")
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
