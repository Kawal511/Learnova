# Rules applied during PPT creation

Every rule the pipeline enforces between raw input and a finished deck, in the
order it runs. Anything not listed here is not enforced.

---

## 1. Ingestion

| Rule | Detail |
|---|---|
| Accepted inputs | `.pptx`, `.pdf`, or typed text |
| Size ceiling | 50 MB (`MAX_FILE_SIZE_MB`); larger uploads are rejected with `413` |
| Text extraction | AnyDoc first; native PyMuPDF / python-pptx parsers on failure |
| Scanned pages | AnyDoc does no OCR. Under 200 characters of output, the native parser takes over so the page can be rendered and OCR'd |
| Multi-column PDFs | Detected from block x-spread on the first 4 pages. AnyDoc has no column awareness and interleaves the columns into nonsense, so these route to the native parser, which sorts blocks per column before reading |
| Reading order | Full-width blocks keep their vertical position; column blocks are read left column fully, then right |
| Image extraction | Always native — markdown cannot carry bytes, and AnyDoc has no document model for PDF |
| Image placeholders | AnyDoc's bare `image.png` lines are stripped; left in, each becomes a junk slide |
| Caching | Markdown is cached by SHA-256 of file bytes; re-running the same file skips conversion |

## 2. Sectioning

| Rule | Detail |
|---|---|
| Slide boundary | A `##` heading (level 2 or shallower) starts a new slide |
| Deeper headings | `###` and below stay inside their parent section |
| Pre-heading content | Text before the first heading becomes its own leading section |
| Typed input | Gets a synthetic `##` heading if none is present, so sectioning has an anchor |
| Junk headings | A "heading" that ends on an operator with `=`, is <40% letters, repeats one word (`Conclusion: Conclusion:`), or runs past 12 words is demoted to body text. PDF extractors promote formula fragments, which make useless titles |
| Residual markers | `#` prefixes are stripped from body lines, which otherwise rendered as literal `### Topic` bullet text |
| Missing titles | A section titled only `Page 10` inherits the previous real heading |
| Repeated headings | Consecutive sections sharing a title merge into one topic, capped at 1800 characters so a whole chapter cannot collapse into one overloaded slide |

## 3. Chunking

| Rule | Detail |
|---|---|
| List runs | Consecutive markdown list items stay together and keep their line breaks |
| List markers | `-`, `*`, `+`, `1.`, `2)` are stripped from the text |
| Prose | Consecutive non-list lines collapse into a single paragraph |
| Tables | `[TABLE DATA]` blocks are never split mid-row |
| Long paragraphs | Split at 180 words; a paragraph under that is passed through verbatim so line structure survives |
| Images | Attached to the **first** chunk of a unit only — otherwise the renderer emits one duplicate figure slide per paragraph |
| One section, one slide | Chunks of a section are merged back before rendering. Without this, a 22-paragraph section became 22 near-empty slides sharing one title |
| Sentence splitting | Prose splits on `.!?` only when the period is not a decimal (`3.14`), a single initial (`J. Smith`), or a known abbreviation (`no.`, `fig.`, `vs.`). Splitting naively turned "Total no. of observations" into two meaningless bullets |

## 4. Image anchoring

An image is matched to the section that discusses it, in escalating order:

1. **Exact heading match** against the source slide/page title
2. **Word-overlap similarity** ≥ 0.25 against the section body
3. **Positional fallback** — same ordinal index

This survives the user deleting or reordering sections in the markdown editor.
A plain index mapping does not.

## 5. Layout classification

Each chunk is assigned exactly one layout:

| Layout | Chosen when |
|---|---|
| `FLOWCHART` | Process/step/sequence language detected |
| `TABLE` | Real pipe-delimited rows are present, **or** a whole-word comparison cue (`vs`, `versus`, `comparison`, `difference between`). Substring matching previously routed any text containing "table" or the letters "vs" to a table |
| `METRIC` | Percentages or quantities detected |
| `CARD_GRID` | Several distinct parallel concepts |
| `MINIMAL_TEXT` | Everything else |

The LLM router runs first; on failure (bad key, quota, timeout) a keyword
heuristic produces the same shape. **Neither path truncates content** — bullet
budgets are applied later, by the density stage.

**No fabricated tables.** If a slide is classified `TABLE` but no real rows can
be parsed from the text, it is downgraded to `MINIMAL_TEXT`. The old fallback
invented a one-row `Item / Description` grid, which looked broken on a slide.
Likewise a table continuation page that has run out of rows becomes
`MINIMAL_TEXT`, since a table branch with nothing to draw rendered blank.

## 6. Deterministic visual planning

Overrides the router only when it produced nothing structural
(`MINIMAL_TEXT` / `CARD_GRID`) or a recognisable placeholder (a flowchart with
no node data, a metric literally labelled `Key Stat`). A genuine LLM result is
left alone.

| Detected | Becomes | Threshold |
|---|---|---|
| Ordered steps / process | Flowchart with real nodes, edges, start/end shapes | ≥ 3 steps |
| Chronological events | Timeline flow | ≥ 3 events |
| A-vs-B comparison | Comparison table | ≥ 1 valid pair |
| Numeric findings | Metric callout using the real figure | ≥ 2 statistics |
| Distinct concepts | Card grid | ≥ 3 concepts |

**Comparison quality gate** — a table is skipped, and the slide falls back to
bullets, when either side is empty, either cell exceeds 38 characters
(a truncated run-on), or the aspect is a bare connector (`vs`, `and`, `than`).
Shipping a malformed table is worse than shipping a clean list.

## 7. Enhancement (optional, LLM-backed)

Adds examples, analogies, real-world applications, common mistakes and revision
points.

