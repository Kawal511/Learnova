import { Link } from "react-router-dom";
import Footer from "../components/Footer.jsx";
import Marquee from "../components/Marquee.jsx";
import Navbar from "../components/Navbar.jsx";

const MARQUEE_TOP = [
  "PPTX PARSING",
  "PDF EXTRACTION",
  "MARKDOWN IR",
  "FLOWCHART ENGINE",
  "VISION OCR",
  "INTERLEAVED QUIZZES",
];

const MARQUEE_BOTTOM = [
  "10 DESIGN THEMES",
  "CUSTOM PALETTES",
  "SMARTART SPECS",
  "KPI CALLOUTS",
  "REVEAL.JS DECKS",
  "ANIMATED PPTX",
];

const PILLARS = [
  ["INTELLIGENCE ENGINE", "20 concept types, zero LLM calls"],
  ["LAYOUT ROUTER", "Flowchart · Table · Metric · Grid"],
  ["IMAGE ANCHORING", "Figures matched to their own section"],
  ["DUAL EXPORT", "Animated PPTX + interactive web deck"],
];

const FEATURES = [
  ["UNIFIED EXTRACTION", "PPTX and PDF converge on one markdown representation — tables, SmartArt, charts, equations and speaker notes included."],
  ["EDITABLE MARKDOWN", "Review and rewrite the extracted content before anything expensive runs. What you edit is what gets built."],
  ["FLOWCHART DETECTION", "Ordered steps are detected in your text and rendered as real node-and-edge diagrams, not placeholder boxes."],
  ["KPI CALLOUTS", "Numeric findings become metric slides using the actual figure pulled from your content."],
  ["CUSTOM PALETTES", "Pick primary and secondary colours plus a font pairing. Both flow into the PPTX and the web deck."],
  ["INTERLEAVED QUIZZES", "Checkpoint questions are generated and dropped in every N slides to drive active recall."],
  ["VISION OCR", "Scanned pages and embedded diagrams are read with Gemini Vision, falling back to local Tesseract on quota limits."],
  ["ENGAGEMENT SCORING", "Every slide is scored on density, structure and readability so you can see what still needs work."],
];

const STATS = [
  ["10", "Design Themes"],
  ["16", "Visual Types"],
  ["20", "Concept Extractors"],
  ["0", "Keys Required"],
];

