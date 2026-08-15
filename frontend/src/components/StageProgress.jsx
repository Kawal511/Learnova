// Renders the pipeline's stage list as a progress rail.
// The backend's 9 named stages map onto this directly.

const ICONS = {
  ok: "",
  failed: "!",
  skipped: "–",
  running: "●",
  pending: "",
};

export default function StageProgress({ stages, current, currentStatus, progress }) {
  if (!stages?.length) return null;

  const currentIndex = stages.indexOf(current);

  return (
    <div className="stages">
      <div className="stages-bar">
        <div className="stages-fill" style={{ width: `${(progress ?? 0) * 100}%` }} />
      </div>
      <ol className="stages-list">
        {stages.map((name, i) => {
          let state = "pending";
          if (currentIndex > -1 && i < currentIndex) state = "ok";
          else if (name === current) state = currentStatus || "running";
          return (
            <li key={name} className={`stage stage-${state}`}>
              <span className="stage-dot">{ICONS[state] ?? ""}</span>
              <span className="stage-name">{name}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
