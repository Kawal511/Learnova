# 🎓 Learnova — Production Sprint Progress & Architecture Documentation

## 📌 Executive Summary

Learnova is an AI-powered presentation transformation platform designed to take ordinary, text-heavy, unstructured `.pptx` presentations and `.pdf` textbooks and transform them into modern, visually engaging, presentation-ready decks.

This document details the architecture, design decisions, and progress completed across **Days 1–4** of the production sprint.

---

## 📅 Sprint Progress Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LEARNOVA SPRINT MATRIX                          │
├─────────┬──────────────────────────────────┬───────────────────────────┤
│ Phase   │ Module                           │ Status                    │
├─────────┼──────────────────────────────────┼───────────────────────────┤
│ Day 1–3 │ Unified Extraction Engine        │ ✅ Complete                │
│ Day 4   │ Intelligent Content Understanding│ ✅ Complete (Today)       │
│ Day 5   │ Layout & Content Generation      │ ⏳ Up Next                 │
│ Day 6+  │ Export & Interactive Web Decks   │ 📅 Scheduled              │
└─────────┴──────────────────────────────────┴───────────────────────────┘
```

---

## 🏛 Architecture Stack (Days 1–4)

```
                            INPUT DOCUMENT (.pptx / .pdf)
                                          │
                                          ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ UNIFIED EXTRACTION LAYER (Days 1–3)                                     │
   │ - PPTX & PDF Parsers (PyMuPDF, python-pptx)                              │
   │ - Text frames, paragraphs, bold/italic, font sizes, bullet levels        │
   │ - Native PowerPoint tables & grids                                       │
   │ - Embedded images (SHA-256 hashed VisualAssetElements)                   │
   │ - Native charts, alt-text, series data                                   │
   │ - SmartArt & diagram XML text nodes                                      │
   │ - OMML math equations → EquationElements                                 │
   │ - Output: DocumentEntity & SlidePageEntity Graph                          │
   └──────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ INTELLIGENT CONTENT UNDERSTANDING ENGINE (Day 4)                         │
   │ package: intelligence/                                                   │
   │                                                                          │
   │ ┌────────────────────────┐  ┌────────────────────────┐                   │
   │ │ 20 Responsibilities    │  │ 18 Presentation        │                   │
   │ │ Heuristic Extractor    │  │ Intents Classifier     │                   │
   │ └───────────┬────────────┘  └───────────┬────────────┘                   │
   │             │                           │                                │
   │ ┌───────────▼────────────┐  ┌───────────▼────────────┐                   │
   │ │ Text Block             │  │ 16 Visual Opportunity  │                   │
   │ │ Prioritizer            │  │ Detector + Rationale   │                   │
   │ └───────────┬────────────┘  └───────────┬────────────┘                   │
   │             │                           │                                │
   │             └─────────────┬─────────────┘                                │
   │                           ▼                                              │
   │             ┌──────────────────────────┐                                 │
   │             │ Complexity Scorer        │                                 │
   │             │ (0.0–10.0 & 4 Levels)    │                                 │
   │             └─────────────┬────────────┘                                 │
   │                           │                                              │
   │                           ▼                                              │
   │             SlideIntelligence Graph Object                               │
   └──────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                         DOWNSTREAM GENERATION (Day 5+)
