"""
Learnova — Streamlit frontend.

This file is deliberately thin: it collects input, calls
``learnova.pipeline.orchestrator``, and renders the result. All business logic
lives in the ``learnova`` package, so the FastAPI backend in ``apps/api`` runs
exactly the same code path.

Run with:  streamlit run apps/streamlit_app/app.py
"""

import pathlib
import sys

# Make `src/` importable before anything from `learnova` is touched.
_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from learnova.config import apply_runtime_env

apply_runtime_env()  # must precede any C-extension import

import faulthandler
import tempfile
import time

import streamlit as st
from dotenv import load_dotenv

from learnova.config import MAX_FILE_SIZE_MB, get_gemini_key
from learnova.logging_config import logger
from learnova.parsers.markdown_converter import from_typed_text
from learnova.pipeline.orchestrator import PipelineConfig, build_markdown, generate
from learnova.rendering.theme_engine import THEMES

from helpers import safe_dataframe
from styles import custom_css

faulthandler.enable()
load_dotenv()

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Learnova — AI Presentation Engine",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(custom_css, unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────────
_defaults = {
    "markdown_doc": None,
    "markdown_text": "",
    "result": None,
    "source_name": None,
    "input_mode": "upload",
}
for key, val in _defaults.items():
    st.session_state.setdefault(key, val)


def _reset() -> None:
    for k, v in _defaults.items():
        st.session_state[k] = v


THEME_OPTIONS = {
    "✨ Auto-Detect Theme from Topic": "auto",
    "⚡ Brutalist Neon (Default)": "brutalist_neon",
    "🌌 Midnight Cyber": "midnight_cyber",
    "🌿 Emerald Academic": "emerald_academic",
    "🇨🇭 Swiss Corporate Minimalist": "swiss_corporate",
    "🌅 Sunset Pastel Editorial": "sunset_editorial",
    "🌊 Deep Ocean Tech": "ocean_tech",
    "👑 Charcoal Gold Luxury": "charcoal_gold",
    "🏔️ Nordic Clean Slate": "nordic_slate",
    "🧱 Warm Terracotta Earth": "warm_terracotta",
    "🔮 Glassmorphism Indigo": "glass_indigo",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h1 style='font-family: Bebas Neue, cursive; color: #ccff00; "
        "margin-top: -2rem;'>LEARNOVA</h1>",
        unsafe_allow_html=True,
    )
    st.header("📖 Visual Engine")
    st.markdown(
        "1. **Upload** a PPT/PDF — or type your syllabus\n"
        "2. **Review** the extracted markdown and edit it\n"
        "3. **AI Layout Router** detects processes, tables & metrics\n"
        "4. **Quizzes** are interleaved dynamically\n"
        "5. **Export** an animated PPTX and an interactive web deck"
    )
    st.divider()

    st.header("⚙️ Settings")
    parsing_mode = st.selectbox("Document Style", ["Auto", "PPT / Slides", "Textbook PDF"])
    quiz_freq = st.slider("Quiz Frequency (Every N Slides)", 2, 6, 4)
    theme_label = st.selectbox("🎨 Presentation Design Template", list(THEME_OPTIONS.keys()))
    theme_id = THEME_OPTIONS[theme_label]

    with st.expander("Advanced"):
        enable_ocr = st.checkbox("Gemini Vision OCR on images", value=True)
        prefer_anydoc = st.checkbox("Try AnyDoc fast text path", value=True)
        use_cache = st.checkbox("Cache markdown by file hash", value=True)
        content_mode = st.radio(
            "Content direction",
            ["compress", "expand"],
            help="compress: condense a long document. expand: build out a short syllabus.",
        )

    st.divider()
    if st.button("🔄 Reset & Start Fresh"):
        _reset()
        st.rerun()

    result = st.session_state.result
    if result:
        st.header("📈 Session Stats")
        st.metric("Total Deck Slides", len(result.final_deck))
        st.metric("Avg Engagement Score", f"{result.scores.get('overall_score', 0)}/100")
        st.metric("Quizzes Interleaved", len(result.quizzes))

