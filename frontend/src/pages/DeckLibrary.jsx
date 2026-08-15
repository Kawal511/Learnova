import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api";
import Footer from "../components/Footer.jsx";
import Navbar from "../components/Navbar.jsx";

function formatDate(seconds) {
  if (!seconds) return "";
  return new Date(seconds * 1000).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function DeckLibrary() {
  const [decks, setDecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listMyDecks();
      setDecks(data.decks || []);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function download(deck, artifact) {
    try {
      await api.downloadArtifact(
        api.deckDownloadPath(deck.id, artifact),
        `Learnova_${deck.title || "deck"}.${artifact}`
      );
    } catch (e) {
      setError(e.message);
    }
  }

  async function showMarkdown(deck) {
    try {
      const data = await api.getDeckMarkdown(deck.id);
      setPreview({ title: deck.title, markdown: data.markdown });
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove(deck) {
    try {
      await api.deleteDeck(deck.id);
      setPreview(null);
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <Navbar variant="solid" />

      <main className="shell">
        <div className="kicker">// LIBRARY</div>
        <h1 className="display" style={{ fontSize: "clamp(2.2rem,5vw,3.6rem)", marginBottom: 26 }}>MY <span className="outline-word">DECKS</span>
        </h1>

        {error ? <div className="error">{error}</div> : null}

        {loading ? (
          <p className="muted">Loading your decks…</p>
        ) : decks.length === 0 ? (
          <div className="empty">
            <p style={{ marginTop: 0 }}>You haven't generated any decks yet.</p>
            <Link to="/studio" className="btn btn-lime btn-sm">OPEN STUDIO
            </Link>
          </div>
        ) : (
          <div className="deck-grid">
            {decks.map((deck) => (
              <article className="deck-card" key={deck.id}>
                <h3>{deck.title}</h3>
                <div className="deck-meta">
                  <span>{deck.slide_count} slides</span>
                  <span>{deck.quiz_count} quizzes</span>
                  <span>{deck.overall_score}/100</span>
                </div>
                <div className="deck-meta">
                  <span>{formatDate(deck.created_at)}</span>
                </div>
                {deck.theme_spec ? (
                  <div style={{ display: "flex", gap: 6 }}>
                    {["primary", "secondary", "background"].map((key) =>deck.theme_spec[key] ? (
                        <span
                          key={key}
                          title={`${key}: ${deck.theme_spec[key]}`}
                          style={{
                            width: 22,
                            height: 22,
                            background: deck.theme_spec[key],
                            border: "2px solid #000",
                            display: "inline-block",
                          }}
                        />
                      ) : null
                    )}
                  </div>
                ) : null}

                <div className="deck-actions">
                  {deck.has_pptx ? (
                    <button
                      className="btn btn-sm btn-lime"
                      type="button"
                      onClick={() => download(deck, "pptx")}
                    >PPTX
                    </button>
                  ) : null}
                  {deck.has_html ? (
                    <button
                      className="btn btn-sm"
                      type="button"
                      onClick={() => download(deck, "html")}
                    >HTML
                    </button>
                  ) : null}
                  <button
                    className="btn btn-sm"
                    type="button"
                    onClick={() => showMarkdown(deck)}
                  >Markdown
                  </button>
                  <button className="btn btn-sm" type="button" onClick={() => remove(deck)}>Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}

        {preview ? (
          <section className="panel" style={{ marginTop: 30 }}>
            <h2>{preview.title} — markdown</h2>
            <textarea className="md-editor" readOnly value={preview.markdown} />
            <button
              className="btn btn-sm"
              type="button"
              onClick={() => setPreview(null)}
              style={{ marginTop: 12 }}
            >Close
            </button>
          </section>
        ) : null}
      </main>

      <Footer />
    </>
  );
}
