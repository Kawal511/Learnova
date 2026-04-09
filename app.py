"""
Learnova – AI Presentation Engine
Streamlit UI with AI-improved slides, quizzes, and engagement scoring.
"""

import os
import tempfile
import time

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from parsers.ppt_parser import parse_ppt
from parsers.pdf_parser import parse_pdf, parse_textbook_pdf
from rag.chunker import chunk_parsed_data
from ai.improver import improve_chunks
from ai.quiz_gen import generate_quizzes
from utils.scorer import score_all_slides
from utils.ppt_builder import build_pptx
from ai.image_describer import describe_images
from logger import logger

# Load environment variables
load_dotenv()

MAX_FILE_SIZE_MB = 10

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

/* Default text and backgrounds */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* Custom dot cursor universally */
* {
    cursor: url('data:image/svg+xml;utf8,<svg width="12" height="12" viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg"><circle cx="6" cy="6" r="6" fill="%23ccff00" stroke="black" stroke-width="1"/></svg>') 6 6, auto !important;
}

/* Larger cursor on hoverable elements (native cursors jump in size instantly) */
button:hover, p:hover, li:hover, h1:hover, h2:hover, h3:hover, h4:hover, h5:hover, h6:hover, a:hover, [data-testid="stExpander"] details:hover, [data-baseweb="tab"]:hover {
    cursor: url('data:image/svg+xml;utf8,<svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg"><circle cx="9" cy="9" r="8" fill="%23ccff00" stroke="black" stroke-width="1.5"/></svg>') 9 9, auto !important;
}