config = PipelineConfig(
    theme_id=theme_id,
    quiz_frequency=quiz_freq,
    textbook_mode=(parsing_mode == "Textbook PDF"),
    enable_vision_ocr=enable_ocr,
    prefer_anydoc=prefer_anydoc,
    use_cache=use_cache,
    content_mode=content_mode,
)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
<div style="background-color:#000; padding:4px 12px; display:inline-block; margin-bottom:20px;">
  <span style="color:#ccff00; font-family:'Inter',sans-serif; font-weight:800;
               font-size:0.8rem; letter-spacing:2px; text-transform:uppercase;">
    ● AI VISUAL PRESENTATION ENGINE
  </span>
</div>
""",
    unsafe_allow_html=True,
)
st.title("LEARNOVA")
st.markdown(
    "*Transform text-heavy PPTs, notes, and PDFs into dynamic visual presentations "
    "complete with flowcharts, tables, metric cards, interactive quizzes, and animations.*"
)
st.divider()

if not get_gemini_key():
    st.warning(
        "⚠️ **GEMINI_API_KEY** not set — image OCR will be skipped. "
        "Text processing works without it."
    )

# ── Step 1: Input ────────────────────────────────────────────────────────────
st.markdown("### 1 · Provide your content")
tab_upload, tab_typed = st.tabs(["📎 Upload a document", "⌨️ Type a syllabus"])

with tab_upload:
    uploaded = st.file_uploader(
        "Choose a PPTX or PDF file",
        type=["pptx", "pdf"],
        help=f"Supported: .pptx, .pdf (max {MAX_FILE_SIZE_MB} MB)",
    )
    if uploaded is not None:
        size_mb = len(uploaded.getbuffer()) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            st.error(f"⚠️ File is too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.")
        elif st.button("📄 Extract to Markdown", type="primary"):
            suffix = pathlib.Path(uploaded.name).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name
            try:
                with st.spinner("Extracting document into markdown…"):
                    doc = build_markdown(tmp_path, source_name=uploaded.name, config=config)
                st.session_state.markdown_doc = doc
                st.session_state.markdown_text = doc.markdown
                st.session_state.source_name = uploaded.name
                st.session_state.result = None
                st.success(f"✅ Extracted via **{doc.converter}** — review the markdown below.")
            except Exception as exc:
                logger.error("extraction failed: %s", exc, exc_info=True)
                st.error(f"⚠️ Extraction failed: {exc}")
            finally:
                try:
                    pathlib.Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass

with tab_typed:
    typed = st.text_area(
        "Paste or type your syllabus / outline",
        height=220,
        placeholder="## Chapter 1: Introduction\n- Key idea one\n- Key idea two",
    )
    typed_name = st.text_input("Title", value="Typed Syllabus")
    if st.button("✍️ Use this text") and typed.strip():
        doc = from_typed_text(typed, source_name=typed_name or "Typed Syllabus")
        st.session_state.markdown_doc = doc
        st.session_state.markdown_text = doc.markdown
        st.session_state.source_name = typed_name or "Typed Syllabus"
        st.session_state.result = None
        st.success("✅ Text accepted — review the markdown below.")

# ── Step 2: Editable markdown review ─────────────────────────────────────────
if st.session_state.markdown_doc is not None:
    st.divider()
    st.markdown("### 2 · Review & edit the extracted markdown")
    st.caption(
        "This is the intermediate representation the whole pipeline reasons over. "
        "Edits here change the generated deck."
    )

    edited = st.text_area(
        "Markdown",
        value=st.session_state.markdown_text,
        height=340,
        label_visibility="collapsed",
    )
    st.session_state.markdown_text = edited

    from learnova.parsers.markdown_converter import split_sections

    sections = split_sections(edited, max_level=2)
    st.caption(f"→ {len(sections)} section(s) detected on `##` boundaries.")

    if st.button("🚀 Generate Visual Deck", type="primary"):
        doc = st.session_state.markdown_doc
        doc.markdown = edited

        bar = st.progress(0.0, text="Starting…")
        status = st.empty()

        def _progress(stage: str, state: str, fraction: float, detail: str) -> None:
            icon = {"running": "⏳", "ok": "✅", "failed": "⚠️", "skipped": "⏭️"}.get(state, "•")
            bar.progress(min(fraction, 1.0), text=f"{icon} {stage}")
            status.markdown(f"{icon} **{stage}** — {state}{(' · ' + detail) if detail else ''}")

        started = time.time()
        try:
            st.session_state.result = generate(doc, config=config, progress=_progress)
            bar.progress(1.0, text="Done")
            status.empty()
            st.success(f"✅ Done in {time.time() - started:.1f}s — scroll down for your deck.")
        except Exception as exc:
            logger.error("generation failed: %s", exc, exc_info=True)
            st.error(f"⚠️ Processing failed: {exc}")

# ── Step 3: Results ──────────────────────────────────────────────────────────
result = st.session_state.result
if result:
    st.divider()
    st.markdown("### 3 · Download your presentation")
    deck = result.final_deck
    dl_name = pathlib.Path(result.source_name or "presentation").stem

    col1, col2 = st.columns(2)
    with col1:
        if result.pptx_bytes:
            st.download_button(
                "📥 Download Animated PPTX (.pptx)",
                data=result.pptx_bytes,
                file_name=f"Learnova_Visual_{dl_name}.pptx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                ),
            )
        else:
            st.warning("⚠️ PPTX build failed – see logs for details.")
    with col2:
        if result.html_bytes:
            st.download_button(
                "🌐 Download Interactive Web Deck (.html)",
                data=result.html_bytes,
                file_name=f"Learnova_Interactive_{dl_name}.html",
                mime="text/html",
            )
        else:
            st.warning("⚠️ HTML build failed – see logs for details.")

    with st.expander("🔬 Pipeline stage report"):
        for stage in result.stages:
            icon = {"ok": "✅", "failed": "⚠️", "skipped": "⏭️"}.get(stage.status, "•")
            line = f"{icon} `{stage.name}` — {stage.status} ({stage.seconds:.2f}s)"
            if stage.detail:
                line += f" · {stage.detail}"
            st.markdown(line)

    st.divider()

    scores_data = result.scores or {"slide_scores": [], "overall_score": 0}
    scores_list = scores_data.get("slide_scores", [])
    quizzes = result.quizzes

    tab_slides, tab_quizzes, tab_scores = st.tabs(
        ["📄 Visual Deck Slides", "🧠 Interleaved Quizzes", "📊 Engagement Dashboard"]
    )

    # ── Tab 1: Visual Deck Slides ────────────────────────────────────────────
    with tab_slides:
        st.subheader(f"🎨 Redesigned Visual Deck ({len(deck)} Slides)")

        badge_colors = {
            "FLOWCHART": "#28a745",
            "TABLE": "#17a2b8",
            "METRIC": "#fd7e14",
            "CARD_GRID": "#e83e8c",
            "QUIZ": "#6f42c1",
        }

        for idx, entry in enumerate(deck):
            orig = entry.get("original", {})
            imp = entry.get("improved", {})

            l_type = imp.get("layout_type", "MINIMAL_TEXT").upper()
            title = imp.get("title", f"Slide {idx + 1}")
            takeaway = imp.get("takeaway", "")
            badge_color = badge_colors.get(l_type, "#1e2761")

            col_a, col_b = st.columns([1, 2])

            with col_a:
                st.markdown("**Source / Original Context**")
                st.markdown(
                    "<div style='background:#f4f4f4; padding:10px; border-left:3px solid #000;'>"
                    f"{orig.get('text', orig.get('title', 'N/A'))}</div>",
                    unsafe_allow_html=True,
                )
                image = orig.get("image")
                if image and image.get("description"):
                    st.markdown(f"🖼️ *Image Description:* {image['description']}")

            with col_b:
                st.markdown(
                    f"### {title} &nbsp; <span style='background:{badge_color}; color:#fff; "
                    f"padding:3px 8px; font-size:0.8rem;'>{l_type}</span>",
                    unsafe_allow_html=True,
                )

                if l_type == "FLOWCHART" and "mermaid_code" in imp:
                    st.markdown("**🔄 Process / Flowchart Sequence:**")
                    steps = imp.get("bullets", [])
                    if steps:
                        flow_html = " &nbsp;➔&nbsp; ".join(
                            f"<span style='background:#17a2b8; color:#fff; padding:4px 10px; "
                            f"border-radius:12px; font-weight:600;'>{s}</span>"
                            for s in steps
                        )
                        st.markdown(
                            f"<div style='margin-bottom:12px;'>{flow_html}</div>",
                            unsafe_allow_html=True,
                        )
                    with st.expander("📐 View Diagram Definition"):
                        st.code(imp["mermaid_code"], language="text")

                elif l_type == "TABLE" and "table_headers" in imp:
                    headers = imp.get("table_headers", [])
                    rows = imp.get("table_rows", [])
                    if headers and rows:
                        safe_dataframe(
                            rows,
                            columns=[str(h) for h in headers],
                            label=f"Slide {idx + 1} — {title}",
                        )

                elif l_type == "METRIC":
                    st.markdown(
                        "<div style='background:#1e2761; color:#ccff00; padding:20px; "
                        "border-radius:8px; text-align:center;'>"
                        f"<h1 style='color:#ccff00; margin:0;'>{imp.get('metric_value', '100%')}</h1>"
                        f"<h4>{imp.get('metric_label', title)}</h4>"
                        f"<p style='color:#fff;'>{imp.get('metric_desc', takeaway)}</p></div>",
                        unsafe_allow_html=True,
                    )

                elif l_type == "CARD_GRID":
                    bullets = imp.get("bullets", [])
                    c_num = min(len(bullets), 4) or 1
                    cols = st.columns(c_num)
                    for b_idx, bullet in enumerate(bullets[:4]):
                        with cols[b_idx % c_num]:
                            st.markdown(
                                "<div style='background:#f0f4ff; border:2px solid #1e2761; "
                                "border-radius:8px; padding:12px; height:100%;'>"
                                f"<h5 style='color:#1e2761; margin:0;'>Pillar {b_idx + 1}</h5>"
                                f"<p style='color:#333; font-size:0.9rem; margin-top:5px;'>{bullet}</p>"
                                "</div>",
                                unsafe_allow_html=True,
                            )

                elif l_type == "QUIZ":
                    st.markdown(f"**❓ Question:** {imp.get('question', '')}")
                    for opt in imp.get("options", []):
                        st.markdown(f"- {opt}")
                    st.markdown(f"**✅ Correct Answer:** `{imp.get('correct', 'A')}`")

                else:
                    for bullet in imp.get("bullets", []):
                        st.markdown(f"- {bullet}")

                if takeaway:
                    st.markdown(f"💡 **Takeaway:** *{takeaway}*")

            st.divider()

    # ── Tab 2: Quizzes ───────────────────────────────────────────────────────
    with tab_quizzes:
        if not quizzes:
            st.info("No quizzes generated.")
        else:
            st.subheader(f"🧠 {len(quizzes)} Interleaved Checkpoint Quizzes")
            for q_idx, quiz in enumerate(quizzes):
                st.markdown(f"**Q{q_idx + 1}: {quiz.get('question', '')}**")
                st.radio("Options", quiz.get("options", []), key=f"q_radio_{q_idx}")
                if st.button(f"Show Explanation (Q{q_idx + 1})", key=f"q_btn_{q_idx}"):
                    st.success(f"Correct: {quiz.get('correct', 'A')}")
                    st.info(f"💡 {quiz.get('explanation', '')}")
                st.divider()

    # ── Tab 3: Scores ────────────────────────────────────────────────────────
    with tab_scores:
        st.subheader("📊 Engagement Score Breakdown")
        st.metric("Overall Engagement Score", f"{scores_data.get('overall_score', 0)} / 100")
        if scores_list:
            score_rows = []
            for i, entry in enumerate(scores_list):
                row = {"Slide": f"Slide {i + 1}", "Score": int(entry.get("score", 0))}
                for key, value in entry.get("breakdown", {}).items():
                    try:
                        row[str(key)] = float(value)
                    except (TypeError, ValueError):
                        row[str(key)] = str(value)
                score_rows.append(row)
            safe_dataframe(score_rows, label="Engagement Score Breakdown")
