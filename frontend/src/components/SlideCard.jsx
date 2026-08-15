// Renders one generated slide according to its layout_type.
// Mirrors the layouts the PPTX/HTML builders emit.

const BADGE_COLORS = {
  FLOWCHART: "#28a745",
  TABLE: "#17a2b8",
  METRIC: "#fd7e14",
  CARD_GRID: "#e83e8c",
  QUIZ: "#6f42c1",
  MINIMAL_TEXT: "#1e2761",
};

function Body({ slide }) {
  switch (slide.layout_type) {
    case "FLOWCHART":
      return (
        <div className="flow">
          {(slide.bullets ?? []).map((step, i) => (
            <span key={i} className="flow-pill">
              {step}
            </span>
          ))}
        </div>
      );

    case "TABLE":
      if (!slide.table_headers?.length) break;
      return (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {slide.table_headers.map((h, i) => (
                  <th key={i}>{String(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(slide.table_rows ?? []).map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td key={c}>{String(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case "METRIC":
      return (
        <div className="metric">
          <div className="metric-value">{slide.metric_value ?? "—"}</div>
          <div className="metric-label">{slide.metric_label ?? slide.title}</div>
          <p className="metric-desc">{slide.metric_desc ?? slide.takeaway}</p>
        </div>
      );

    case "CARD_GRID":
      return (
        <div className="card-grid">
          {(slide.bullets ?? []).slice(0, 4).map((bullet, i) => (
            <div key={i} className="pillar">
              <h5>Pillar {i + 1}</h5>
              <p>{bullet}</p>
            </div>
          ))}
        </div>
      );

    case "QUIZ":
      return (
        <div className="quiz">
          <p className="quiz-q">{slide.question}</p>
          <ul>
            {(slide.options ?? []).map((opt, i) => (
              <li key={i}>{opt}</li>
            ))}
          </ul>
          <p className="quiz-a">Correct: {slide.correct}</p>
        </div>
      );

    default:
      break;
  }

  return (
    <ul className="bullets">
      {(slide.bullets ?? []).map((bullet, i) => (
        <li key={i}>{bullet}</li>
      ))}
    </ul>
  );
}

export default function SlideCard({ slide }) {
  const color = BADGE_COLORS[slide.layout_type] ?? "#1e2761";
  return (
    <article className="slide">
      <header>
        <h3>{slide.title}</h3>
        <span className="badge" style={{ background: color }}>
          {slide.layout_type}
        </span>
      </header>
      <Body slide={slide} />
      {slide.takeaway ? <p className="takeaway"> {slide.takeaway}</p> : null}
    </article>
  );
}
