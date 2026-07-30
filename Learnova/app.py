"""
Learnova – AI Presentation Engine
Streamlit UI with AI-improved slides, dynamic visual layouts (Flowcharts, Tables, Metrics), quizzes, and web exports.
"""

import os
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONFAULTHANDLER"] = "1"
# macOS: prevent segfault when forking after loading Objective-C/C-extension libraries
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import hashlib
import tempfile
import time

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from parsers.ppt_parser import parse_ppt
from parsers.pdf_parser import parse_pdf, parse_textbook_pdf
from rag.chunker import chunk_parsed_data
from rag.retriever import ChunkRetriever
from ai.improver import improve_chunks
from ai.quiz_gen import generate_quizzes, interleave_quizzes_into_slides
from utils.scorer import score_all_slides
from utils.ppt_builder import build_pptx
from utils.web_deck_builder import build_web_deck
from utils.subprocess_builder import build_pptx_safe, build_html_safe
from utils.theme_engine import THEMES, get_theme, auto_detect_theme
from ai.image_describer import describe_images
from logger import logger

# Load environment variables
load_dotenv()

MAX_FILE_SIZE_MB = 50

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Learnova – AI Presentation Engine",
    page_icon="🎓",
    layout="wide",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

* {
    cursor: url('data:image/svg+xml;utf8,<svg width="12" height="12" viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg"><circle cx="6" cy="6" r="6" fill="%23ccff00" stroke="black" stroke-width="1"/></svg>') 6 6, auto !important;
}

button:hover, p:hover, li:hover, h1:hover, h2:hover, h3:hover, h4:hover, h5:hover, h6:hover, a:hover, [data-testid="stExpander"] details:hover, [data-baseweb="tab"]:hover {
    cursor: url('data:image/svg+xml;utf8,<svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg"><circle cx="9" cy="9" r="8" fill="%23ccff00" stroke="black" stroke-width="1.5"/></svg>') 9 9, auto !important;
}

.stApp {
    background-color: #ffffff;
    background-image: radial-gradient(#e0e0e0 2px, transparent 2px);
    background-size: 30px 30px;
}

h1, h2, h3, .st-emotion-cache-10trblm h1 {
    font-family: 'Bebas Neue', cursive !important;
    text-transform: uppercase;
    color: #000000 !important;
    letter-spacing: 1px;
}
h1 {
    font-size: 5.5rem !important;
    line-height: 1.1 !important;
    margin-bottom: 0.5rem !important;
}
h2 {
    font-size: 3rem !important;
}

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    background-color: #ccff00 !important;
    color: #000000 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    border: 3px solid #000000 !important;
    border-radius: 0px !important;
    box-shadow: 6px 6px 0px #000000 !important;
    transition: all 0.2s ease !important;
    padding: 0.5rem 1.5rem !important;
}

.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translate(3px, 3px) !important;
    box-shadow: 3px 3px 0px #000000 !important;
    color: #000000 !important;
    border-color: #000000 !important;
}

[data-testid="stFileUploadDropzone"] {
    background-color: #ffffff !important;
    border: 3px dashed #000000 !important;
    border-radius: 0px !important;
    box-shadow: 6px 6px 0px #000000 !important;
}

[data-testid="stSidebar"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    border-right: 5px solid #ccff00 !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] p {
    color: #ffffff !important;
}

