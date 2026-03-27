# Greek NT Source Structure

Audit of available Greek NT sources, format details, and the feasibility
of producing a polytonic Antoniades Patriarchal Text for the vault.

---

## Sources on disk

| Path | Contents | Format | Accents |
|------|----------|--------|---------|
| `source_files/Greek/antoniades/` | Antoniades 1904/1912 Patriarchal NT | Stripped Beta Code (`.ANT`), pre-converted unicode (`.txt`), morphological (`.UAN`) | **None** — all diacritics stripped |
| `source_files/Greek/byzantine-majority-text/` | Robinson-Pierpont Byzantine Majority Text 2018 | CSV (`chapter,verse,text`), TEI-XML | **Full polytonic Unicode** |

---

## The accent problem

### What the Antoniades files actually contain

The `.ANT` files use a **stripped Beta Code** — all accent marks, breathing marks,
and iota subscripts are absent. This is a deliberate encoding choice in Robinson's
electronic transcription, not a conversion artifact.

```
# JOH.ANT — what is actually there
1:1 en arch hn o logov, kai o logov hn prov ton yeon ...

# What full polytonic Beta Code would look like
1:1 e)n a)rxh=| h}=n o( lo/gov, kai\ o( lo/gov h}=n pro\v to\n qeo/n ...
```

The pre-converted unicode files (`textonly/unicode/*.txt`) reflect this exactly:

```
# JOH.txt — unaccented monotonic output
1:1 εν αρχη ην ο λογος, και ο λογος ην προς τον θεον ...
```

The morphological `.UAN` files add Strong's numbers and parsing codes but
share the same unaccented base text. No diacritic data exists anywhere
in the repository.

**The 1904 Antoniades printed edition had full polytonic accents.**
Robinson's electronic transcription discarded them. There is no known
freely-available digital transcription of the Antoniades text that
restores them.

---

## The BYZ-ANT.TXT collation

`textonly/BYZ-ANT.TXT` is a complete collation of every difference between
Robinson-Pierpont Byzantine Majority Text 2005 (Byz05) and the Antoniades
1912 corrected edition, prepared by Robinson and Ala-Konni.

### Summary statistics

| Category | Count |
|----------|-------|
| Total differences | 1,555 |
| Additions (Antoniades has words Byz05 lacks) | 246 |
| Substitutions / deletions / transpositions | 1,315 |
| Books with most divergence | Revelation (262), Mark (293), Luke (289) |
| Books with least divergence | Philemon (1), 3 John (1), 2 Peter (2) |

### Format

```
<BOOK CH:V>
BYZ05_READING ] ANTONIADES_READING
```

Operators used in the Antoniades column:
- `word` — replace Byz05 word(s) with this
- `+ word` — Antoniades inserts word(s) not in Byz05
- `[word]` — word appears in small type in Antoniades (bracketed / uncertain)
- `(sic)` — acknowledged error in Antoniades edition
- Multi-word entries on one line may affect a phrase, not just one word
- Transpositions shown by reordering words on the right side

All readings on **both sides** are unaccented Beta Code.

---

## Reconstruction feasibility

### Option A: Keep Byzantine Majority Text CSV as-is (current)

**What it is:** Robinson-Pierpont 2018, polytonic Unicode, Public Domain.
Already implemented as `GreekNtCsvSource`.

**Divergence from Antoniades:** 1,555 locations across the entire NT.
Per-book rate: ~0.5–3% of verses affected. The texts are >98% identical.

**Pros:** Polytonic throughout. Zero additional work. Academically sound.

**Cons:** Not the Antoniades Patriarchal Text. A small number of Orthodox
liturgical readings will differ from the ecclesiastical standard.

---

### Option B: Apply BYZ-ANT.TXT to produce unaccented Antoniades

**Approach:** Parse the 1,555 collation entries; apply each as a patch
to the unaccented `.ANT` base text (or equivalently to the unicode
`textonly/unicode/` files).

**Result:** Correct Antoniades readings, unaccented throughout.
This is essentially what `textonly/unicode/` already provides — we have
this text today without any patch work.

**Net gain: zero.** The patch source and target are both unaccented.