| Rule | Detail |
|---|---|
| Skipped entirely | At `low` density, or with no LLM provider configured |
| Slide cap | First 12 slides only — each costs six sequential LLM calls |
| Quiz slides | Never enhanced |
| Failure | One slide failing yields an empty result, never a failed run |
| Selection order | Example → Analogy → In practice → Watch out → Recall (one per category, for variety) |

## 8. Text density and continuity

The user picks one setting; every limit derives from it.

| | Low | Medium (default) | Heavy |
|---|---|---|---|
| Bullets per slide | 3 | 5 | 8 |
| Words per bullet | 12 | 20 | 32 |
| Characters per bullet | 90 | 140 | 220 |
| Table rows per slide | 4 | 6 | 10 |
| Flowchart steps per slide | 3 | 4 | 6 |
| Card-grid cards | 3 | 4 | 4 |
| Enhancement extras | none | 1 | 3 |

**Continuity rules**

- Content is **never truncated away**. Overflow moves to a continuation slide.
- A slide is never split mid-bullet.
- Continuation slides are titled `Topic (2/3)` so the run reads as one topic.
- Only the **final** part carries the takeaway bar, so the conclusion lands once.
- Only the **first** part keeps the figure, so images are not duplicated.
- Over-long bullets are trimmed at a **clause boundary** (`,` `;` `:` `—`)
  where one exists in the last half, so the result still reads as a sentence.

**Atomic layouts** — `METRIC` and `QUIZ` are never split; they lose their
meaning when broken across slides.

**Per-layout splitting**

- **Table** — rows are paginated, the header repeats on every part. Lead-in
  bullets paginate alongside them rather than being capped; capping deleted
  content, which the continuity contract forbids.
- **Flowchart** — split into stages, never mid-step. Each continuation gets a
  rebuilt Mermaid chain for just its own steps, rather than reusing the
  whole-diagram code.
- **Text / card grid** — bullets paginate; enhancement extras append first so
  they participate in the same budget.

## 9. Quizzes

Checkpoints are rendered **inline, at the foot of the slide that closes the
run** — not as separate slides. A question reads better beside the material it
tests, and the deck no longer inflates with interruptions (a 12-slide deck used
to become 15).

| Rule | Detail |
|---|---|
| Frequency | Attached after every N slides (user-set, 2–6) |
| Placement | A band above the takeaway bar: question line, then four options in a single row |
| Options | Capped at four; a model-supplied `A)` prefix is stripped so letters are not doubled |
| Slide count | Unchanged — inline quizzes add no slides |
| Body area | The content band shrinks by the quiz band height, so nothing overlaps |
| Source | Generated from the improved slide content |
| Failure | An empty quiz list never costs the deck |
| Separate slides | Still available via `interleave_quizzes_into_slides(..., inline=False)` |

## 10. Theme, palette and typography

| Rule | Detail |
|---|---|
| Custom palette | User picks primary, secondary and background; it overrides any named theme |
| Derived roles | Card fill, body text and muted text are computed, not asked for |
| Text contrast | Chosen by WCAG relative luminance (threshold 0.45) — a dark primary never gets dark text |
| Invalid hex | Falls back to a default rather than raising |
| Fonts | A heading/body pairing applied to both PPTX and web deck |
| PPTX font rule | Bold runs, or runs ≥ 24 pt, get the display face; everything else gets the body face |
| Font portability | PPTX embeds a font *name*, not the file — the viewer needs it installed. `Arial` and `Georgia` pairings are the safe choices |

## 11. Rendering

| Rule | Detail |
|---|---|
| Slide size | 13.33 × 7.5 in (16:9) |
| Structure | Title slide → content slides → closing slide |
| Header band | 0 → 1.1 in, filled with the primary colour |
| Content band | **Computed per slide**, not fixed: starts at 1.35 in and ends above whichever of the takeaway bar and quiz band are present |
| Takeaway bar | 1.05 in tall at the foot, only when takeaway text exists |
| Quiz band | 2.05 in, directly above the takeaway bar, only when a checkpoint is attached |
| Figure slides | An image on a non-`MINIMAL_TEXT` layout gets its own slide immediately after, since those layouts fill their content band |
| Transitions | OpenXML push transition on every slide |
| Isolation | PPTX and HTML are built in a **separate interpreter** to contain C-extension state |
| Build failure | Degrades to an in-process build; a failed artifact never fails the whole run |

### Dynamic sizing

Boxes and cards are measured from their content rather than being fixed
rectangles, so short text no longer floats in a mostly empty box and long text
no longer spills past the edge.

| Rule | Detail |
|---|---|
| Font fitting | The largest size at which the text fits is chosen, stepping down in half-points |
| Legibility floor | Body stops at 11 pt, cards at 9 pt. Below that the content is paginated instead of shrunk further |
| Ceilings | Body 22 pt, cards 18 pt, slide title 28 pt (title floors at 15 pt) |
| Uniform sizing | All cards in a row share one size — the smallest that fits any of them — so the row reads evenly |
| Card grids | Wrap past 4 per row and use the vertical space; the last row is balanced (5 items become 3+2, not 4+1) |
| Text + image | The body splits into a text column and a 38% image column; with no image the text takes the full width |
| Measurement | An estimate (0.52 × point size per glyph, 1.28 line height), deliberately conservative so the error lands on "slightly small" rather than "overflowing". PowerPoint does the final shaping |

## 12. Ownership and persistence

| Rule | Detail |
|---|---|
| Identity | Taken from a verified Clerk JWT, never from a client-supplied header |
| Storage | `.data/users/<user_id>/<deck_id>/` — markdown, PPTX, HTML, metadata |
| Isolation | A deck belonging to another user returns **404, not 403**, so ids cannot be probed |
| Path safety | User and deck ids must match `^[A-Za-z0-9_\-]{1,128}$`; traversal attempts raise |