div[role="radiogroup"] label {
    color: #000000 !important;
    font-weight: 600 !important;
}
</style>
<script>
// Auto-reload on 'Importing a module script failed' — happens when the
// Streamlit server restarts after a crash and old JS bundle hashes are stale.
(function() {
    var _reloaded = sessionStorage.getItem('_lr_reload');
    window.addEventListener('unhandledrejection', function(event) {
        var msg = (event.reason && event.reason.message) ? event.reason.message : '';
        if ((msg.includes('Importing a module script failed') ||
             msg.includes('Failed to fetch dynamically imported module')) && !_reloaded) {
            sessionStorage.setItem('_lr_reload', '1');
            window.location.reload();
        }
    });
    // Clear the flag after a successful load so future crashes also auto-reload.
    window.addEventListener('load', function() {
        sessionStorage.removeItem('_lr_reload');
    });
})();
</script>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ── Session State Defaults ───────────────────────────────────────────────────
_defaults = {
    "parsed_data": None,
    "file_type": None,
    "file_name": None,
    "improved_results": None,
    "final_deck": None,
    "quizzes": None,
    "scores": None,
    "processing_time": None,
    "pptx_bytes": None,
    "html_bytes": None,
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h1 style='font-family: Bebas Neue, cursive; color: #ccff00; margin-top: -2rem; padding-left: 0;'>LEARNOVA</h1>",
        unsafe_allow_html=True,
    )
    st.header("📖 Visual Engine")
    st.markdown(
        "1. **Upload** PPT or PDF\n"
        "2. **AI Layout Router** detects processes, tables & metrics\n"
        "3. **Flowcharts & Diagrams** are generated\n"
        "4. **Quizzes Interleaved** dynamically\n"
        "5. **Export** Animated PPTX & Interactive HTML"
    )
    st.divider()

    st.header("⚙️ Settings")
    st.session_state.parsing_mode = st.selectbox("Document Style", ["Auto", "PPT / Slides", "Textbook PDF"])
    st.session_state.quiz_freq = st.slider("Quiz Frequency (Every N Slides)", 2, 6, 4)

    theme_options = {
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
    selected_theme_label = st.selectbox("🎨 Presentation Design Template", list(theme_options.keys()))
    st.session_state.selected_theme_id = theme_options[selected_theme_label]
    st.divider()

    if st.button("🔄 Reset & Start Fresh"):
        for key, val in _defaults.items():
            st.session_state[key] = val
        st.rerun()

    if st.session_state.final_deck:
        scores_data = st.session_state.scores or {"slide_scores": [], "overall_score": 0}
        st.header("📈 Session Stats")
        st.metric("Total Deck Slides", len(st.session_state.final_deck))
        st.metric("Avg Engagement Score", f"{scores_data.get('overall_score', 0)}/100")
        st.metric("Quizzes Interleaved", len(st.session_state.quizzes or []))

# ── Header Banner ────────────────────────────────────────────────────────────
st.markdown("""
<div style="background-color: #000; padding: 4px 12px; display: inline-block; margin-bottom: 20px;">
    <span style="color: #ccff00; font-family: 'Inter', sans-serif; font-weight: 800; font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase;">
        ● AI VISUAL PRESENTATION ENGINE
    </span>
</div>
""", unsafe_allow_html=True)
st.title("LEARNOVA")
st.markdown("*Transform text-heavy PPTs, notes, and PDFs into dynamic visual presentations complete with flowcharts, tables, metric cards, interactive quizzes, and animations.*")
st.divider()

# ── Check GEMINI_API_KEY ─────────────────────────────────────────────────────
if not os.getenv("GEMINI_API_KEY"):
    st.error("⚠️ **GEMINI_API_KEY** not found in `.env` file.")
    st.stop()

# ── File Uploader ────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Choose a PPTX or PDF file",
    type=["pptx", "pdf"],
    help="Supported formats: .pptx, .pdf (max 50 MB)",
)