---

### Option C: Hybrid polytonic patch (partially feasible)

**Approach:**
1. Start with Byzantine Majority Text CSV (polytonic Unicode) as the base.
2. For each of the 1,555 collation entries, apply the Antoniades reading.
3. For patch-site words, attempt to infer polytonic accents.

**Where accent inference is possible:**
- Substitutions where the Antoniades word differs only in spelling
  (e.g., `diati` vs. `dia ti`) — the polytonic form can be looked up
  from the Byzantine CSV or a Strong's lexicon by lemma match.
- Simple word replacements where the replacement word appears with
  polytonic accents elsewhere in the Byzantine CSV — same form, copy accents.

**Where accent inference fails:**
- Additions (246 entries): Antoniades adds words not present in Byz05 at
  that verse. No polytonic form to copy from the Byzantine source.
- Words with context-sensitive accentuation (enclitics, proclitics,
  accent shifts in compounds) — wrong accent is worse than none.
- Transpositions: reordering words can shift accent patterns.
- `(sic)` typos in Antoniades that differ from any valid Greek form.

**Realistic outcome:** ~80–90% of patch sites could be accented correctly
using lemma lookup; the remaining 10–20% (particularly additions and
complex substitutions) would be unaccented or wrongly accented.
The output would be a **mixed-quality polytonic text** — not reliably
usable for liturgical reference.

**Implementation cost:** High. Requires:
1. A parser for the BYZ-ANT.TXT collation format (multi-line, context-sensitive)
2. A Beta Code → Unicode converter for Antoniades readings
3. A polytonic accent lookup table (Strong's-indexed or lemma-indexed)
4. Alignment logic to locate the patch site within the Byzantine CSV verse

---

### Option D: Find an alternative Antoniades digitization

**Context:** The 1904 Antoniades edition is in the public domain. A properly
polytonic digitization may exist in:
- Logos / Accordance software databases (not freely extractable)
- A Greek Orthodox scholarly project (not found in open repositories as of 2026-03-21)
- The `byztext.com` website may have additional resources not in the GitHub repo

**Status:** No freely-available polytonic Antoniades digitization found.
Would require active research or community contact (e.g., Robinson directly).

---

## Decision record (2026-03-21)

**Current vault uses Option A:** Byzantine Majority Text 2018 CSV.
Labeled as `source: "Greek NT"` in companion frontmatter.

**Rationale:**
- Only polytonic source available without reconstruction
- 1,555 differences from Antoniades are well-documented and concentrated
  in the Gospels and Revelation; the epistles diverge minimally
- For personal study, polytonic readability outweighs ecclesiastical
  text-critical precision
- Option C is not ruled out as a future enhancement if a reliable
  accent lookup table is assembled; document this as a known gap

**If Antoniades with polytonic accents becomes available** (Option D),
switching is straightforward: update `GreekNtCsvSource` to point to the
new source directory and adjust the per-line parser.

---

## Byzantine Majority Text CSV format reference

Files: `source_files/Greek/byzantine-majority-text/csv-unicode/ccat/no-variants/*.csv`

```
chapter,verse,text
1,1,"Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος."
1,2,Οὗτος ἦν ἐν ἀρχῇ πρὸς τὸν θεόν.
```

- Header row always present
- Some verses prefixed with `¶` (paragraph marker) — stripped by adapter
- `ACT24.csv` — Western text variant of Acts 24:6–7; skipped
- `PA.csv` — Pericope Adulterae (Jn 7:53–8:11); skipped
- 27 canonical NT book files; adapter processes in canonical order

## Antoniades unicode format reference

Files: `source_files/Greek/antoniades/greektext-antoniades-master/textonly/unicode/*.txt`

```
1:1 εν αρχη ην ο λογος, και ο λογος ην προς τον θεον, ...
```

- One verse per line: `chapter:verse text`
- Blank lines between some verses (paragraph separators; ignored by any parser)
- Continuation lines (long verses wrap): lines without `N:N` prefix are
  continuations of the previous verse
- 27 NT books; file codes differ from Byzantine CSV (MT/MR/LU vs MAT/MAR/LUK)
