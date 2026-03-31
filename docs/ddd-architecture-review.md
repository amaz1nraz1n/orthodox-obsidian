# DDD Architecture Review

Source: [Architecture Patterns with Python (Cosmic Python)](https://www.cosmicpython.com/book/)
Reviewed against: `vault_builder/` hexagonal architecture

---

## Summary Verdict

**All items complete as of 2026-03-31** (PER-26–35, 367 tests passing).

The core hexagonal structure (domain → ports → adapters) is solid and well-applied. All identified gaps from the Cosmic Python review have been resolved.

---

## Chapter 1 — Domain Modeling

**Relevant to this project: High**

### Gaps Found

#### 1.1 Value objects are mutable
`Verse`, `StudyNote`, `StudyArticle`, `BookIntro`, `ChapterIntro`, `PartIntro` are all defined by their data alone — they have no identity beyond their fields. These should be frozen.

```python
# current
@dataclass
class Verse:
    number: int
    text: str

# correct
@dataclass(frozen=True)
class Verse:
    number: int
    text: str
```

Affected: all six types above. `Chapter`, `Book`, `ChapterNotes` are aggregates and stay mutable.

#### 1.2 Aggregates have no mutation methods — adapters reach inside them
The book's core critique of the anemic domain model: logic that belongs to the aggregate lives in adapters instead. Right now 16 source adapters do:

```python
chapter.verses[num] = Verse(num, text)         # mutation in adapter
notes.footnotes.append(StudyNote(...))          # mutation in adapter
```

The aggregate should own its mutation and enforce invariants:

```python
class Chapter:
    def add_verse(self, number: int, text: str) -> None:
        if number in self.verses:
            raise DuplicateVerseError(f"{self.book} {self.number}:{number}")
        self.verses[number] = Verse(number, text)

class ChapterNotes:
    def add_note(self, note_type: NoteType, note: StudyNote) -> None:
        getattr(self, self._NOTE_LISTS[note_type]).append(note)
```

#### 1.3 Missing `VerseRef` value object
`(book, chapter, verse)` as loose strings/ints appears across adapters and renderers. A named, frozen value object expresses the concept:

```python
@dataclass(frozen=True)
class VerseRef:
    book: str
    chapter: int
    verse: int

    def __str__(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse}"
```

This would replace ad-hoc `ref_str = "1:14"` fields and fragile string parsing in multiple adapters.

#### 1.4 No domain exceptions
Generic `ValueError` is raised when things go wrong. Domain-language exceptions communicate intent:

```python
class DuplicateVerseError(Exception): ...
class UnknownBookError(Exception): ...
class MissingSourceError(Exception): ...
```

---

## Chapter 2 — Repository Pattern

**Relevant to this project: Medium**

The `ScriptureSource` ABC already functions as a repository port — sources are "repositories of Scripture content." The core pattern is already applied. The gap is test doubles.

### Gaps Found

#### 2.1 No fake implementations for fast testing
The book prescribes: every port should have a `Fake*` implementation for use in unit tests. There is no `FakeScriptureSource` or `FakeVaultRenderer`. Without these, tests must use real EPUB files or mock at a lower level.

```python
class FakeScriptureSource(ScriptureSource):
    def __init__(self, books: list[Book] | None = None, notes: list[ChapterNotes] | None = None):
        self._books = books or []
        self._notes = notes or []

    def read_text(self) -> Iterator[Book]:
        return iter(self._books)

    def read_notes(self) -> Iterator[ChapterNotes]:
        return iter(self._notes)
```

Design signal from the book: if a fake is hard to write, the interface is overcomplicated. `ScriptureSource` fakes easily — good sign.

#### 2.2 `ObsidianWriter` has no port
The renderer has a port (`VaultRenderer`), but the writer does not. This means it cannot be swapped for a `FakeVaultWriter` in tests, or replaced with a different output target.

```python
class VaultWriter(ABC):
    @abstractmethod
    def write_hub(self, chapter: Chapter, content: str) -> Path: ...
    @abstractmethod
    def write_notes(self, notes: ChapterNotes, content: str) -> Path: ...
    @abstractmethod
    def write_text_companion(self, chapter: Chapter, source: str, content: str) -> Path: ...
    @abstractmethod
    def write_book_intro(self, book: str, content: str) -> Path: ...
```

---

## Chapter 3 — Abstractions and Coupling (Functional Core, Imperative Shell)

**Relevant to this project: High**

The renderer is already a nearly perfect functional core — pure functions returning strings, no I/O. The writer is the imperative shell. This separation is correct.

### Gaps Found

#### 3.1 Extract scripts mix all three concerns
The book identifies three phases that should be separated: *interrogation* (read inputs), *decision logic* (compute changes), *mutation* (apply outputs). The `scripts/extract_*.py` scripts collapse all three:

```python
# current pattern in extract scripts
source = OsbEpubSource(epub_path)           # input
renderer = ObsidianRenderer()               # decision
writer = ObsidianWriter(output_dir)         # mutation

for book in source.read_text():             # all three tangled in one loop
    for ch in book.chapters.values():
        hub = renderer.render_hub(ch, ...)
        writer.write_hub(ch, hub)
```

There is no seam between "compute what to write" and "write it." This makes the orchestration logic untestable without hitting the filesystem.

#### 3.2 Mocking instead of abstraction
Without fake ports, tests presumably use `mock.patch` or real files. The book explicitly warns: "Patching out the dependency makes unit testing possible but does nothing to improve design." Fakes force better abstractions.

---

## Chapter 4 — Service Layer

**Relevant to this project: High**

There is no service layer. The extract scripts ARE the application logic, but they are procedural and not abstracted.

### Gaps Found

#### 4.1 Missing application/use-case layer
Each extract script is a standalone entrypoint with hardcoded dependencies. A service layer would:
- Accept abstract ports (not concrete classes)
- Be testable with fake ports
- Be reusable across different entrypoints (CLI, future web API, tests)

```python
# vault_builder/service_layer/extraction.py
def extract_source(
    source: ScriptureSource,
    renderer: VaultRenderer,
    writer: VaultWriter,
    *,
    books: list[str] | None = None,
) -> ExtractionResult:
    for book in source.read_text():
        if books and book.name not in books:
            continue
        for ch in sorted(book.chapters.values(), key=lambda c: c.number):
            hub_content = renderer.render_hub(ch, book.max_chapter())
            writer.write_hub(ch, hub_content)
    ...
```

The extract scripts become thin entrypoints that construct concrete dependencies and call the service.

#### 4.2 Service functions should accept primitives, not just domain objects
Per Ch. 5 — when calling from CLI or tests, it's easier to pass `book_name: str` than to construct domain objects. The service layer is the right boundary for this translation.

---

## Chapter 6 — Unit of Work

**Relevant to this project: Low**

No database, no transactions. The pattern doesn't map directly.

### Partial applicability

The concept of "safe by default — must explicitly commit" has a weak analogue: the writer could buffer rendered files in memory and only flush to disk on explicit `.commit()`. This would allow dry-run mode and atomic chapter writes. Not a priority, but the pattern is recognizable.

---

## Chapter 7 — Aggregates and Consistency Boundaries

**Relevant to this project: High**

The aggregate structure is mostly right. The gap is enforcement.

### Gaps Found

#### 7.1 Aggregate roots identified but not enforced
`Book` contains `Chapter` objects; `Chapter` contains `Verse` objects; `ChapterNotes` contains `StudyNote` lists. These are the correct aggregate boundaries. But there's no enforcement:

- Adapters modify `chapter.verses` directly (bypasses the aggregate root)
- `ChapterNotes` fields are public lists — any code can append to any list

The fix from 1.2 above (adding `add_verse()`, `add_note()`) addresses this directly.

#### 7.2 `ScriptureSource.read_notes()` yields `ChapterNotes` per chapter — correct
Yielding the aggregate root (not individual `StudyNote` objects) is the right call. No change needed.

#### 7.3 Consider: should `Book.chapters` be protected?
Currently `book.chapters` is a plain public `dict`. If `Book` is truly an aggregate root, callers should go through `book.get_chapter(n)` or `book.add_chapter(chapter)` rather than accessing the dict directly. Low priority, but the boundary is currently soft.

---

## Chapter 12 — CQRS

**Relevant to this project: Low-Medium**

This project is write-heavy (extracting and generating), not a read-heavy query system. Full CQRS doesn't apply.

### Partial applicability

#### 12.1 Read methods on aggregates are already CQRS-adjacent
`sorted_verses()`, `max_chapter()`, `sorted_notes()` are pure query methods with no side effects. This is the command-query separation (CQS) principle at the method level — already correctly applied.

#### 12.2 Rendering is a read path — keep it pure
The renderer already follows this: it receives domain objects and returns strings without mutating anything. Don't add side effects to render methods.

---

## Chapter 13 — Dependency Injection and Bootstrapping

**Relevant to this project: High**

### Gaps Found

#### 13.1 No composition root — dependencies hardcoded in scripts
Each `scripts/extract_*.py` constructs its own dependencies inline:

```python
epub_path = sources_config["osb"]["path"]
source = OsbEpubSource(epub_path)
renderer = ObsidianRenderer()
writer = ObsidianWriter(output_dir)
```

There is no central place that declares "these are the dependencies and here are their defaults." Adding a composition root / bootstrap module would:
- Make swapping implementations trivial (e.g., `DryRunVaultWriter`)
- Make tests constructable without touching scripts
- Centralize configuration (sources.yaml, output paths)

```python
# vault_builder/bootstrap.py
def bootstrap(
    source_name: str,
    output_dir: Path | None = None,
    writer: VaultWriter | None = None,
    renderer: VaultRenderer | None = None,
) -> ExtractionService:
    cfg = load_sources_yaml()
    source = build_source(source_name, cfg)
    return ExtractionService(
        source=source,
        renderer=renderer or ObsidianRenderer(),
        writer=writer or ObsidianWriter(output_dir or DEFAULT_OUTPUT),
    )
```

#### 13.2 No DI in tests — tests presumably rely on real files
Without a bootstrap function that accepts fake overrides, unit tests of orchestration logic require real EPUB/PDF files. With it:

```python
def test_extract_writes_hub_per_chapter():
    source = FakeScriptureSource(books=[make_test_book()])
    writer = FakeVaultWriter()
    service = bootstrap(source_name="fake", writer=writer, source=source)
    service.extract()
    assert len(writer.written_hubs) == expected_chapter_count
```

---

## scripts/ — The Missing Entrypoint Layer

**Relevant to this project: High**

`scripts/extract_*.py` sit outside the DDD system entirely. In Cosmic Python's folder model they map to the **entrypoints** layer — equivalent to Flask route handlers or CLI commands. They should exist, but should be thin.

### Current problem

Each script is simultaneously an entrypoint AND a service layer: it constructs dependencies inline, contains the chapter iteration loop, drives renderer/writer calls, and holds all sample-vs-full logic. There is no seam between "compute what to write" and "write it."

### Target shape (after PER-31 + PER-32)

```python
# scripts/extract_osb.py — what it should look like
if __name__ == "__main__":
    args = parse_args()
    service = bootstrap("osb", output_dir=args.output, sample_only=args.sample)
    result = service.extract()
    print(result.summary())
```

All iteration, construction, and rendering logic moves into `ExtractionService`. Scripts become three-line CLI wrappers. This is PER-35.

### Folder model (target)

```
vault_builder/
  domain/          # Verse, Chapter, Book, StudyNote, …
  ports/           # ScriptureSource, VaultRenderer, VaultWriter
  adapters/
    sources/       # OsbEpubSource, EobEpubSource, …
    obsidian/      # ObsidianRenderer, ObsidianWriter
  service_layer/   # ExtractionService  ← NEW (PER-31)
  bootstrap.py     # composition root   ← NEW (PER-32)
scripts/           # thin CLI entrypoints (PER-35)
```

---

## Epilogue — Getting There From Here

**Relevant to this project: Medium**

The epilogue covers the "strangler fig" pattern for refactoring legacy codebases. Not directly applicable since this codebase isn't legacy, but the advice is relevant for sequencing:

- Don't rewrite everything at once
- Start by identifying use cases (each extract script = one use case)
- Extract one service function, test it with fakes, then move on
- The aggregate mutation changes (Ch 1/7) are the highest-leverage starting point

---

## Prioritized Improvement List — ALL COMPLETE (2026-03-31)

| # | Linear | Chapter | Change | Status |
|---|--------|---------|--------|--------|
| 1 | PER-26 | Ch 1/7 | Freeze value objects (`frozen=True`) | ✅ Done |
| 2 | PER-27 | Ch 1/7 | Add `add_verse()` / `add_note()` to aggregates | ✅ Done |
| 3 | PER-28 | Ch 1 | Add `VerseRef` value object | ✅ Done |
| 4 | PER-29 | Ch 2 | Add `FakeScriptureSource` + `FakeVaultWriter` | ✅ Done |
| 5 | PER-30 | Ch 2 | Add `VaultWriter` port (ABC) | ✅ Done |
| 6 | PER-31 | Ch 4/13 | Extract `ExtractionService` layer | ✅ Done |
| 7 | PER-32 | Ch 13 | Add `bootstrap.py` composition root | ✅ Done |
| 8 | PER-35 | Ch 4/13 | Refactor `scripts/` to thin entrypoints | ✅ Done |
| 9 | PER-33 | Ch 1 | Add domain exceptions (`DuplicateVerseError`, etc.) | ✅ Done |
| 10 | PER-34 | Ch 7 | Protect `Book.chapters` via `MappingProxyType` | ✅ Done |

---

## What Does NOT Apply

- **Unit of Work (Ch 6):** No database, no transactions needed.
- **Event Bus / Message Bus (Ch 8–11):** Single-process pipeline, no async event dispatch needed.
- **ORM mapping (Ch 2):** No persistence layer — domain objects are transient by design.
- **CQRS read models (Ch 12):** Not a query-heavy system; CQS at the method level is sufficient.
