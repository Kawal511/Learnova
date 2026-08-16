import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "../api";
import Footer from "../components/Footer.jsx";
import Navbar from "../components/Navbar.jsx";
import PalettePicker, { PRESETS } from "../components/PalettePicker.jsx";
import SlideCard from "../components/SlideCard.jsx";
import StageProgress from "../components/StageProgress.jsx";

const POLL_MS = 700;

export default function Studio() {
  const [stages, setStages] = useState([]);
  const [fonts, setFonts] = useState([{ id: "bebas_inter", label: "Bebas Neue + Inter" }]);
  const [densities, setDensities] = useState([]);
  const [job, setJob] = useState(null);
  const [markdown, setMarkdown] = useState("");
  const [sectionCount, setSectionCount] = useState(0);
  const [deck, setDeck] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("upload");
  const [typedText, setTypedText] = useState("");

  const [palette, setPalette] = useState(PRESETS[0]);
  const [fontId, setFontId] = useState("bebas_inter");
  const [density, setDensity] = useState("medium");
  const [quizFreq, setQuizFreq] = useState(4);
  const [ocr, setOcr] = useState(true);

  const pollRef = useRef(null);

  useEffect(() => {
    api.health().then((h) => setStages(h.stages)).catch(() => {});
    api
      .listThemes()
      .then((t) => {
        if (t.fonts?.length) setFonts(t.fonts);
        if (t.densities?.length) setDensities(t.densities);
      })
      .catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  const loadMarkdown = useCallback(async (id) => {
    const md = await api.getMarkdown(id);
    setMarkdown(md.markdown);
    setSectionCount(md.section_count);
  }, []);

  const poll = useCallback((id, onSettled) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const next = await api.getJob(id);
        setJob(next);
        if (["awaiting_review", "done", "failed"].includes(next.status)) {
          clearInterval(pollRef.current);
          setBusy(false);
          if (next.status === "failed") setError(next.error || "job failed");
          else onSettled?.(next);
        }
      } catch (e) {
        clearInterval(pollRef.current);
        setBusy(false);
        setError(e.message);
      }
    }, POLL_MS);
  }, []);

  async function onUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setDeck(null);
    setBusy(true);
    try {
      const created = await api.uploadDocument(file);
      setJob(created);
      poll(created.id, (settled) => loadMarkdown(settled.id));
    } catch (e) {
      setBusy(false);
      setError(e.message);
    }
  }

  async function onUseTyped() {
    if (!typedText.trim()) return;
    setError("");
    setDeck(null);
    setBusy(true);
    try {
      const created = await api.createTypedJob(typedText, "Typed Syllabus");
      setJob(created);
      await loadMarkdown(created.id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function onGenerate() {
    if (!job) return;
    setError("");
    setBusy(true);
    try {
      await api.saveMarkdown(job.id, markdown);
      await api.startGenerate(job.id, {
        theme_id: "auto",
        theme_spec: {
          primary: palette.primary,
          secondary: palette.secondary,
          background: palette.background,
          font_id: fontId,
          name: "Custom Palette",
        },
        quiz_frequency: Number(quizFreq),
        enable_vision_ocr: ocr,
        text_density: density,
        markdown,
      });
      poll(job.id, async (settled) => {
        if (settled.status === "done") setDeck(await api.getDeck(settled.id));
      });
    } catch (e) {
      setBusy(false);
      setError(e.message);
    }
  }

  async function download(artifact) {
    try {
      await api.downloadArtifact(
        api.jobDownloadPath(job.id, artifact),
        `Learnova_${job.source_name || "deck"}.${artifact}`
      );
    } catch (e) {
      setError(e.message);
    }
  }

  const reviewing = job && ["awaiting_review", "done", "running"].includes(job.status);

  return (
    <>
      <Navbar variant="solid" />

      <main className="shell">
        <div className="kicker">// STUDIO</div>
        <h1 className="display" style={{ fontSize: "clamp(2.2rem,5vw,3.6rem)", marginBottom: 30 }}>BUILD A <span className="outline-word">DECK</span>
        </h1>

        {error ? <div className="error">{error}</div> : null}

        {/* 1 — input */}
        <section className="panel">
          <h2>1 · Provide your content</h2>

          <div className="tabs">
            <button
              className="tab"
              aria-selected={tab === "upload"}
              onClick={() => setTab("upload")}
              type="button"
            >Upload file
            </button>
            <button
              className="tab"
              aria-selected={tab === "typed"}
              onClick={() => setTab("typed")}
              type="button"
            >Type a syllabus
            </button>
          </div>

          {tab === "upload" ? (
            <label className="file-btn">Choose PPTX / PDF
              <input type="file" accept=".pptx,.pdf" onChange={onUpload} hidden />
            </label>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <textarea
                rows={6}
                placeholder={"## Chapter 1: Introduction\n- Step 1: ...\n- Step 2: ..."}
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
              />
              <button
                className="btn btn-sm btn-accent"
                onClick={onUseTyped}
                disabled={busy || !typedText.trim()}
                type="button"
                style={{ alignSelf: "flex-start" }}
              >Use this text
              </button>
            </div>
          )}
        </section>

        {job ? (
          <section className="panel">
            <h2>Pipeline</h2>
            <StageProgress
              stages={stages}
              current={job.stage}
              currentStatus={job.stage_status}
              progress={job.progress}
            />
            <p className="muted" style={{ marginTop: 10 }}>status: <strong>{job.status}</strong>
              {job.detail ? ` · ${job.detail}` : ""}
            </p>
          </section>
        ) : null}

        {reviewing ? (
          <>
            {/* 2 — markdown */}
            <section className="panel">
              <h2>2 · Review &amp; edit the markdown</h2>
              <p className="muted">This is what the pipeline reasons over — edits here change the deck.{" "}
                {sectionCount} section(s) detected.
              </p>
              <textarea
                className="md-editor"
                value={markdown}
                onChange={(e) => setMarkdown(e.target.value)}
                spellCheck={false}
              />
            </section>

            {/* 3 — density */}
            <section className="panel">
              <h2>3 · How much text per slide?</h2>
              <p className="muted">
                Content is never dropped. At a lighter setting the same material is
                spread across more slides, numbered so the run reads continuously.
              </p>
              <div className="density-grid">
                {densities.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className="density-option"
                    aria-pressed={density === option.id}
                    onClick={() => setDensity(option.id)}
                  >
                    <span className="density-label">{option.label}</span>
                    <span className="density-desc">{option.description}</span>
                    <span className="density-meta">
                      up to {option.max_bullets} bullets ·{" "}
                      {option.max_words_per_bullet} words each
                      {option.includes_enhancement ? " · adds examples" : ""}
                    </span>
                  </button>
                ))}
              </div>
            </section>

            {/* 4 — design */}
            <section className="panel">
              <h2>4 · Choose your palette &amp; type</h2>
              <PalettePicker
                palette={palette}
                onChange={setPalette}
                fonts={fonts}
                fontId={fontId}
                onFontChange={setFontId}
              />

              <div className="controls">
                <label>Quiz every
                  <input
                    type="number"
                    min={2}
                    max={6}
                    value={quizFreq}
                    onChange={(e) => setQuizFreq(e.target.value)}
                    style={{ width: 62 }}
                  />slides
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={ocr}
                    onChange={(e) => setOcr(e.target.checked)}
                  />Vision OCR
                </label>
                <button
                  className="btn btn-accent"
                  onClick={onGenerate}
                  disabled={busy}
                  type="button"
                >
                  {busy ? "GENERATING…" : "GENERATE DECK"}
                </button>
              </div>
            </section>
          </>
        ) : null}

        {deck ? (
          <section className="panel">
            <h2>5 · Your deck</h2>
            <div className="summary">
              <div>
                <strong>{deck.summary.slide_count}</strong>
                <span>slides</span>
              </div>
              <div>
                <strong>{deck.summary.quiz_count}</strong>
                <span>quizzes</span>
              </div>
              <div>
                <strong>{deck.summary.overall_score}</strong>
                <span>/100 engagement</span>
              </div>
              <div>
                <strong>{deck.summary.total_seconds}s</strong>
                <span>total</span>
              </div>
            </div>

            <div className="downloads">
              <button className="file-btn" type="button" onClick={() => download("pptx")}>Download PPTX
              </button>
              <button className="file-btn" type="button" onClick={() => download("html")}>Download Web Deck
              </button>
            </div>

            <p className="muted" style={{ marginBottom: 18 }}>Saved to your library — find it under <strong>My Decks</strong>.
            </p>

            <div className="slides">
              {deck.slides.map((slide) => (
                <SlideCard key={slide.index} slide={slide} />
              ))}
            </div>
          </section>
        ) : null}
      </main>

      <Footer />
    </>
  );
}