export default function Landing() {
  return (
    <>
      <Navbar />

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section id="hero" className="hero dotgrid">
        <div className="watermark hero-watermark">LEARNOVA</div>

        <div className="hero-badge">
          <span className="dot" />
          <span className="eyebrow">AI PRESENTATION ENGINE</span>
        </div>

        <h1 className="display hero-title">
          <span className="line">BORING</span>
          <span className="line outline-word">DECKS</span>
          <span className="line">REBUILT</span>
        </h1>

        <p className="hero-copy">Learnova turns text-heavy PPTs, PDFs and raw syllabi into structured visual
          presentations — flowcharts, comparison tables, metric cards and interleaved
          quizzes — generated programmatically, with AI only where it earns its place.
        </p>

        <div className="hero-cta">
          <Link to="/studio" className="btn btn-accent">OPEN STUDIO
          </Link>
          <a href="#features" className="btn">SEE FEATURES
          </a>
        </div>
      </section>

      {/* ── Dual marquees ────────────────────────────────────────────────── */}
      <Marquee items={MARQUEE_TOP} variant="dark" />
      <Marquee items={MARQUEE_BOTTOM} variant="accent" reverse />

      {/* ── Intro ────────────────────────────────────────────────────────── */}
      <section id="intro" className="section section-dark dotgrid on-dark">
        <div className="watermark on-dark" style={{ left: "-2vw", bottom: "-4vh", fontSize: "clamp(4rem,14vw,12rem)" }}>INTRO
        </div>

        <div className="intro-grid">
          <div>
            <div className="kicker on-dark">// JUST AN INTRO</div>
            <h2 className="display section-title">YOUR SLIDE
              <br />
              <span className="outline-word">REDESIGN</span>
              <br />ENGINE.
            </h2>
            <p className="intro-copy">Unlike template galleries, Learnova reads your <strong>content</strong>. It
              extracts steps, statistics, comparisons and hierarchies, then decides which
              visual each one deserves — and builds it. Upload a deck, paste a syllabus,
              or drop in a textbook PDF.
            </p>
            <Link to="/studio" className="btn btn-accent" style={{ marginTop: 26 }}>START BUILDING
            </Link>
          </div>

          <div className="stack">
            {PILLARS.map(([title, sub], i) => (
              <div className="stack-card" key={title}>
                <span className="stack-icon">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <div className="stack-title">{title} +</div>
                  <div className="stack-sub">{sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────────── */}
      <section id="features" className="section">
        <div className="section-head">
          <div>
            <div className="kicker">// ALL MODULES</div>
            <h2 className="display section-title">CAPABI<span className="outline-word">LITIES</span>
            </h2>
          </div>
          <div className="section-note">
            <span>Eight modules engineered for educators, students and analysts.</span>
          </div>
        </div>

        <div className="feature-grid">
          {FEATURES.map(([title, text], i) => {
            // Checkerboard: alternate fill by row parity, as in the reference.
            const row = Math.floor(i / 4);
            const on = (i + row) % 2 === 0;
            return (
              <div key={title} className={`feature-cell ${on ? "on" : "off"}`}>
                <span className="feature-icon">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="feature-title">{title}</h3>
                <p className="feature-text">{text}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Stats ────────────────────────────────────────────────────────── */}
      <section id="stats" className="section" style={{ paddingTop: 0 }}>
        <div className="kicker">// BY THE NUMBERS</div>
        <h2 className="display section-title" style={{ marginBottom: 44 }}>THE <span className="outline-word">NUMBERS</span>
        </h2>
        <div className="stat-grid">
          {STATS.map(([value, label]) => (
            <div className="stat" key={label}>
              <div className="stat-value">{value}</div>
              <div className="stat-label">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Contact ──────────────────────────────────────────────────────── */}
      <section id="contact" className="section">
        <div className="contact-grid">
          <div>
            <div className="kicker">// GET IN TOUCH</div>
            <h2 className="display section-title">CONNECT!</h2>
            <p className="muted" style={{ maxWidth: "46ch", marginTop: 18 }}>Whether you're an educator, a student, or evaluating Learnova for your
              institution — we'd like to hear how you'd use it.
            </p>
            <ul className="contact-list">
              <li>Built as an IPD project</li>
              <li>Parsing · Intelligence · Visual Specs · Rendering</li>
              <li>Groq · Gemini · NVIDIA NIM · AnyDoc</li>
            </ul>
            <Marquee
              items={["PARSING", "INTELLIGENCE", "VISUAL SPECS", "RENDERING", "EXPORT"]}
              variant="accent"
            />
          </div>

          <form className="contact-card" onSubmit={(e) => e.preventDefault()}>
            <div className="field">
              <label htmlFor="cname">Name</label>
              <input id="cname" placeholder="Write your name..." />
            </div>
            <div className="field">
              <label htmlFor="cmail">Email</label>
              <input id="cmail" type="email" placeholder="Enter your email..." />
            </div>
            <div className="field">
              <label htmlFor="cmsg">Message</label>
              <textarea id="cmsg" placeholder="Enter your message here..." />
            </div>
            <button type="submit" className="btn btn-accent" style={{ width: "100%" }}>SEND MESSAGE
            </button>
            <p className="form-note">Demo form — not wired to a mail service yet.
            </p>
          </form>
        </div>
      </section>

      <Footer />

      <Link to="/studio" className="floating-cta">OPEN STUDIO
      </Link>
    </>
  );
}
