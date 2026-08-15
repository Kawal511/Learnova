# 🎓 Learnova — AI Presentation Transformation Engine

> Transforms text-heavy PPTs and PDFs into modern, visually engaging, presentation-ready decks.
> Flowcharts, timelines, comparison tables, KPI cards, SmartArt and interleaved quizzes —
> fully programmatic, with optional Groq / NVIDIA NIM / Gemini AI integration.

---

## 🚀 What it does

1. **Ingest** a `.pptx`, a `.pdf`, or a typed syllabus.
2. **Convert to Markdown** via AnyDoc — one intermediate representation for all
   three inputs. Images are extracted separately and **anchored back to the
   section that discusses them**.
3. **Review & edit** that markdown before anything expensive runs.
4. **Chunk** on `##` heading boundaries, so slides break at semantic seams.
5. **Classify layout** per chunk (flowchart / table / metric / card grid / minimal text).
6. **Plan visuals deterministically** — detect real flowcharts, comparison
   tables and KPI callouts from the text itself, with no LLM.
7. **Enhance** — examples, analogies and revision points from `enhancement/`.
8. **Apply text density** — low / medium / heavy, paginating overflow onto
   numbered continuation slides so nothing is dropped.
9. **Generate quizzes** and interleave them as checkpoint slides.
10. **Score** engagement quality per slide.
11. **Export** an animated `.pptx` and an interactive Reveal.js web deck.

### Where the visuals come from

A typed syllabus has no images or charts, so structure is its only source of
visual richness. `pipeline/visual_planner.py` runs the (previously unused)
`intelligence` + `visual_specs` engines over each chunk and emits a real
layout:

| Detected in the text | Becomes |
|---|---|
| 3+ ordered steps / a described process | **Flowchart** with real nodes, edges and start/end shapes |
| 3+ dated or chronological events | **Timeline** flow |
| An explicit A-vs-B comparison | **Comparison table** (skipped if the extraction is low quality) |
| 2+ numeric findings | **Metric callout** using the actual figure, e.g. `47%` |
| 3+ distinct key concepts | **Card grid** |

This only overrides the layout router when the router produced nothing
structural, or produced a recognisable placeholder (a flowchart with no node
data, or a metric literally labelled `Key Stat`). A genuine LLM result is left
alone.

---

## 🏗️ Architecture

```
              ┌───────────┐
  PPTX ──┐    │           │
  PDF  ──┼───▶│ Markdown  │──▶ sections ──▶ chunks ──▶ layout ──▶ quizzes ──▶ score
  Typed ─┘    │    IR     │                                                     │
              └───────────┘                                                     ▼
                    ▲                                              PPTX  +  HTML web deck
                    │
              user may edit
```

Everything under `src/learnova/` is **UI-agnostic** — it imports no Streamlit and no FastAPI.
Both frontends call the same `learnova.pipeline.orchestrator`.

---

## 📂 Project structure

```text
learnova/
├── pyproject.toml                 # packaging + pytest config
├── requirements.txt
├── .env.example
│
├── src/learnova/                  # ← the library. No UI imports anywhere.
│   ├── config.py                  # paths, limits, API keys, runtime env flags
│   ├── logging_config.py
│   ├── parsers/
│   │   ├── schema.py              # 8 structured dataclasses (rich view)
│   │   ├── legacy.py              # SlideData / ParsedDocument (flat view, single definition)
│   │   ├── base.py                # BaseDocumentParser ABC
│   │   ├── ppt_parser.py          # PPTX: tables, SmartArt, charts, equations, notes
│   │   ├── pdf_parser.py          # PDF: PyMuPDF text/tables/images + scanned-page render
│   │   └── markdown_converter.py  # ← Markdown IR (AnyDoc) + image anchoring
│   ├── providers/
│   │   ├── base.py                # LLM / Vision / Embedding ABCs
│   │   ├── groq_provider.py
│   │   ├── nvidia_provider.py     # ← NVIDIA NIM over plain REST (no openai SDK)
│   │   ├── gemini_vision.py
│   │   ├── gemini_embedding.py
│   │   └── router.py              # ← LLMRouter: ordered failover on 429/timeouts
│   ├── pipeline/
│   │   ├── orchestrator.py        # ← the 12-stage pipeline, UI-free
│   │   ├── visual_planner.py      # ← deterministic flowchart/table/KPI detection
│   │   ├── density.py             # ← text density + slide continuity/pagination
│   │   ├── enhancer.py            # ← bridges enhancement/ into the runtime
│   │   └── jobs.py                # in-memory async job store for the API
│   ├── auth/clerk.py              # ← Clerk JWT verification against JWKS
│   ├── storage/deck_library.py    # ← per-user saved decks on disk
│   ├── ai/                        # improver, layout_router, quiz_gen, image_describer
│   ├── intelligence/              # zero-LLM concept extraction & transformation planning
│   ├── enhancement/               # pedagogical generators (examples, analogies, mnemonics)
│   ├── visual_specs/              # deterministic visual specification builders
│   ├── rag/                       # chunker, retriever, embedder
│   ├── rendering/                 # themes, PPTX builder, web deck, subprocess isolation
│   └── scoring/                   # engagement scorer
│
├── apps/
│   ├── streamlit_app/             # Streamlit UI (app.py, styles.py, helpers.py)
│   └── api/main.py                # FastAPI REST backend
│
├── frontend/                      # React + Vite SPA (Clerk auth, routing)
│   ├── .env                       # VITE_CLERK_PUBLISHABLE_KEY
│   └── src/
│       ├── pages/                 # Landing · AuthPage · Studio · DeckLibrary
│       └── components/            # Navbar · Footer · Marquee · PalettePicker · …
│
├── scripts/                       # verify_day4.py, verify_day5.py, generate_sample.py
├── tests/                         # pytest suite + conftest.py + fixtures/
└── docs/PROGRESS_README.md
```

