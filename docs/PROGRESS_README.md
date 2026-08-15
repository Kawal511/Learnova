# 🎓 Learnova — Production Sprint Progress & Architecture Documentation

## 📌 Executive Summary

**Learnova AI** is an AI-powered presentation transformation platform designed to take ordinary, text-heavy, unstructured `.pptx` presentations and `.pdf` textbooks and transform them into modern, visually engaging, presentation-ready decks with flowcharts, tables, metric callouts, and interactive web decks.

---

## 📅 Day-by-Day Sprint Progress (Days 1–8)

### 🚀 Day 1 – Project Planning & Research
- Finalized the project core concept: **Learnova AI**.
- Defined the problem statement: converting boring, text-heavy slides and PDFs into modern visual presentations.
- Researched existing presentation tools and identified critical gaps (lack of structural process diagrams, dynamic quizzes, and automated layout routing).
- Planned the overall modular architecture and processing workflow.

### ⚙️ Day 2 – Project Setup & Environment
- Created the core project directory structure and modular package layout (`parsers/`, `rag/`, `ai/`, `providers/`, `utils/`, `intelligence/`, `enhancement/`, `visual_specs/`).
- Set up the development environment and virtual environment (`venv`).
- Integrated core dependencies (`python-pptx`, `PyMuPDF`, `google-genai`, `groq`, `streamlit`, `altair`, `pandas`, `PIL`, `tesseract`).
- Initialized Git repository and established version control standards.

### 📊 Day 3 – PPT Parsing Engine
- Developed the PowerPoint extraction parser (`parsers/ppt_parser.py`).
- Extracted slide text, titles, body paragraphs, bullet points, font metrics, and formatting.
- Extracted shapes, native PowerPoint tables, SmartArt diagrams, OMML math equations, and embedded images.
- Standardized slide output into structured dataclass format (`SlideData` and `ParsedDocument`).

### 📄 Day 4 – PDF Parsing & Unified Pipeline
- Added full PDF ingestion support (`parsers/pdf_parser.py`).
- Extracted text blocks, headings, font sizes, embedded visual assets (with SHA-256 deduplication), and PyMuPDF native tables (`find_tables`).
- Implemented full-page rendered fallback for image-only or scanned textbook pages.
- Unified PPT and PDF extraction under a single, common `BaseDocumentParser` interface.

### 🧠 Day 5 – Intelligent Content Understanding Engine
- Built the zero-LLM heuristic content intelligence engine (`intelligence/`).
- Extracted 20 slide responsibilities (Topics, Definitions, Statistics, Steps, Comparisons, Timelines, Cause & Effect, FAQs, Formulas, etc.).
- Classified presentation intent across 18 distinct intent types (`Workflow`, `Process`, `Table`, `Checklist`, `Definition`, etc.).
- Evaluated slide complexity (0.0–10.0 scale) and mapped text prioritization (`High`, `Medium`, `Low`, `Redundant`).

### 🔄 Day 6 – Content Transformation Logic & Summarization
- Designed transformation planning rules (`enhancement/` and `ai/improver.py`):
  - Summarize lengthy body paragraphs while retaining core learning objectives.
  - Convert structured procedural text into process sequences and flowcharts.
  - Map data matrices into structured tables and KPI metric cards.
  - Action planning per block: `KEEP`, `SUMMARIZE`, `MOVE_TO_VISUAL`, `MOVE_TO_NOTES`.

### 🎨 Day 7 – Layout & Design System Planning
- Planned the visual slide generation and styling engine (`utils/theme_engine.py` & `visual_specs/`).
- Designed 10 curated design themes (e.g., *Brutalist Neon*, *Midnight Cyber*, *Emerald Academic*, *Swiss Corporate Minimalist*, *Sunset Editorial*).
- Created visual specifications for 15 visual structures (Flowchart, Comparison Table, Matrix, Timeline, KPI Cards, Icon Grid, Mindmap, SmartArt, AI Image Prompts).
- Implemented responsive typography and color palette standards.

### ⚡ Day 8 – Current Progress & Thread-Safe Architecture
- Integrated interactive Web Decks (`Reveal.js` + `Mermaid.js`) and PowerPoint OpenXML transition animation engine.
- Implemented thread-safe subprocess execution (`rendering/subprocess_builder.py` + `rendering/build_worker.py`) to isolate PPTX and HTML compilation, resolving macOS C-extension memory conflicts.
- Built instant fallback from Gemini Vision OCR to local Tesseract OCR on API 429 quota exhaustion.
- Automated MCQ quiz generation (`ai/quiz_gen.py`) and interleaved knowledge check slides into presentations.

### 🧱 Day 9 – Architecture Restructure & Multi-Frontend

- Moved the codebase to a `src/learnova/` package layout; the library now imports
  **no UI framework at all**. Entry points live under `apps/`.
- Extracted the 8-stage pipeline out of the 706-line `app.py` into
  `learnova/pipeline/orchestrator.py`, so Streamlit, FastAPI and the tests all
  drive one code path.
