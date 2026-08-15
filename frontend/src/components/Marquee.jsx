// Infinite horizontal ticker. The item list is rendered twice so the
// -50% keyframe lands exactly on the seam and the loop is invisible.

export default function Marquee({ items, variant = "dark", reverse = false }) {
  const doubled = [...items, ...items];

  return (
    <div className={`marquee marquee-${variant}`} aria-hidden="true">
      <div className={`marquee-track${reverse ? " reverse" : ""}`}>
        {doubled.map((item, i) => (
          <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 34 }}>
            {item}
            <span className="marquee-sep">◆</span>
          </span>
        ))}
      </div>
    </div>
  );
}