---

## ⚙️ Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in whichever keys you have. **All of them are optional** — with no keys at all the
pipeline still produces a deck using heuristic layout classification.

| Key | Used for | Required? |
|-----|----------|-----------|
| `GROQ_API_KEY` | Fast layout classification | No |
| `NVIDIA_API_KEY` | Higher-quality rewriting/quizzes + 429 failover | No |
| `GEMINI_API_KEY` | Image OCR / vision descriptions | No |
| `VITE_CLERK_PUBLISHABLE_KEY` | Sign-in + per-user deck library | For accounts |
| `CLERK_SECRET_KEY` | Reserved for server-side Clerk calls | For accounts |

The frontend reads its Clerk key from **`frontend/.env`** (`VITE_` prefix — Vite
does not expose bare or `NEXT_PUBLIC_` names to the browser). The project-root
`.env` holds the backend copy. Without Clerk configured the API runs in
anonymous single-user mode, so local development still works.

### 3. Run

**Streamlit (single process, simplest):**

```bash
streamlit run apps/streamlit_app/app.py
```

**FastAPI + React (two processes):**

```bash
uvicorn apps.api.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Then open <http://localhost:5173>. Vite proxies `/api` to port 8000, so there is no CORS setup.

---

## 🧪 Tests

```bash
python -m pytest -q
```

208 passed, 7 skipped. The skips need real API credentials or a PDF
fixture; run the credentialed ones deliberately with `pytest -m live`.

Verification scripts (write JSON into `.cache/`):

```bash
python scripts/verify_day4.py
```

```bash
python scripts/verify_day5.py
```

---

## 🔌 API reference

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness + the canonical stage list |
| `GET` | `/api/themes` | Available design themes |
| `POST` | `/api/jobs` | Upload a document → `job_id`; conversion starts |
| `POST` | `/api/jobs/typed` | Create a job from typed text |
| `GET` | `/api/jobs/{id}` | Poll status, stage, progress |
| `GET` | `/api/jobs/{id}/markdown` | Fetch the editable markdown IR |
| `PUT` | `/api/jobs/{id}/markdown` | Save user edits |
| `POST` | `/api/jobs/{id}/generate` | Run the expensive half |
| `GET` | `/api/jobs/{id}/deck` | Slides + quizzes + scores as JSON |
| `GET` | `/api/jobs/{id}/download/pptx` | Download the PPTX |
| `GET` | `/api/jobs/{id}/download/html` | Download the web deck |

The pipeline outlives an HTTP request, so uploads return **202** immediately and the
client polls. The 12 stages map directly onto a progress bar.

---

## 🤖 Provider strategy

`LLMRouter` implements `LLMProvider`, so it drops into any call site that already
accepts one. It tries providers in a task-specific order and falls through on
429 / timeout / 5xx:

| Task | Preferred | Fallback |
|------|-----------|----------|
| Layout classification | Groq (short JSON, high volume) | NVIDIA |
| Content improvement | NVIDIA (larger model) | Groq |
| Quiz generation | NVIDIA (better distractors) | Groq |
| Image description | Gemini Vision | local Tesseract |

**No OpenAI dependency.** NVIDIA NIM is reached with plain `requests` against its
OpenAI-compatible endpoint; the `openai` package is not installed or imported.
NIM reasoning models return chain-of-thought in a separate `reasoning_content`
field, which the provider deliberately ignores so JSON parsing stays clean.

---

## 🖼️ How images are handled

AnyDoc produces **text only**: markdown cannot carry bytes, and AnyDoc exposes
no document model for PDF at all (`to_document` is PPTX-only). So the split is:

- **Text** → AnyDoc, which gives cleaner heading/list structure than flattening
  our own parser output.
- **Image bytes** → always the native parsers, which know the slide or page each
  image came from.

Each extracted image is then **anchored** back onto a markdown section by
`markdown_converter.anchor_assets`, in three escalating steps:

1. exact heading match,
2. word-overlap similarity against the section body,
3. positional fallback.

This is why an image stays with its related content even after the user
deletes or reorders sections in the markdown editor — a plain index mapping
breaks the moment the two documents differ in length.

Layouts other than `MINIMAL_TEXT` fill their content area with cards or tables,
so an anchored image there gets its **own figure slide immediately after** the
slide it belongs to, rather than being dropped or overlapped.

AnyDoc marks embedded pictures with a bare `image.png` line; those placeholders
are stripped, otherwise each one becomes a junk slide.

## 📝 Notes & known limits

- **Retrieval is keyword-based, not vector-based.** `rag/retriever.py` is a
  pure-Python keyword-overlap store. There is no FAISS in this project, and no
  embeddings run in the default pipeline. `ChunkRetriever` is currently built
  and discarded — it exists for future retrieval-augmented stages.
- **AnyDoc does no OCR.** If it returns too little text (a scanned page), the
  native PyMuPDF path takes over, which can render and OCR the page. AnyDoc is
  a required dependency but the pipeline still runs without it.
- **`LLMRouter` is now used by the enhancement stage** but the older AI modules
  (`layout_router`, `quiz_gen`, `diagram_gen`) still construct `GroqProvider()`
  directly, so NVIDIA failover only covers enhancement so far.
- **Enhancement is LLM-backed**, so it is skipped at `low` density, capped at
  the first 12 slides, and degrades to plain slides with no provider.
- **The job store is in-memory and single-process.** Jobs are lost on restart
  and it will not work across multiple uvicorn workers. Fine for a demo.
- PPTX/HTML builds run in a **separate interpreter** (`rendering/subprocess_builder.py`)
  to isolate C-extension state; this is what fixed the exit-139 segfaults.
- The intelligence / enhancement / visual_specs packages are fully tested
  libraries but are **not yet wired into the runtime pipeline** — they are
  reachable from `scripts/verify_day4.py` and `scripts/verify_day5.py`.

---

## 🔐 Accounts & the deck library

Sign-in is handled by **Clerk**. The React app sends Clerk's session JWT as
`Authorization: Bearer …`; the API verifies its RS256 signature against Clerk's
published JWKS. **The user id is never taken from the client** — otherwise
changing a header would expose someone else's decks.

Every generated deck is written to `.data/users/<user_id>/<deck_id>/`
(markdown + PPTX + HTML + metadata) and listed under **My Decks**. Requests for
a deck you don't own return `404`, not `403`, so ids cannot be probed.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/decks` | Your saved decks, newest first |
| `GET` | `/api/decks/{id}/markdown` | The saved markdown |
| `GET` | `/api/decks/{id}/download/{pptx or html}` | Download a saved artifact |
| `DELETE` | `/api/decks/{id}` | Remove a deck |