if uploaded_file is None:
    st.markdown(
        """
        <div style="background-color: #f7ffcc; padding: 15px; border: 3px solid #000; margin-top: 20px;">
            <h4 style="color: #000; margin: 0;">👆 Upload a PPT or PDF to get started</h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.stop()

file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
if file_size_mb > MAX_FILE_SIZE_MB:
    st.error(f"⚠️ File is too large ({file_size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.")
    st.stop()

file_name = uploaded_file.name
file_ext = os.path.splitext(file_name)[1].lower()

if st.session_state.file_name != file_name:
    for key, val in _defaults.items():
        st.session_state[key] = val
    st.session_state.file_name = file_name
    st.session_state.file_type = file_ext

# ── Parsing ──────────────────────────────────────────────────────────────────
if st.session_state.parsed_data is None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    try:
        if file_ext == ".pptx":
            parsed_obj = parse_ppt(tmp_path)
        else:
            if st.session_state.get("parsing_mode") == "Textbook PDF":
                parsed_obj = parse_textbook_pdf(tmp_path)
            else:
                parsed_obj = parse_pdf(tmp_path)

        if parsed_obj:
            parsed_dicts = []
            for s in parsed_obj.slide_units:
                d = {
                    "id": s.id,
                    "slide": s.id + 1,
                    "page": s.id + 1,
                    "title": s.title,
                    "content": s.text.split('\n'),
                    "text": s.text,
                }
                if s.image:
                    d["image"] = s.image
                parsed_dicts.append(d)
            st.session_state.parsed_data = parsed_dicts
    except Exception as e:
        logger.error("Parsing error: %s", e, exc_info=True)
        st.error(f"⚠️ Parsing error: {e}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

parsed = st.session_state.parsed_data

if parsed:
    is_ppt = st.session_state.file_type == ".pptx"
    label = "Slide" if is_ppt else "Page"
    count = len(parsed)

    st.subheader(f"{'📊' if is_ppt else '📄'} Extracted Document Content ({count} {label}s)")
    for item in parsed:
        num = item.get("slide") or item.get("page")
        title = item.get("title") or item.get("heading", f"{label} {num}")
        raw_text = item.get("text", "")

        # Badge for image or scanned page
        has_img = bool(item.get("image"))
        badge = " 🖼️" if has_img else ""

        with st.expander(f"{label} {num}: {title}{badge}"):
            if raw_text and raw_text != "(No readable text on this slide)":
                # Render each line with appropriate formatting
                lines = raw_text.splitlines()
                for ln in lines:
                    stripped = ln.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("## "):
                        st.markdown(f"**{stripped[3:]}**")
                    elif stripped == "[TABLE DATA]":
                        st.markdown("📊 *Table detected:*")
                    elif " | " in stripped:
                        cols = [c.strip() for c in stripped.split(" | ")]
                        st.markdown("| " + " | ".join(cols) + " |")
                    else:
                        st.markdown(f"- {stripped}")
            else:
                st.markdown("<span style='color:#888;'>⚠️ No selectable text — scanned or image-only</span>", unsafe_allow_html=True)

            # Show image thumbnail if present
            if has_img:
                img_bytes = item["image"].get("bytes")
                if img_bytes:
                    st.image(img_bytes, caption="📸 Extracted Image / Page Render", use_container_width=True)

    st.divider()

    # ── AI Processing ────────────────────────────────────────────────────────
    active_theme = st.session_state.get("selected_theme_id", "auto")
    file_name = st.session_state.file_name or "presentation"
    if st.session_state.improved_results is None:
        if st.button("🚀 Process Visual Layouts, Flowcharts & Interleaved Quizzes"):
            t_start = time.time()
            try:
                chunks = chunk_parsed_data(parsed)

                # Process images with Gemini Vision
                images_to_describe = []
                seen_keys = set()
                for i, chunk_data in enumerate(chunks):
                    if "image" in chunk_data and chunk_data["image"] and chunk_data["image"].get("bytes"):
                        img_bytes = chunk_data["image"]["bytes"]
                        key = hashlib.sha256(img_bytes).hexdigest()[:16]
                        if key not in seen_keys:
                            seen_keys.add(key)
                            images_to_describe.append({
                                "index": i,
                                "bytes": img_bytes,
                                "ext": chunk_data["image"].get("ext", "png")
                            })

                if images_to_describe:
                    with st.spinner("🔍 Running Gemini Vision OCR & Diagram Extraction..."):
                        try:
                            described = describe_images(images_to_describe)
                            desc_map = {d["bytes"]: d["description"] for d in described if "bytes" in d and "description" in d}
                            for chunk_data in chunks:
                                if "image" in chunk_data and chunk_data["image"]:
                                    b = chunk_data["image"].get("bytes")
                                    if b in desc_map:
                                        chunk_data["image"]["description"] = desc_map[b]
                                        chunk_data["text"] += f"\n\n[Extracted OCR & Image Diagram Content:\n{desc_map[b]}]"
                        except Exception as e:
                            logger.warning("Gemini Vision OCR description skipped: %s", e)

                # ── RAG Indexing Step ─────────────────────────────────────
                retriever = None  # ensure always defined before conditional del
                with st.spinner("⚡ Building FAISS Vector Index & RAG Context Store..."):
                    try:
                        retriever = ChunkRetriever(chunks)
                        logger.info("RAG FAISS index built successfully in app.py")
                    except Exception as e:
                        logger.warning("RAG FAISS indexing skipped: %s", e)

                # Release the retriever immediately — it is only needed for
                # context storage and holding it past this point risks C-extension
                # destructor conflicts with Groq/httpx threads in Streamlit.
                if retriever is not None:
                    del retriever

                with st.spinner("🤖 Classifying content layouts (Flowcharts, Tables, Metrics)..."):
                    improved = improve_chunks(chunks)
                    st.session_state.improved_results = improved

                with st.spinner("🧠 Generating quizzes & interleaving checkpoint slides..."):
                    quizzes = generate_quizzes(improved)
                    st.session_state.quizzes = quizzes
                    freq = st.session_state.get("quiz_freq", 4)
                    final_deck = interleave_quizzes_into_slides(improved, quizzes, frequency=freq)
                    st.session_state.final_deck = final_deck

                with st.spinner("📊 Calculating engagement metrics..."):
                    scores = score_all_slides(st.session_state.final_deck)
                    st.session_state.scores = scores

                # session_state.retriever was already deleted above after
                # indexing — no need to delete here (guard for old sessions).
                if "retriever" in st.session_state:
                    del st.session_state["retriever"]

                with st.spinner("📦 Building Animated PPTX Deck..."):
                    try:
                        st.session_state.pptx_bytes = build_pptx_safe(
                            st.session_state.final_deck,
                            topic_title=file_name,
                            theme_id=active_theme
                        )
                    except Exception as e:
                        logger.error("PPTX build failed: %s", e)
                        st.session_state.pptx_bytes = None

                with st.spinner("🌐 Building Interactive HTML Web Deck..."):
                    try:
                        st.session_state.html_bytes = build_html_safe(
                            st.session_state.final_deck,
                            topic_title=file_name,
                            theme_id=active_theme
                        )
                    except Exception as e:
                        logger.error("HTML build failed: %s", e)
                        st.session_state.html_bytes = None

                st.session_state.processing_time = round(time.time() - t_start, 1)
                st.success(f"✅ Done! Processed in {st.session_state.processing_time}s — scroll down for your deck.")
                # NOTE: No st.rerun() — results section renders immediately below from session_state

            except Exception as e:
                logger.error("Processing failed: %s", e, exc_info=True)
                st.error(f"⚠️ Processing failed: {e}")

# ── Results & Exporters ──────────────────────────────────────────────────────
if st.session_state.final_deck:
    deck = st.session_state.final_deck
    _dl_name = st.session_state.file_name or "presentation"
    st.markdown("## 📥 Download Your Presentation")

    col_dl1, col_dl2 = st.columns(2)

    with col_dl1:
        if st.session_state.pptx_bytes:
            st.download_button(
                label="📥 Download Animated PPTX (.pptx)",
                data=st.session_state.pptx_bytes,
                file_name=f"Learnova_Visual_{_dl_name}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
        else:
            st.warning("⚠️ PPTX build failed – see logs for details.")

    with col_dl2:
        if st.session_state.html_bytes:
            st.download_button(
                label="🌐 Download Interactive Web Deck (.html)",
                data=st.session_state.html_bytes,
                file_name=f"Learnova_Interactive_{_dl_name}.html",
                mime="text/html"
            )
        else:
            st.warning("⚠️ HTML build failed – see logs for details.")

    st.divider()

    tab_slides, tab_quizzes, tab_scores = st.tabs(
        ["📄 Visual Deck Slides", "🧠 Interleaved Quizzes", "📊 Engagement Dashboard"]
    )

    scores_data = st.session_state.scores or {"slide_scores": [], "overall_score": 0}
    scores_list = scores_data.get("slide_scores", [])

    # ── Tab 1: Visual Deck Slides ────────────────────────────────────────────
    with tab_slides:
        st.subheader(f"🎨 Redesigned Visual Deck ({len(deck)} Slides)")

        for idx, entry in enumerate(deck):
            orig = entry.get("original", {})
            imp = entry.get("improved", {})

            l_type = imp.get("layout_type", "MINIMAL_TEXT").upper()
            title = imp.get("title", f"Slide {idx + 1}")
            takeaway = imp.get("takeaway", "")

            # Badge styling
            badge_color = "#1e2761"
            if l_type == "FLOWCHART":
                badge_color = "#28a745"
            elif l_type == "TABLE":
                badge_color = "#17a2b8"
            elif l_type == "METRIC":
                badge_color = "#fd7e14"
            elif l_type == "CARD_GRID":
                badge_color = "#e83e8c"
            elif l_type == "QUIZ":
                badge_color = "#6f42c1"

            col_a, col_b = st.columns([1, 2])

            with col_a:
                st.markdown(f"**Source / Original Context**")
                st.markdown(f"<div style='background:#f4f4f4; padding:10px; border-left:3px solid #000;'>{orig.get('text', orig.get('title', 'N/A'))}</div>", unsafe_allow_html=True)
                if "image" in orig and orig["image"] and orig["image"].get("description"):
                    st.markdown(f"🖼️ *Image Description:* {orig['image']['description']}")

            with col_b:
                st.markdown(
                    f"### {title} &nbsp; <span style='background:{badge_color}; color:#fff; padding:3px 8px; font-size:0.8rem;'>{l_type}</span>",
                    unsafe_allow_html=True
                )

                if l_type == "FLOWCHART" and "mermaid_code" in imp:
                    m_code = imp["mermaid_code"]
                    # Render visual flowchart pills
                    st.markdown("**🔄 Process / Flowchart Sequence:**")
                    steps = imp.get("bullets", [])
                    if steps:
                        flow_html = " &nbsp;➔&nbsp; ".join(
                            f"<span style='background:#17a2b8; color:#fff; padding:4px 10px; border-radius:12px; font-weight:600;'>{s}</span>"
                            for s in steps
                        )
                        st.markdown(f"<div style='margin-bottom:12px;'>{flow_html}</div>", unsafe_allow_html=True)
                    with st.expander("📐 View Diagram Definition"):
                        st.code(m_code, language="text")

                elif l_type == "TABLE" and "table_headers" in imp:
                    headers = imp.get("table_headers", [])
                    rows = imp.get("table_rows", [])
                    if headers and rows:
                        df = pd.DataFrame(rows, columns=headers)
                        st.dataframe(df, use_container_width=True)

                elif l_type == "METRIC":
                    m_val = imp.get("metric_value", "100%")
                    m_lbl = imp.get("metric_label", title)
                    m_desc = imp.get("metric_desc", takeaway)
                    st.markdown(
                        f"<div style='background:#1e2761; color:#ccff00; padding:20px; border-radius:8px; text-align:center;'>"
                        f"<h1 style='color:#ccff00; margin:0;'>{m_val}</h1>"
                        f"<h4>{m_lbl}</h4>"
                        f"<p style='color:#fff;'>{m_desc}</p>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                elif l_type == "CARD_GRID":
                    bullets = imp.get("bullets", [])
                    c_num = min(len(bullets), 4) or 1
                    cols = st.columns(c_num)
                    for b_idx, bullet in enumerate(bullets[:4]):
                        with cols[b_idx % c_num]:
                            st.markdown(
                                f"<div style='background:#f0f4ff; border:2px solid #1e2761; border-radius:8px; padding:12px; height:100%;'>"
                                f"<h5 style='color:#1e2761; margin:0;'>Pillar {b_idx + 1}</h5>"
                                f"<p style='color:#333; font-size:0.9rem; margin-top:5px;'>{bullet}</p>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

                elif l_type == "QUIZ":
                    st.markdown(f"**❓ Question:** {imp.get('question', '')}")
                    for opt in imp.get('options', []):
                        st.markdown(f"- {opt}")
                    st.markdown(f"**✅ Correct Answer:** `{imp.get('correct', 'A')}`")

                else:
                    for b in imp.get("bullets", []):
                        st.markdown(f"- {b}")

                if takeaway:
                    st.markdown(f"💡 **Takeaway:** *{takeaway}*")

            st.divider()

    # ── Tab 2: Quizzes ───────────────────────────────────────────────────────
    with tab_quizzes:
        quizzes = st.session_state.quizzes or []
        if not quizzes:
            st.info("No quizzes generated.")
        else:
            st.subheader(f"🧠 {len(quizzes)} Interleaved Checkpoint Quizzes")
            for q_idx, quiz in enumerate(quizzes):
                st.markdown(f"**Q{q_idx + 1}: {quiz['question']}**")
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
            df_scores = pd.DataFrame([
                {"Slide": f"Slide {i+1}", "Score": s["score"], **s["breakdown"]}
                for i, s in enumerate(scores_list)
            ])
            st.dataframe(df_scores, use_container_width=True)