- Introduced a **Markdown intermediate representation**: PPTX, PDF and typed
  syllabus input all converge on markdown, which the user can edit before
  generation. Chunking now happens on `##` heading boundaries instead of
  fixed-size word windows.
- Added `NvidiaProvider` (NVIDIA NIM over plain REST — no `openai` package) and
  `LLMRouter`, which fails over between providers on 429 / timeout / 5xx.
- Added a **FastAPI backend** with an async job store, and a **React + Vite
  frontend** that polls stage progress and offers an editable markdown pane.
- Removed duplicated `SlideData` / `ParsedDocument` definitions, corrected the
  false "FAISS index" claims (retrieval is keyword-based), and fixed
  `generate_sample.py`, which had a hardcoded macOS path and a missing function.

---

## 📊 Overall Progress Matrix

| Module / Goal | Status |
|---|---|
| **Project Architecture & Setup** | ✅ Complete |
| **PowerPoint Parsing Engine** | ✅ Complete |
| **PDF Extraction Engine** | ✅ Complete |
| **Intelligent Content Understanding** | ✅ Complete |
| **Content Summarization & Transformation** | ✅ Complete |
| **Thread-Safe Subprocess PPTX/HTML Builders** | ✅ Complete |
| **Interleaved Quiz Checkpoints** | ✅ Complete |
| **UI-Agnostic Pipeline Orchestrator** | ✅ Complete |
| **Markdown Intermediate Representation** | ✅ Complete |
| **Multi-Provider Failover (Groq / NVIDIA)** | ✅ Complete |
| **FastAPI Backend + React Frontend** | ✅ Complete |
| **AnyDoc Markdown Conversion + Image Anchoring** | ✅ Complete |
| **Deterministic Visual Planning (flowchart/table/KPI)** | ✅ Complete |
| **Automatic Slide Generation & Visual Synthesis** | ✅ Complete |
| **Wiring `intelligence/` + `visual_specs/` into runtime** | ✅ Complete |
| **Wiring `enhancement/` into runtime** | ✅ Complete |
| **Text density (low/medium/heavy) + slide continuity** | ✅ Complete |
| **Activating LLMRouter / NVIDIA failover in the AI modules** | ⬜ Not started |

---

### 🖼️ Day 10 – AnyDoc, Image Anchoring & Visual Synthesis

- Adopted **AnyDoc** (`firecrawl-anydoc`) as the primary markdown converter. It
  ships an `abi3` wheel, so it installs on CPython 3.10+ including 3.13 on
  Windows. The native parsers remain the fallback and the only OCR path.
- Split responsibilities: AnyDoc supplies **text**, the native parsers supply
  **image bytes** (AnyDoc has no document model for PDF, and markdown cannot
  carry bytes anyway).
- Built **image anchoring** — each extracted image is matched back to the
  markdown section that discusses it by exact heading, then word-overlap
  similarity, then position. Verified to survive section deletion *and*
  reordering, which a positional mapping cannot.
- Images on non-`MINIMAL_TEXT` layouts now get their **own figure slide**
  directly after the slide they belong to, instead of being silently dropped.
- Added `pipeline/visual_planner.py`, which finally puts `intelligence/` and
  `visual_specs/` to work: ordered steps become **real flowcharts** (proper
  nodes, edges, start/end shapes, generated Mermaid), statistics become metric
  callouts with the actual figure, comparisons become tables. This is what
  gives a **typed syllabus** visual structure despite having no images.
- Fixed three bugs found along the way: the chunker attached a unit's image to
  *every* one of its chunks (producing duplicate figure slides); AnyDoc's bare
  `image.png` placeholder lines became junk slides; and the flowchart fallback
  emitted a hardcoded three-node placeholder instead of the real steps.

---

### 📐 Day 11 – Density, Continuity & Enhancement

- Wired `enhancement/` into the pipeline via `pipeline/enhancer.py`, which
  rebuilds the `SlideIntelligence` + `TransformationPlan` pair the engine needs.
  It is skipped at low density, capped at 12 slides, and degrades to plain
  content when no provider is configured.
- Added **text density** (`low` / `medium` / `heavy`) driving bullet counts,
  word budgets, table rows, flowchart steps and enhancement volume.
- Added **slide continuity**: overflow paginates onto numbered continuation
  slides (`Topic (2/3)`) instead of being truncated. Takeaway appears only on
  the final part; the figure only on the first. `METRIC` and `QUIZ` are atomic.
- Fixed a content-loss bug: the layout router's fallback capped bullets at five,
  deleting user content before the density stage could paginate it.
- Documented every creation rule in `docs/PPT_RULES.md`.
- Landing page: hover/focus motion on all buttons and cards, and **all emoji
  removed** app-wide (replaced with numbered marks and CSS rules).

---

## 🎯 Next Milestones

1. **Activate `LLMRouter`** in the four AI modules that currently construct
   `GroqProvider()` directly, so NVIDIA failover actually takes effect.
2. **Persistent job store**: the current one is in-memory and single-process.
3. **End-to-End Bulk Generation**: multi-document batch processing.