## 🎨 Palette & typography

The studio exposes a Canva-style picker: **primary**, **secondary** and
**background** colours plus a font pairing, with eight presets and a live
preview. The chosen values travel as a `theme_spec` through the pipeline and the
build subprocess into *both* the PPTX and the web deck.

Remaining roles (card fill, body text, muted text) are derived, and text colour
is picked by WCAG relative luminance — so a dark primary never ends up with
dark text on it.

PPTX embeds a font *name*, so the viewer needs the font installed; each pairing
therefore names a safe fallback. `Arial` and `Georgia` are the safest choices
for decks you will hand to someone else.

---

## Text density & slide continuity

The studio asks one question — **how much text per slide?** — and every limit
derives from it.

| | Low | Medium (default) | Heavy |
|---|---|---|---|
| Bullets per slide | 3 | 5 | 8 |
| Words per bullet | 12 | 20 | 32 |
| Table rows | 4 | 6 | 10 |
| Flowchart steps | 3 | 4 | 6 |
| Enhancement extras | none | 1 | 3 |

**Content is never dropped.** A lighter setting spreads the same material
across more slides, titled `Topic (2/3)` so the run reads as one continuous
thought. Only the last part carries the takeaway; only the first keeps the
figure. `METRIC` and `QUIZ` slides are never split.

Full rule list: **[docs/PPT_RULES.md](docs/PPT_RULES.md)** — every rule applied
between raw input and finished deck, in execution order.