```

---

## 🧩 Module Breakdown

### 1. Unified Extraction Layer (`parsers/`) — Days 1–3
Constructs a strongly-typed document graph (`DocumentEntity`, `SlidePageEntity`):
- `TextBlockElement`: Captures text runs, heading status, font sizes, bold/italic flags, and bullet depth.
- `TableElement`: Extracts grid matrices, row headers, merged cells, and spatial bounding boxes.
- `VisualAssetElement`: Extracts embedded images with SHA-256 deduplication and dimensions.
- `StructuredChartElement`: Extracts chart categories, series data, titles, and alt-text.
- `DiagramElement`: Extracts SmartArt and diagram raw XML text nodes.
- `EquationElement`: Converts OMML math nodes into LaTeX and ASCII expressions.

### 2. Intelligent Content Understanding Engine (`intelligence/`) — Day 4
A pure Python, zero-LLM, heuristic intelligence engine that analyzes extracted `SlidePageEntity` objects and populates a rich, structured `SlideIntelligence` object per slide.

#### Key Modules in `intelligence/`:

| Module | File Link | Role |
|---|---|---|
| **Data Schema** | [`intelligence/schema.py`](file:///Users/swayampanchal/Desktop/New%20Learnova/Learnova/intelligence/schema.py) | Strongly-typed dataclasses: `SlideIntelligence`, `PresentationIntent` (18 intents), `TextPriority` (6 categories), `VisualOpportunityType` (16 types), `ComplexityLevel`, `ConceptRelationship`, `PrioritizedTextBlock`, and `VisualOpportunity`. |
| **Concept Extractor** | [`intelligence/concept_extractor.py`](file:///Users/swayampanchal/Desktop/New%20Learnova/Learnova/intelligence/concept_extractor.py) | Pure-heuristic extraction of all 20 slide responsibilities. |
| **Content Classifier** | [`intelligence/content_classifier.py`](file:///Users/swayampanchal/Desktop/New%20Learnova/Learnova/intelligence/content_classifier.py) | Multi-intent classifier supporting 18 presentation intents using keyword signals combined with structural evidence. |
| **Text Prioritizer** | [`intelligence/text_prioritizer.py`](file:///Users/swayampanchal/Desktop/New%20Learnova/Learnova/intelligence/text_prioritizer.py) | Categorizes text blocks into `High`, `Medium`, `Low`, `Decorative`, `Redundant`, and `Repeated`. |
| **Visual Opportunity Detector** | [`intelligence/visual_opportunity.py`](file:///Users/swayampanchal/Desktop/New%20Learnova/Learnova/intelligence/visual_opportunity.py) | Detects opportunities to upgrade text into 16 visual types (Flowchart, Timeline, Comparison Table, KPI Cards, Icon Grid, etc.) with explicit rationale and confidence scores. |
| **Complexity Scorer** | [`intelligence/complexity_scorer.py`](file:///Users/swayampanchal/Desktop/New%20Learnova/Learnova/intelligence/complexity_scorer.py) | Computes a weighted 0.0–10.0 score based on vocab richness, sentence length, tech term density, equations/tables, and bullet depth. |
| **Engine Orchestrator** | [`intelligence/engine.py`](file:///Users/swayampanchal/Desktop/New%20Learnova/Learnova/intelligence/engine.py) | Orchestrator exposing `SlideIntelligenceEngine.analyze_slide()` and `analyze_document()`. |

---

## 🔍 The 20 Slide Responsibilities

The engine extracts and structures the following 20 responsibilities for every slide:

1. **Main Topic**: Slide title or primary heading.
2. **Learning Objective**: Action-oriented goal sentences ("understand", "able to").
3. **Key Concepts**: Core bold terms, main headings, and title concepts.
4. **Supporting Concepts**: Sub-topics and non-heading conceptual text.
5. **Definitions**: Term-to-definition mappings ("X is defined as Y", "X: Y").
6. **Important Facts**: High-yield factual statements flagged by importance keywords.
7. **Numbers & Statistics**: Percentages, currencies, numerical benchmarks with context.
8. **Processes**: Sentences describing mechanisms, procedures, or workflows.
9. **Comparisons**: Side-by-side comparative structures ("vs", "compared to", table rows).
10. **Cause & Effect**: Causal relationships ("because", "therefore", "leads to").
11. **Chronology**: Temporal sequences, explicit dates, and ordinal items.
12. **Advantages**: Benefits, pros, strengths, and upside callouts.
13. **Disadvantages**: Drawbacks, limitations, risks, and downside callouts.
14. **Steps**: Sequenced procedural items ("1.", "Step 1", "Phase 1").
15. **Examples**: Illustrative instances ("for example", "e.g.", "such as").
16. **Formulas**: Mathematical/scientific equations (LaTeX & ASCII).
17. **Lists**: Structured bullet groups and table matrix columns.
18. **FAQs**: Question-and-answer pairs ("What is...", "Q&A").
19. **Concept Relationships**: Semantic triples (subject → predicate → object).
20. **Complexity Level**: 0.0–10.0 score mapped to Introductory, Intermediate, Advanced, Expert.

---

## 🧪 Runtime Verification

To run verification against any presentation file:

```bash
python3 verify_day4.py sample_test_presentation.pptx
```

### Sample Output Verification:
```text
=== Parsing Document: sample_test_presentation.pptx ===
Document ingested: sample_test_presentation.pptx with 5 slides.

=== Running Intelligent Content Understanding Engine ===
Successfully analyzed 5 slides.

[Slide 1] 'Artificial Intelligence in Education' | Topic: Artificial Intelligence in Education | Intents: Architecture | Complexity: 3.1 (Intermediate) | Visual Opps: 0
[Slide 2] 'Key Challenges in Higher Education' | Topic: Key Challenges in Higher Education | Intents: Problem, Checklist | Complexity: 3.4 (Intermediate) | Visual Opps: 3
[Slide 3] 'Learnova Automated Processing Pipeline Workflow' | Topic: Learnova Automated Processing Pipeline Workflow | Intents: Workflow, Process, Table | Complexity: 3.4 (Intermediate) | Visual Opps: 3
[Slide 4] 'Student Engagement Benchmark Metrics' | Topic: Student Engagement Benchmark Metrics | Intents: Checklist | Complexity: 4.0 (Intermediate) | Visual Opps: 2
[Slide 5] 'Four Pillars of Learnova Architecture' | Topic: Four Pillars of Learnova Architecture | Intents: Workflow, Checklist, Definition | Complexity: 4.4 (Intermediate) | Visual Opps: 5
```

---

## 🚀 Next Steps (Day 5+)

- **Dynamic Layout Generator**: Map `primary_intent` and `suggested_visualizations` to structured visual slide templates.
- **Smart Content Summarizer**: Use `prioritized_text` to compress medium/low text while preserving high-priority concepts.
- **Visual Asset Synthesizer**: Render Mermaid diagrams, KPI callout cards, and comparison matrices based on `visual_opportunities`.
