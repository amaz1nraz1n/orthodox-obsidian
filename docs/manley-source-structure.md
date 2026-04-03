# Manley Source Structure

Audit of the Internet Archive scan of Johanna Manley, *The Bible and the Holy Fathers for Orthodox* (SVS Press, 1984).

Archive item:

- `svs-press-holy-bible-the-fathers-for-orthodox-cmplr.-johanna-manley-fwdrd.-bisho`
- Item title: `SVS Press. - ''HOLY BIBLE & THE FATHERS FOR ORTHODOX'' {cmp. & ed. Johanna Manley, fwrd. Kalistos Ware}`

---

## File Metadata

- Original PDF: 80,013,019 bytes
- Page count: 1,143
- Page size: 445.45 x 661.45 pts
- PDF version: 1.4
- OCR engine: Tesseract 5.3.0
- OCR language: `eng+Latin`
- OCR derivatives available:
  - PDF scan
  - `_djvu.txt`
  - `_hocr.html`
  - `chOCR`
  - page index / search text derivatives

## Audit Verdict

The source is structurally usable for a TDD-backed extraction pass.

- The PDF text layer is noisy in the front matter, but the body pages are readable.
- The `_djvu.txt` OCR derivative is the best primary parse target.
- The book is organized by Orthodox liturgical calendar / daily readings, not as a flat chapter commentary.
- Patristic sections are regular enough to extract into `ChapterFathers` companions keyed to Scripture chapters.

## Layout Summary

- Front matter includes title page, cataloging data, preface, foreword, and introduction.
- Body text is arranged as liturgical readings by season, week, day, and pericope.
- Scripture reading headers appear as all-caps book/chapter lines, for example:
  - `MATTHEW 18`
  - `JOHN 14`
  - `GENESIS 1`
  - `ISAIAH 7`
  - `PROVERBS 9`
- Daily reading headers often include the full lectionary range, for example:
  - `Ephesians 5:9-19; Matthew 18:10-20`
  - `Acts 19:1-8; John 14:1-11`

## Commentary Structure

Each patristic unit usually has:

1. A short all-caps section heading.
2. A prose excerpt or cluster of paragraphs.
3. An attribution line that ends in `B#...` bibliography markers.

Example attribution patterns observed in the audit:

- `St. John Chrysostom. Homily LIX on Matthew XVIII, 4, 5. B#54, pp. 367-368.`
- `St. Leo the Great. The Tome, 5. B#7, p. 367.`
- `St. John Chrysostom. Homily XIX on Ephesians V B#57, pp. 137,139.`

## OCR / Parsing Notes

- `_djvu.txt` preserves the reading order well enough for chapter-level extraction.
- The PDF front matter contains OCR noise and should not drive the parser.
- `hOCR` is available as a fallback if line ordering needs confirmation.
- The source is best modeled as a Fathers companion source, not as a Scripture text source.
- `ChapterFathers` items should be keyed to the Scripture chapter being commented on, with the verse range inferred from the internal reference when present.

## Sample Readings Confirmed

The audit confirmed these representative passages:

- Great Lent: `Genesis 1`
- Pascha cycle: `John 14`
- Matthew 18 catena centered on Chrysostom on `Matthew XVIII, 4, 5`
- Luke 9 and Luke 18 readings are present and structurally consistent
- The broader shared sample envelope used by the other source adapters also maps cleanly where Manley has a matching reading header, including `Genesis 2`, `Exodus 20`, `Leviticus 1`, `Numbers 6`, `Deuteronomy 6`, `Joshua 1`, `Matthew 1`, `Matthew 5`, `John 1`, `Romans 8`, and `Revelation 1`

## Extraction Model

Recommended first-pass model:

- Output only Fathers companions.
- Keep the source in the `PatristicSource` layer, with no Scripture hub text generation.
- Use the OCR text derivative as the primary input.
- Preserve the patristic excerpt text and attribution.
- Derive the linked Scripture chapter from the daily reading header or the explicit biblical reference in the attribution line.

## Known Limitations

- The source spans many daily readings and multiple biblical books.
- Attribution lines vary slightly in punctuation and name formatting.
- Some sections cite the chapter but not a precise verse range; those cases will need a fallback verse anchor policy.
- The source is not chapter-shaped, so extraction should avoid assuming a one-file-per-chapter EPUB layout.

## Initial Build Target

Start with the shared sample envelope used by the other extractors, then fill any gaps where the OCR or lectionary structure does not line up cleanly.