/* Background grid styling */
.stApp {
    background-color: #ffffff;
    background-image: radial-gradient(#e0e0e0 2px, transparent 2px);
    background-size: 30px 30px;
}

/* Headers */
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

/* Streamlit Buttons wrapper and buttons */
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

.stButton > button:active, .stDownloadButton > button:active, .stFormSubmitButton > button:active {
    transform: translate(6px, 6px) !important;
    box-shadow: 0px 0px 0px #000000 !important;
}

/* File Uploader styling */
[data-testid="stFileUploadDropzone"] {
    background-color: #ffffff !important;
    border: 3px dashed #000000 !important;
    border-radius: 0px !important;
    box-shadow: 6px 6px 0px #000000 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploadDropzone"]:hover {
    background-color: #f7ffcc !important;
}

/* Expanders */
[data-testid="stExpander"] {
    border: none !important;
    background: transparent !important;
}
[data-testid="stExpander"] > details {
    border: 3px solid #000 !important;
    border-radius: 0 !important;
    background-color: #ffffff !important;
    box-shadow: 4px 4px 0px #000 !important;
    margin-bottom: 10px !important;
    color: #000 !important;
    transition: all 0.2s ease !important;
}
[data-testid="stExpander"] > details:hover {
    transform: translate(2px, 2px) !important;
    box-shadow: 2px 2px 0px #000 !important;
}
[data-testid="stExpander"] > details > summary {
    font-family: 'Bebas Neue', cursive !important;
    font-size: 1.5rem !important;
}

/* Tabs */
[data-baseweb="tab-list"] {
    gap: 10px;
    border-bottom: 3px solid #000 !important;
}
[data-baseweb="tab"] {
    background-color: #ffffff !important;
    border: 3px solid #000 !important;
    border-bottom: none !important;
    border-top-left-radius: 0 !important;
    border-top-right-radius: 0 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
    font-size: 1rem !important;
    padding: 10px 20px !important;
    color: #000 !important;
    box-shadow: 4px -4px 0px rgba(0,0,0,0) !important;
    transition: all 0.2s !important;
}
[aria-selected="true"] {
    background-color: #ccff00 !important;
    box-shadow: 4px -4px 0px #000 !important;
    transform: translateY(-4px);
    border-bottom: none !important;
}

/* Text Inputs / Textareas / Radio Buttons */
input[type="text"], input[type="number"], .stTextArea textarea {
    border: 3px solid #000 !important;
    border-radius: 0 !important;
    box-shadow: 4px 4px 0px rgba(0,0,0,0.1) !important;
}
input[type="text"]:focus, .stTextArea textarea:focus {
    box-shadow: 4px 4px 0px #ccff00 !important;
    border-color: #000 !important;
}

/* Explicitly force radio button text (options) to be black */
div[role="radiogroup"] label, 
[data-testid="stRadio"] p,
[data-testid="stRadio"] div[data-baseweb="radio"] div {
    color: #000000 !important;
    font-weight: 600 !important;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #000000 !important;
    color: #ffffff !important;
    border-right: 5px solid #ccff00 !important;
}
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown {
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stButton > button {
    background-color: #ffffff !important;
    color: #000000 !important;
    box-shadow: 4px 4px 0px #ccff00 !important;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    color: #000000 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    box-shadow: 2px 2px 0px #ccff00 !important;
    transform: translate(2px, 2px) !important;
}

/* Divider */
hr {
    border-top: 3px solid #000 !important;
}
[data-testid="stSidebar"] hr {
    border-top: 3px solid #ccff00 !important;
}

/* Badges / Metrics */
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #ccff00 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Bebas Neue', cursive !important;
    color: #000000 !important;
    font-size: 3rem !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 800 !important;
    text-transform: uppercase !important;
}

/* Altair / Vega chart container – force white background */
[data-testid="stVegaLiteChart"],
[data-testid="stVegaLiteChart"] canvas,
[data-testid="stVegaLiteChart"] > div {
    background-color: #ffffff !important;
    border: 3px solid #000 !important;
    border-radius: 0 !important;
}

/* Dataframe: white bg, black text, neon hover */
[data-testid="stDataFrame"] [data-testid="glideDataEditor"],
[data-testid="stDataFrame"] {
    background-color: #ffffff !important;
    border: 3px solid #000 !important;
    border-radius: 0 !important;
    box-shadow: 4px 4px 0px #000 !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ── Session State Defaults ───────────────────────────────────────────────────
_defaults = {
    "parsed_data": None,
    "file_type": None,
    "file_name": None,
    "improved_results": None,
    "quizzes": None,
    "scores": None,
    "processing_time": None,
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h1 style='font-family: Bebas Neue, cursive; color: #ccff00; "
        "margin-top: -2rem; padding-left: 0; text-align: left; "
        "margin-bottom: 0.2rem;'>LEARNOVA</h1>",
        unsafe_allow_html=True,
    )
    st.header("📖 How It Works")
    st.markdown(
        "1. **Upload** a PPT or PDF file\n"
        "2. **AI extracts** and chunks content\n"
        "3. **Gemini improves** each slide\n"
        "4. **Quizzes & scores** are generated\n"
        "5. **Export** beautifully formatted PPTX"
    )
    st.divider()

    st.header("⚙️ Parsing Mode")
    st.session_state.parsing_mode = st.selectbox("Document Style", ["Auto", "PPT / Slides", "Textbook PDF"])
    st.divider()

    # Reset button
    if st.button("🔄 Reset & Start Fresh"):
        for key, val in _defaults.items():
            st.session_state[key] = val
        st.rerun()

    st.divider()

    # Stats (populated after processing)
    if st.session_state.improved_results:
        scores_data = st.session_state.scores or {"scores": [], "average": 0}
        st.header("📈 Session Stats")
        st.metric("Slides Processed", len(st.session_state.improved_results))
        st.metric(
            "Avg Engagement Score",
            f"{scores_data['average']}/100" if scores_data["scores"] else "N/A",
        )
        st.metric("Quizzes Generated", len(st.session_state.quizzes or []))
        if st.session_state.processing_time is not None:
            st.metric("Processing Time", f"⏱ {st.session_state.processing_time}s")

# ── Banner ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background-color: #000; padding: 4px 12px; display: inline-block; margin-bottom: 20px; border-radius: 0px;">
    <span style="color: #ccff00; font-family: 'Inter', sans-serif; font-weight: 800; font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase;">
        ● ENHANCE YOUR PPT
    </span>
</div>
""", unsafe_allow_html=True)
st.title("LEARNOVA")
st.markdown("*Learnova converts static documents into confident, smart, and interactive learning real-time decisions. AI-powered slide generation, quiz scoring, and content intelligence.*")
st.divider()

# ── Check GEMINI_API_KEY ─────────────────────────────────────────────────────
if not os.getenv("GEMINI_API_KEY"):
    st.error("⚠️ **GEMINI_API_KEY** not found in `.env` file. "
             "Please add it and restart the app.")
    st.stop()

# ── File Uploader ────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pptx", "pdf"],
    help="Supported formats: .pptx, .pdf (max 10 MB)",
)

if uploaded_file is None:
    st.markdown(
        """
        <div style="background-color: #f7ffcc; padding: 15px; border: 3px solid #000; border-radius: 0px; box-shadow: 4px 4px 0px #000; margin-top: 20px;">
            <h4 style="color: #000; margin: 0; font-family: 'Inter', sans-serif;">👆 Upload a PPT or PDF to get started</h4>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.stop()

# ── File size check ──────────────────────────────────────────────────────────
file_size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
if file_size_mb > MAX_FILE_SIZE_MB:
    st.error(f"⚠️ File is too large ({file_size_mb:.1f} MB). "
             f"Maximum allowed is {MAX_FILE_SIZE_MB} MB.")
    st.stop()

file_name = uploaded_file.name
file_ext = os.path.splitext(file_name)[1].lower()

# Reset state when a new file is uploaded
if st.session_state.file_name != file_name:
    for key, val in _defaults.items():
        st.session_state[key] = val
    st.session_state.file_name = file_name
    st.session_state.file_type = file_ext

# ── Parse (only once per file) ───────────────────────────────────────────
if st.session_state.parsed_data is None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    try:
        parsed_obj = None
        if file_ext == ".pptx":
            parsed_obj = parse_ppt(tmp_path)
        elif file_ext == ".pdf":
            if st.session_state.get("parsing_mode") == "Textbook PDF":
                parsed_obj = parse_textbook_pdf(tmp_path)
            else:
                parsed_obj = parse_pdf(tmp_path)
        else:
            st.error("Unsupported file type.")
            
        if parsed_obj:
            # Convert to list of dicts for UI compatibility
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
            
    except ValueError as ve:
        logger.error("Parsing error for %s: %s", file_name, ve, exc_info=True)
        st.error(f"⚠️ Parsing error: {ve}")
    except Exception as e:
        logger.error("Unexpected error for %s: %s", file_name, e, exc_info=True)
        st.error(f"⚠️ An unexpected error occurred: {e}")
    finally:
        os.unlink(tmp_path)

parsed = st.session_state.parsed_data

# ── Show extracted content + improve button ──────────────────────────────
if parsed:
    is_ppt = st.session_state.file_type == ".pptx"
    label = "Slide" if is_ppt else "Page"
    count = len(parsed)

    st.subheader(f"{'📊' if is_ppt else '📄'} Extracted Content")
    for item in parsed:
        num = item.get("slide") or item.get("page")
        title = item.get("title") or item.get("heading", "")
        with st.expander(f"{label} {num}: {title}"):
            content = item.get("content", "")
            if isinstance(content, list):
                for bullet in (content or []):
                    st.markdown(f"- {bullet}")
                if not content:
                    st.markdown("<span style='color:black;'>(No bullet content)</span>", unsafe_allow_html=True)
            else:
                st.markdown(content if content else "(No text content)")

    st.markdown(
        f"""
        <div style="background-color: #d4edda; padding: 15px; border: 3px solid #000; border-radius: 0px; box-shadow: 4px 4px 0px #000; margin-top: 10px; margin-bottom: 20px;">
            <h4 style="color: #000; margin: 0; font-family: 'Inter', sans-serif;">✅ Extracted <b>{count}</b> {label.lower()}(s) from <code>{file_name}</code>.</h4>
        </div>
        """, 
        unsafe_allow_html=True
    )
    st.divider()

    # ── AI Improve + Quiz + Score Button ─────────────────────────────────
    if st.session_state.improved_results is None:
        if st.button("✨ Improve with AI, Generate Quizzes & Score"):
            t_start = time.time()
            try:
                chunks = chunk_parsed_data(parsed)
                
                # Intercept Pipeline to Describe Images!
                images_to_describe = []
                seen_image_keys = set()
                for i, chunk_data in enumerate(chunks):
                    if "image" in chunk_data and chunk_data["image"]:
                        img_key = len(chunk_data["image"]["bytes"])
                        if img_key not in seen_image_keys:
                            seen_image_keys.add(img_key)
                            images_to_describe.append({
                                "index": i,
                                "bytes": chunk_data["image"]["bytes"],
                                "ext": chunk_data["image"].get("ext", "png")
                            })
                
                if images_to_describe:
                    with st.spinner(f"🔍 Analyzing {len(images_to_describe)} unique images with Gemini Vision..."):
                        described_data = describe_images(images_to_describe)
                        # Build a lookup: image bytes size -> description
                        desc_lookup = {}
                        for d in described_data:
                            desc_lookup[id(d["bytes"])] = d["description"]
                        # Also build lookup by bytes content (for cross-reference)
                        desc_by_content = {}
                        for d in described_data:
                            desc_by_content[d["bytes"]] = d["description"]

                        # Write descriptions into chunks (for the AI improver context)
                        for chunk_data in chunks:
                            if "image" in chunk_data and chunk_data["image"]:
                                img_bytes = chunk_data["image"].get("bytes")
                                desc = desc_by_content.get(img_bytes)
                                if desc:
                                    chunk_data["image"]["description"] = desc
                                    chunk_data["text"] = chunk_data["text"] + "\n\n[Visual Image Context: " + desc + "]"

                        # CRITICAL: Also write descriptions back to the parsed list
                        # so the frontend's original["image"]["description"] check works
                        for item in parsed:
                            if "image" in item and item["image"]:
                                img_bytes = item["image"].get("bytes")
                                desc = desc_by_content.get(img_bytes)
                                if desc:
                                    item["image"]["description"] = desc

                st.info(f"📄 Processing {len(chunks)} page(s)/chunks... This may take a moment for large documents.")
                with st.spinner("🤖 Learnova is improving your slides..."):
                    st.session_state.improved_results = improve_chunks(chunks)
            except Exception as e:
                logger.error("AI improvement failed: %s", e, exc_info=True)
                st.error(f"⚠️ AI improvement failed: {e}")

            if st.session_state.improved_results:
                with st.spinner("🧠 Generating quizzes..."):
                    try:
                        st.session_state.quizzes = generate_quizzes(
                            st.session_state.improved_results
                        )
                    except Exception as e:
                        logger.error("Quiz generation failed: %s", e, exc_info=True)
                        st.error(f"⚠️ Quiz generation failed: {e}")

                with st.spinner("📊 Computing engagement scores..."):
                    try:
                        st.session_state.scores = score_all_slides(
                            st.session_state.improved_results
                        )
                    except Exception as e:
                        logger.error("Scoring failed: %s", e, exc_info=True)
                        st.error(f"⚠️ Scoring failed: {e}")

            st.session_state.processing_time = round(time.time() - t_start, 1)
            st.rerun()

# ── Tabbed Results ───────────────────────────────────────────────────────
if st.session_state.improved_results:
    st.markdown("## 📥 Download Your Presentation")
    
    with st.spinner("📦 Generating .pptx file..."):
        # Make sure that image dictionary persists for ppt_builder
        for data in st.session_state.improved_results:
            orig = data["original"]
            img = orig.get("image")
            if img:
                data["original"]["image"] = img

        pptx_bytes = build_pptx(st.session_state.improved_results, topic_title=file_name)
    
    st.download_button(
        label="Download Midnight Executive .pptx",
        data=pptx_bytes,
        file_name=f"Learnova_{file_name}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    st.divider()

    tab_slides, tab_quizzes, tab_scores = st.tabs(
        ["📄 Improved Slides", "🧠 Quizzes", "📊 Engagement Score"]
    )

    scores_data = st.session_state.scores or {"scores": [], "average": 0}
    scores_list = scores_data["scores"]

    # ── Tab 1: Improved Slides ───────────────────────────────────────────
    with tab_slides:
        st.subheader("🚀 Original vs AI-Improved")

        for idx, entry in enumerate(st.session_state.improved_results):
            original = entry["original"]
            improved = entry["improved"]

            # Score badge
            slide_score = scores_list[idx]["score"] if idx < len(scores_list) else 0
            if slide_score > 75:
                badge = f"🟢 {slide_score}/100"
            elif slide_score >= 50:
                badge = f"🟡 {slide_score}/100"
            else:
                badge = f"🔴 {slide_score}/100"

            col_orig, col_improved = st.columns(2)

            with col_orig:
                st.markdown(f"<p style='color:black; font-weight:bold;'>📝 Original — {original['title']}</p>", unsafe_allow_html=True)
                st.markdown(
                    f"<div style='background:#f8f9fa;color:#1a1a1a;padding:12px;"
                    f"border-radius:8px'>{original['text']}</div>",
                    unsafe_allow_html=True,
                )
                # Show image description if parsed!
                if "image" in original and original["image"] is not None and "description" in original["image"]:
                    st.markdown(
                        f"<div style='background:#e0f7fa;color:#0056b3;padding:12px;margin-top:8px;"
                        f"border-radius:8px;'><b>🖼️ Image Description:</b><br>{original['image']['description']}</div>",
                        unsafe_allow_html=True,
                    )

            with col_improved:
                st.markdown(
                    f"<p style='color:black; font-weight:bold;'>✨ Improved — {improved.get('title', '')} &nbsp; <code>{badge}</code></p>",
                    unsafe_allow_html=True
                )
                bullets_md = "".join(
                    f"<li>{b}</li>" for b in improved.get("bullets", [])
                )
                takeaway = improved.get("takeaway", "")
                st.markdown(
                    f"<div style='background:#e8f5e9;color:#1a1a1a;padding:12px;"
                    f"border-radius:8px'><ul>{bullets_md}</ul>"
                    f"{'<br><b>💡 Takeaway:</b> ' + takeaway if takeaway else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.divider()

    # ── Tab 2: Quizzes ───────────────────────────────────────────────────
    with tab_quizzes:
        quizzes = st.session_state.quizzes or []
        if not quizzes:
            st.info("No quizzes were generated.")
        else:
            st.subheader(f"🧠 {len(quizzes)} Quiz Question(s)")

            for q_idx, quiz in enumerate(quizzes):
                st.markdown(f"<p style='color:black; font-weight:bold; font-size:1.1rem;'>Q{q_idx + 1}: {quiz['question']}</p>", unsafe_allow_html=True)
                st.markdown(
                    f"<p style='color:#333; font-size:0.9rem;'><i>Based on slides: {', '.join(str(s) for s in quiz.get('source_slides', []))}</i></p>",
                    unsafe_allow_html=True
                )

                # Radio for options
                answer_key = f"quiz_answer_{q_idx}"
                st.radio(
                    "Select your answer:",
                    quiz.get("options", []),
                    key=answer_key,
                    label_visibility="collapsed",
                )

                # Reveal button
                reveal_key = f"reveal_{q_idx}"
                if st.button(f"Reveal Answer (Q{q_idx + 1})", key=reveal_key):
                    correct = quiz.get("correct", "")
                    explanation = quiz.get("explanation", "")
                    st.markdown(f"<div style='background-color:#d4edda;padding:10px;border-radius:5px;color:black;'><strong>✅ Correct Answer: {correct}</strong></div>", unsafe_allow_html=True)
                    if explanation:
                        st.markdown(f"<div style='background-color:#d1ecf1;padding:10px;border-radius:5px;color:black;'>💡 {explanation}</div>", unsafe_allow_html=True)

                st.divider()

    # ── Tab 3: Engagement Scores ─────────────────────────────────────────
    with tab_scores:
        if not scores_list:
            st.info("No scores computed.")
        else:
            st.subheader("📊 Engagement Score Dashboard")

            # Overall metric
            avg_score = scores_data["average"]
            st.metric("Overall Engagement Score", f"{avg_score} / 100")
            st.divider()

            # Bar chart of per-slide scores
            chart_data = pd.DataFrame({
                "Slide": [s["slide_title"][:30] for s in scores_list],
                "Score": [s["score"] for s in scores_list],
            })
            bar_chart = alt.Chart(chart_data).mark_bar(
                color="#ccff00",
                stroke="#000000",
                strokeWidth=2,
            ).encode(
                x=alt.X("Slide:N", sort=None, axis=alt.Axis(
                    labelAngle=-45, labelColor="#000", titleColor="#000",
                    labelFont="Inter", titleFont="Inter", titleFontWeight="bold",
                    gridColor="#e0e0e0",
                )),
                y=alt.Y("Score:Q", scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(
                    labelColor="#000", titleColor="#000",
                    labelFont="Inter", titleFont="Inter", titleFontWeight="bold",
                    gridColor="#e0e0e0",
                )),
                tooltip=["Slide", "Score"],
            ).properties(
                height=350,
            ).configure_view(
                strokeWidth=0,
                fill="#ffffff",
            ).configure(
                background="#ffffff",
            )
            st.altair_chart(bar_chart, use_container_width=True, theme=None)
            st.divider()

            # Breakdown table
            st.markdown("**Per-Slide Breakdown**")
            rows = []
            for s in scores_list:
                row = {"Slide": s["slide_title"][:40], "Score": s["score"]}
                row.update(s["breakdown"])
                rows.append(row)
            df_breakdown = pd.DataFrame(rows)
            df_breakdown.index = df_breakdown.index + 1
            st.dataframe(df_breakdown, use_container_width=True)
