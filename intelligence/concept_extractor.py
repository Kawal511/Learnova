"""
Learnova Intelligence Layer — Concept Extractor
================================================
Performs pure-heuristic extraction of all 20 slide responsibilities
from a SlidePageEntity with NO LLM calls, NO external API dependencies.

Responsibilities extracted:
 1.  Main Topic
 2.  Learning Objective
 3.  Key Concepts
 4.  Supporting Concepts
 5.  Definitions
 6.  Important Facts
 7.  Numbers & Statistics
 8.  Processes
 9.  Comparisons
 10. Cause & Effect
 11. Chronology
 12. Advantages
 13. Disadvantages
 14. Steps
 15. Examples
 16. Formulas
 17. Lists
 18. FAQs
 19. Relationships between concepts
 20. Complexity Level (raw signals — scored in complexity_scorer.py)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from parsers.schema import (
    DiagramElement,
    EquationElement,
    SlidePageEntity,
    TextBlockElement,
)
from intelligence.schema import ConceptRelationship, RelationshipType


# ─────────────────────────────────────────────────────────────────────────────
# Compiled regex patterns (module-level for performance)
# ─────────────────────────────────────────────────────────────────────────────

# Numbers: integers, decimals, percentages, large units, currency
_RE_NUMBERS = re.compile(
    r"""
    (?:
        \$[\d,]+(?:\.\d+)?              |  # currency: $1,200.50
        \d+(?:\.\d+)?\s*%               |  # percentages: 42%, 3.5%
        \d+(?:,\d{3})+(?:\.\d+)?        |  # comma-formatted: 1,000,000
        \d+(?:\.\d+)?\s*
        (?:billion|million|trillion|
           thousand|hundred|
           km|kg|mb|gb|tb|hz|mhz|ghz|
           ms|ns|\bx\b|px|pt|em|rem)   |  # numeric + unit
        \b\d{4}\b                           # standalone 4-digit years
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Definition patterns
_RE_DEFINITION = re.compile(
    r"""
    (?P<term>[A-Z][A-Za-z\s\-]{2,40})
    \s*
    (?:
        is\s+defined\s+as      |
        refers\s+to            |
        is\s+known\s+as        |
        means                  |
        can\s+be\s+defined\s+as|
        is\s+the\s+process\s+of|
        is\s+a(?:n)?\s+        |
        \:\s+                  |
        —\s+                   |
        –\s+
    )
    (?P<definition>.+?)
    (?=\.|$|\n)
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Cause & effect connectors
_CAUSE_KEYWORDS  = ["because", "since", "due to", "as a result of", "owing to", "caused by"]
_EFFECT_KEYWORDS = [
    "therefore", "thus", "hence", "consequently", "as a result",
    "leads to", "results in", "causes", "produces", "triggers",
    "enables", "allows", "so that",
]

# Chronology signals: ordinal words + explicit date patterns
_ORDINAL_WORDS = [
    "first", "second", "third", "fourth", "fifth",
    "initially", "then", "next", "subsequently", "finally",
    "previously", "before", "after", "during", "while",
    "earlier", "later", "eventually", "simultaneously",
    "following", "preceding",
]
_RE_DATE = re.compile(
    r"""
    (?:
        \b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|
               May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|
               Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)
        \s+\d{1,2}(?:,\s*\d{4})?      |  # Month Day, Year
        \b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b |  # MM/DD/YYYY
        \b(?:19|20)\d{2}\b                           # Standalone year 19xx/20xx
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Step detection: numbered or lettered lists
_RE_STEP = re.compile(
    r"""
    ^\s*
    (?:
        (?:step|phase|stage|part|item|point)\s*[\d]+  |  # "Step 1", "Phase 2"
        [\d]+[\.:\)]\s+                                |  # "1. ", "2: ", "3) "
        [a-z][\.:\)]\s+                                |  # "a. ", "b) "
        [ivxlcdm]+[\.:\)]\s+                           |  # Roman numerals
        \b(?:first|second|third|fourth|fifth|sixth|
              seventh|eighth|ninth|tenth)\b             # Ordinal words at start
    )
    """,
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)

# Example signals
_EXAMPLE_PHRASES = [
    "for example", "for instance", "e.g.", "such as",
    "to illustrate", "consider", "as an example", "like",
    "including", "namely", "i.e.",
]

# Advantage signals
_ADVANTAGE_PHRASES = [
    "advantage", "benefit", "pro", "strength", "merit",
    "positive", "plus", "upside", "gain", "reward",
    "asset", "virtue", "boon", "virtue", "opportunity",
]

# Disadvantage signals
_DISADVANTAGE_PHRASES = [
    "disadvantage", "drawback", "con", "weakness", "limitation",
    "challenge", "downside", "risk", "issue", "problem",
    "concern", "obstacle", "barrier", "cost", "penalty",
    "pitfall", "threat", "negative",
]

# Comparison signals
_COMPARISON_PHRASES = [
    "vs", "versus", "compared to", "compared with",
    "unlike", "whereas", "on the other hand",
    "in contrast", "alternatively", "similarly",
    "different from", "same as", "as opposed to",
]

# Process signals
_PROCESS_PHRASES = [
    "process", "mechanism", "procedure", "operation",
    "system", "workflow", "pipeline", "sequence",
    "cycle", "algorithm", "method", "technique",
    "approach", "strategy", "protocol",
]

# Learning objective signals
_OBJECTIVE_PHRASES = [
    "understand", "learn", "able to", "by the end",
    "objective", "goal", "aim", "purpose",
    "you will", "students will", "learners will",
    "upon completion", "after this", "this module",
    "this lesson", "this slide", "this section",
]

# Frequently-asked-question signals
_FAQ_SUFFIX_WORDS = [
    "what", "why", "how", "when", "where", "who",
    "which", "can", "does", "is", "are", "do",
    "should", "will", "would", "could",
]

# Technical domain terms (common across STEM/business disciplines)
_TECHNICAL_TERMS = frozenset([
    "algorithm", "architecture", "bandwidth", "byte", "cache",
    "catalyst", "chromosome", "coefficient", "compiler", "database",
    "derivative", "ecosystem", "electrode", "entropy", "equilibrium",
    "firmware", "gradient", "hypothesis", "inference", "integral",
    "iteration", "kernel", "latency", "microcontroller", "middleware",
    "molecule", "neural", "nucleus", "optimization", "paradigm",
    "photosynthesis", "polymer", "protocol", "quantum", "recursion",
    "regression", "render", "repository", "runtime", "semiconductor",
    "serialization", "synthesis", "topology", "transformer", "variance",
    "velocity", "wavelength", "widget", "framework", "interface",
    "api", "sdk", "cpu", "gpu", "ram", "sql", "nosql", "cloud",
    "container", "microservice", "agile", "scrum", "devops", "ci",
    "cd", "saas", "paas", "iaas", "roi", "kpi", "erp", "crm",
])

# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _sentences(text: str) -> List[str]:
    """Split text into sentences using simple punctuation heuristic."""
    # Split on period/exclamation/question mark followed by space or end
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


def _words(text: str) -> List[str]:
    """Lowercase word tokens, stripped of punctuation."""
    return re.findall(r"[a-zA-Z']+", text.lower())


def _contains_any(text: str, phrases: List[str]) -> bool:
    lower = text.lower()
    return any(ph in lower for ph in phrases)


def _extract_after_phrase(text: str, phrase: str) -> str:
    """Extract the clause that follows a given connecting phrase."""
    lower = text.lower()
    idx = lower.find(phrase)
    if idx == -1:
        return ""
    after = text[idx + len(phrase):].strip().rstrip(".")
    return after[:200]  # cap length


def _deduplicate(items: List[str]) -> List[str]:
    """Remove exact duplicates while preserving order."""
    seen: set = set()
    result = []
    for item in items:
        norm = item.strip().lower()
        if norm not in seen and norm:
            seen.add(norm)
            result.append(item.strip())
    return result


def _word_overlap_ratio(a: str, b: str) -> float:
    """Jaccard similarity between word sets of two strings."""
    sa = set(_words(a))
    sb = set(_words(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# ─────────────────────────────────────────────────────────────────────────────
# Text aggregation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _all_text_blocks(slide: SlidePageEntity) -> List[TextBlockElement]:
    """Return all text blocks sorted by reading order."""
    return sorted(slide.text_blocks, key=lambda tb: tb.reading_order)


def _all_plain_text(slide: SlidePageEntity) -> str:
    """Concatenate all text blocks into one string (speaker notes excluded)."""
    parts = [tb.text for tb in slide.text_blocks if tb.text]
    if slide.speaker_notes:
        parts.append(slide.speaker_notes)
    return " ".join(parts)


def _body_text_blocks(slide: SlidePageEntity) -> List[TextBlockElement]:
    """Non-heading text blocks."""
    return [tb for tb in slide.text_blocks if not tb.is_heading and tb.text]


# ─────────────────────────────────────────────────────────────────────────────
# Extractor functions — one per responsibility
# ─────────────────────────────────────────────────────────────────────────────

def extract_main_topic(slide: SlidePageEntity) -> str:
    """
    Responsibility 1 — Main Topic.
    Primary: slide title. Fallback: most capitalised noun-phrase from headings.
    """
    if slide.title and slide.title.strip():
        title = slide.title.strip()
        # Remove generic slide labels
        if not re.match(r"^slide\s+\d+$", title, re.IGNORECASE):
            return title

    # Fallback: first heading text block
    for tb in _all_text_blocks(slide):
        if tb.is_heading and tb.text:
            return tb.text.strip()

    # Last resort: first non-empty text
    for tb in _all_text_blocks(slide):
        if tb.text:
            return tb.text.strip()[:80]

    return "Untitled Slide"


def extract_learning_objective(slide: SlidePageEntity) -> str:
    """
    Responsibility 2 — Learning Objective.
    Detects objective-phrased sentences in text blocks and speaker notes.
    """
    all_text = _all_plain_text(slide)
    for sent in _sentences(all_text):
        if _contains_any(sent, _OBJECTIVE_PHRASES):
            return sent.strip()

    # Check speaker notes specifically
    if slide.speaker_notes:
        for sent in _sentences(slide.speaker_notes):
            if _contains_any(sent, _OBJECTIVE_PHRASES):
                return sent.strip()

    return ""


def extract_key_concepts(slide: SlidePageEntity) -> List[str]:
    """
    Responsibility 3 — Key Concepts.
    Sources: bold text, heading-level blocks, and capitalised terms from title.
    """
    concepts: List[str] = []

    for tb in _all_text_blocks(slide):
        if tb.is_heading or tb.is_bold or (tb.font_size and tb.font_size >= 20):
            text = tb.text.strip()
            if text and len(text) > 1:
                # Split compound headings by common separators
                parts = re.split(r"[:\-–|/]", text)
                for part in parts:
                    p = part.strip()
                    if p and len(p) > 1:
                        concepts.append(p)

    # Add capitalized multi-word phrases from title
    title_words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", slide.title or "")
    concepts.extend(title_words)

    return _deduplicate(concepts)[:10]


def extract_supporting_concepts(
    slide: SlidePageEntity,
    key_concepts: List[str],
) -> List[str]:
    """
    Responsibility 4 — Supporting Concepts.
    Non-heading, non-bold body text that is NOT a definition/step/example.
    """
    key_lower = {c.lower() for c in key_concepts}
    supporting: List[str] = []

    for tb in _body_text_blocks(slide):
        text = tb.text.strip()
        if not text or len(text) < 5:
            continue
        if tb.is_bold or tb.is_heading:
            continue
        # Skip pure numbers or very short fragments
        if re.fullmatch(r"[\d\s\.\,\%\$\-]+", text):
            continue
        # Skip if too similar to a key concept
        if any(_word_overlap_ratio(text, kc) > 0.7 for kc in key_concepts):
            continue
        supporting.append(text[:120])

    return _deduplicate(supporting)[:8]


def extract_definitions(slide: SlidePageEntity) -> Dict[str, str]:
    """
    Responsibility 5 — Definitions.
    Regex-based pattern matching for 'X is defined as Y', 'X: Y', 'X — Y', etc.
    """
    definitions: Dict[str, str] = {}
    all_text = _all_plain_text(slide)

    for match in _RE_DEFINITION.finditer(all_text):
        term       = match.group("term").strip()
        definition = match.group("definition").strip()
        if len(term) >= 3 and len(definition) >= 5:
            # Normalise term — remove trailing articles
            term = re.sub(r"\s+(a|an|the)\s*$", "", term, flags=re.IGNORECASE).strip()
            definitions[term] = definition[:300]

    # Also check colon-separated inline definitions from text blocks
    for tb in _all_text_blocks(slide):
        text = tb.text.strip()
        colon_match = re.match(r"^([A-Z][A-Za-z\s\-]{2,35}):\s+(.{5,})", text)
        if colon_match:
            term = colon_match.group(1).strip()
            defn = colon_match.group(2).strip()
            if term not in definitions:
                definitions[term] = defn[:300]

    return definitions


def extract_important_facts(slide: SlidePageEntity) -> List[str]:
    """
    Responsibility 6 — Important Facts.
    Declarative sentences flagged by explicit importance markers OR bold styling.
    """
    importance_signals = [
        "important", "critical", "key", "essential", "fundamental",
        "note that", "remember", "significant", "must", "required",
        "primary", "main", "core", "vital", "crucial",
    ]
    facts: List[str] = []
    all_text = _all_plain_text(slide)

    for sent in _sentences(all_text):
        if _contains_any(sent, importance_signals):
            facts.append(sent.strip())

    # Also include bold, non-heading blocks as facts
    for tb in _all_text_blocks(slide):
        if tb.is_bold and not tb.is_heading and tb.text.strip():
            text = tb.text.strip()
            if text not in facts:
                facts.append(text)

    return _deduplicate(facts)[:8]


def extract_numbers_and_statistics(slide: SlidePageEntity) -> List[str]:
    """
    Responsibility 7 — Numbers & Statistics.
    Extracts all numeric expressions with their surrounding context.
    """
    stats: List[str] = []
    all_text = _all_plain_text(slide)

    for match in _RE_NUMBERS.finditer(all_text):
        # Grab up to 60 chars of surrounding context
        start = max(0, match.start() - 30)
        end   = min(len(all_text), match.end() + 30)
        context = all_text[start:end].strip()
        # Clean partial sentences
        context = re.sub(r"^\S+\s", "", context)  # drop leading partial word
        stats.append(context.strip())

    return _deduplicate(stats)[:12]


def extract_processes(slide: SlidePageEntity) -> List[str]:
    """
    Responsibility 8 — Processes.
    Sentences describing mechanisms, procedures, workflows.
    """
    processes: List[str] = []
    all_text = _all_plain_text(slide)

    for sent in _sentences(all_text):
        if _contains_any(sent, _PROCESS_PHRASES):
            processes.append(sent.strip())

    return _deduplicate(processes)[:6]


def extract_comparisons(slide: SlidePageEntity) -> List[Dict[str, Any]]:
    """
    Responsibility 9 — Comparisons.
    Detects 'X vs Y', 'X compared to Y', etc. and also uses table headers.
    """
    comparisons: List[Dict[str, Any]] = []
    all_text = _all_plain_text(slide)

    # Sentence-level comparison detection
    for sent in _sentences(all_text):
        lower = sent.lower()
        for phrase in _COMPARISON_PHRASES:
            if phrase in lower:
                idx = lower.find(phrase)
                left  = sent[:idx].strip().rstrip(",;")
                right = sent[idx + len(phrase):].strip().lstrip(",;")
                if left and right:
                    comparisons.append({
                        "left":   left[:100],
                        "right":  right[:100],
                        "aspect": phrase,
                        "source": "text",
                    })
                break  # one comparison per sentence

    # Table-based comparisons
    for tbl in slide.tables:
        if len(tbl.headers) >= 2:
            comparisons.append({
                "left":   tbl.headers[0],
                "right":  tbl.headers[1] if len(tbl.headers) > 1 else "",
                "aspect": "table comparison",
                "source": "table",
                "table_id": tbl.id,
            })

    return comparisons[:6]


def extract_cause_and_effect(slide: SlidePageEntity) -> List[Dict[str, str]]:
    """
    Responsibility 10 — Cause & Effect.
    Splits sentences at causal connectors.
    """
    pairs: List[Dict[str, str]] = []
    all_text = _all_plain_text(slide)

    for sent in _sentences(all_text):
        lower = sent.lower()

        # Cause → Effect: "X because/since Y" → cause = X, effect = Y... wait, reversed
        for kw in _CAUSE_KEYWORDS:
            if kw in lower:
                idx = lower.find(kw)
                effect = sent[:idx].strip().rstrip(",;")
                cause  = sent[idx + len(kw):].strip().lstrip(",;")
                if cause and effect:
                    pairs.append({"cause": cause[:150], "effect": effect[:150]})
                break

        # Effect: "X therefore/thus/leads to Y"
        for kw in _EFFECT_KEYWORDS:
            if kw in lower:
                idx = lower.find(kw)
                cause  = sent[:idx].strip().rstrip(",;")
                effect = sent[idx + len(kw):].strip().lstrip(",;")
                if cause and effect:
                    # Avoid duplicate from above pass
                    entry = {"cause": cause[:150], "effect": effect[:150]}
                    if entry not in pairs:
                        pairs.append(entry)
                break

    return pairs[:6]


def extract_chronology(slide: SlidePageEntity) -> List[str]:
    """
    Responsibility 11 — Chronology.
    Ordered list of temporal items (dates, ordinals, sequential phrases).
    """
    chronology: List[str] = []
    all_text = _all_plain_text(slide)

    # Explicit dates
    for match in _RE_DATE.finditer(all_text):
        start = max(0, match.start() - 10)
        end   = min(len(all_text), match.end() + 60)
        snippet = all_text[start:end].strip()
        chronology.append(snippet[:120])

    # Ordinal-word-led sentences
    for sent in _sentences(all_text):
        lower = sent.lower()
        for word in _ORDINAL_WORDS:
            if re.search(r"\b" + re.escape(word) + r"\b", lower):
                chronology.append(sent.strip()[:150])
                break

    return _deduplicate(chronology)[:10]


def extract_advantages(slide: SlidePageEntity) -> List[str]:
    """Responsibility 12 — Advantages."""
    advantages: List[str] = []
    all_text = _all_plain_text(slide)

    for sent in _sentences(all_text):
        if _contains_any(sent, _ADVANTAGE_PHRASES):
            advantages.append(sent.strip())

    # Bullet items from blocks explicitly listing advantages
    for tb in _body_text_blocks(slide):
        if _contains_any(tb.text, _ADVANTAGE_PHRASES):
            advantages.append(tb.text.strip())

    return _deduplicate(advantages)[:6]


def extract_disadvantages(slide: SlidePageEntity) -> List[str]:
    """Responsibility 13 — Disadvantages."""
    disadvantages: List[str] = []
    all_text = _all_plain_text(slide)

    for sent in _sentences(all_text):
        if _contains_any(sent, _DISADVANTAGE_PHRASES):
            disadvantages.append(sent.strip())

    for tb in _body_text_blocks(slide):
        if _contains_any(tb.text, _DISADVANTAGE_PHRASES):
            disadvantages.append(tb.text.strip())

    return _deduplicate(disadvantages)[:6]


def extract_steps(slide: SlidePageEntity) -> List[str]:
    """
    Responsibility 14 — Steps.
    Numbered items, "Step N", "Phase N" patterns, and ordered bullet sequences.
    """
    steps: List[str] = []
    all_text = _all_plain_text(slide)

    # Multi-line text: scan line by line
    for line in all_text.splitlines():
        line = line.strip()
        if _RE_STEP.match(line) and len(line) > 4:
            # Strip the leading marker
            clean = _RE_STEP.sub("", line).strip()
            if clean:
                steps.append(clean)

    # Consecutive bullet_level=0 or 1 blocks with clear ordering
    prev_order = -1
    step_candidate_group: List[str] = []
    for tb in sorted(slide.text_blocks, key=lambda t: t.reading_order):
        if tb.bullet_level in (0, 1) and not tb.is_heading:
            if _RE_STEP.search(tb.text):
                step_candidate_group.append(tb.text.strip())

    steps.extend(step_candidate_group)

    return _deduplicate(steps)[:10]


def extract_examples(slide: SlidePageEntity) -> List[str]:
    """Responsibility 15 — Examples."""
    examples: List[str] = []
    all_text = _all_plain_text(slide)

    for sent in _sentences(all_text):
        if _contains_any(sent, _EXAMPLE_PHRASES):
            examples.append(sent.strip())

    return _deduplicate(examples)[:6]


def extract_formulas(slide: SlidePageEntity) -> List[str]:
    """
    Responsibility 16 — Formulas.
    Sources: EquationElement objects + inline math-pattern regex.
    """
    formulas: List[str] = []

    # From structured equation elements
    for eq in slide.equations:
        if eq.latex_expression:
            formulas.append(eq.latex_expression.strip())
        elif eq.ascii_fallback:
            formulas.append(eq.ascii_fallback.strip())

    # Inline math patterns: =, ×, ÷, ^, √, ∑, ∫, ±, Δ
    all_text = _all_plain_text(slide)
    math_pattern = re.compile(
        r"[A-Za-z0-9\s]+(?:[=×÷\^√∑∫±Δ→←↔≤≥≠∞∝∈∀∃])[A-Za-z0-9\s\+\-\*\/\(\)\.]+"
    )
    for match in math_pattern.finditer(all_text):
        candidate = match.group(0).strip()
        if 4 <= len(candidate) <= 200:
            formulas.append(candidate)

    # Also check "formula", "equation" keyword context
    formula_kw_pattern = re.compile(
        r"(?:formula|equation|expression)\s*:?\s*(.+?)(?=\.|$|\n)",
        re.IGNORECASE,
    )
    for match in formula_kw_pattern.finditer(all_text):
        candidate = match.group(1).strip()
        if candidate:
            formulas.append(candidate[:150])

    return _deduplicate(formulas)[:8]


def extract_lists(slide: SlidePageEntity) -> List[List[str]]:
    """
    Responsibility 17 — Lists.
    Groups consecutive bullet-level>0 blocks into logical lists.
    Also captures table columns as lists.
    """
    result_lists: List[List[str]] = []

    # Group bullet blocks into lists by continuity
    current_group: List[str] = []
    prev_was_bullet = False

    for tb in sorted(slide.text_blocks, key=lambda t: t.reading_order):
        if tb.bullet_level > 0 and tb.text.strip():
            current_group.append(tb.text.strip())
            prev_was_bullet = True
        else:
            if current_group and len(current_group) >= 2:
                result_lists.append(current_group)
            current_group = []
            prev_was_bullet = False

    if current_group and len(current_group) >= 2:
        result_lists.append(current_group)

    # Table columns as lists
    for tbl in slide.tables:
        if tbl.headers:
            result_lists.append(tbl.headers)
        for col_idx in range(tbl.num_cols):
            col_items = []
            for row in tbl.rows:
                if col_idx < len(row) and row[col_idx].strip():
                    col_items.append(row[col_idx].strip())
            if col_items:
                result_lists.append(col_items)

    return result_lists[:8]


def extract_faqs(slide: SlidePageEntity) -> List[Dict[str, str]]:
    """
    Responsibility 18 — FAQs.
    Detects question-answer pairs. A question is any sentence ending in '?'
    or starting with a question word.
    """
    faqs: List[Dict[str, str]] = []
    all_sents = _sentences(_all_plain_text(slide))

    i = 0
    while i < len(all_sents):
        sent = all_sents[i]
        is_question = sent.strip().endswith("?")
        if not is_question:
            first_word = _words(sent)[0] if _words(sent) else ""
            is_question = first_word in _FAQ_SUFFIX_WORDS and len(sent.split()) < 15

        if is_question:
            answer = all_sents[i + 1].strip() if i + 1 < len(all_sents) else ""
            faqs.append({"question": sent.strip(), "answer": answer})
            i += 2
        else:
            i += 1

    return faqs[:6]


def extract_relationships(
    slide: SlidePageEntity,
    key_concepts: List[str],
) -> List[ConceptRelationship]:
    """
    Responsibility 19 — Relationships between concepts.
    Detects co-occurrence of two key concepts in one sentence with a linking verb.
    """
    relationships: List[ConceptRelationship] = []
    if len(key_concepts) < 2:
        return relationships

    # Build lower-case concept index
    concept_lower = {c.lower(): c for c in key_concepts}

    _LINK_VERB_MAP: List[Tuple[List[str], RelationshipType]] = [
        (["is a", "is an", "are a", "are an"],                     RelationshipType.IS_A),
        (["is part of", "are part of", "belongs to"],              RelationshipType.PART_OF),
        (["causes", "caused by", "triggers"],                      RelationshipType.CAUSES),
        (["leads to", "results in", "produces", "enables"],        RelationshipType.LEADS_TO),
        (["depends on", "requires", "relies on"],                  RelationshipType.DEPENDS_ON),
        (["unlike", "versus", "compared to", "in contrast"],       RelationshipType.CONTRASTS_WITH),
        (["supports", "enhances", "improves"],                     RelationshipType.SUPPORTS),
        (["is defined as", "refers to", "means"],                  RelationshipType.DEFINED_BY),
        (["includes", "contains", "consists of", "comprises"],     RelationshipType.INCLUDES),
        (["follows", "precedes", "after", "before"],               RelationshipType.FOLLOWS),
    ]

    all_text = _all_plain_text(slide)
    for sent in _sentences(all_text):
        lower = sent.lower()
        found_concepts = [c for c_lower, c in concept_lower.items() if c_lower in lower]
        if len(found_concepts) < 2:
            continue

        rel_type = RelationshipType.UNKNOWN
        for verbs, rtype in _LINK_VERB_MAP:
            if any(v in lower for v in verbs):
                rel_type = rtype
                break

        # Emit first pair found
        relationships.append(
            ConceptRelationship(
                subject=found_concepts[0],
                predicate=rel_type,
                object=found_concepts[1],
                confidence=0.7 if rel_type != RelationshipType.UNKNOWN else 0.3,
            )
        )

        if len(relationships) >= 10:
            break

    return relationships


# ─────────────────────────────────────────────────────────────────────────────
# Raw signals for complexity scorer (Responsibility 20 — partial)
# ─────────────────────────────────────────────────────────────────────────────

def extract_complexity_signals(slide: SlidePageEntity) -> Dict[str, Any]:
    """
    Responsibility 20 — raw signals consumed by complexity_scorer.py.
    Returns a dict of raw metrics rather than a final score.
    """
    all_text = _all_plain_text(slide)
    words = _words(all_text)
    sents = _sentences(all_text)

    unique_words     = set(words)
    total_words      = len(words) if words else 1
    vocab_richness   = len(unique_words) / total_words

    avg_sent_length  = (total_words / len(sents)) if sents else 0
    tech_term_count  = sum(1 for w in words if w in _TECHNICAL_TERMS)
    technical_density = tech_term_count / (total_words / 100) if total_words > 0 else 0

    element_count    = (
        len(slide.text_blocks)
        + len(slide.equations)
        + len(slide.charts)
        + len(slide.diagrams)
        + len(slide.tables)
    )

    max_bullet_depth = max((tb.bullet_level for tb in slide.text_blocks), default=0)

    return {
        "vocab_richness":    round(vocab_richness, 4),
        "avg_sent_length":   round(avg_sent_length, 2),
        "technical_density": round(technical_density, 2),
        "element_count":     element_count,
        "max_bullet_depth":  max_bullet_depth,
        "total_words":       total_words,
        "sentence_count":    len(sents),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def extract_all(slide: SlidePageEntity) -> Dict[str, Any]:
    """
    Run all 20 extractors against a single SlidePageEntity and return
    a unified dict consumed by the engine orchestrator.
    """
    key_concepts = extract_key_concepts(slide)

    return {
        # 1
        "main_topic":             extract_main_topic(slide),
        # 2
        "learning_objective":     extract_learning_objective(slide),
        # 3
        "key_concepts":           key_concepts,
        # 4
        "supporting_concepts":    extract_supporting_concepts(slide, key_concepts),
        # 5
        "definitions":            extract_definitions(slide),
        # 6
        "important_facts":        extract_important_facts(slide),
        # 7
        "numbers_and_statistics": extract_numbers_and_statistics(slide),
        # 8
        "processes":              extract_processes(slide),
        # 9
        "comparisons":            extract_comparisons(slide),
        # 10
        "cause_and_effect":       extract_cause_and_effect(slide),
        # 11
        "chronology":             extract_chronology(slide),
        # 12
        "advantages":             extract_advantages(slide),
        # 13
        "disadvantages":          extract_disadvantages(slide),
        # 14
        "steps":                  extract_steps(slide),
        # 15
        "examples":               extract_examples(slide),
        # 16
        "formulas":               extract_formulas(slide),
        # 17
        "lists":                  extract_lists(slide),
        # 18
        "faqs":                   extract_faqs(slide),
        # 19
        "relationships":          extract_relationships(slide, key_concepts),
        # 20 (raw signals — final score computed in complexity_scorer.py)
        "complexity_signals":     extract_complexity_signals(slide),
    }
