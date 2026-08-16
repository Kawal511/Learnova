import { useId } from "react";

// Ready-made pairings, so a user can start from a good combination instead of
// hunting for two colours that work together.
export const PRESETS = [
  { name: "Brutalist Amber", primary: "#000000", secondary: "#ffbd00", background: "#ffffff" },
  { name: "Midnight Cyber", primary: "#1e293b", secondary: "#38bdf8", background: "#0f172a" },
  { name: "Emerald Academic", primary: "#047857", secondary: "#6ee7b7", background: "#064e3b" },
  { name: "Swiss Red", primary: "#18181b", secondary: "#ef4444", background: "#ffffff" },
  { name: "Sunset Editorial", primary: "#4c1d95", secondary: "#f59e0b", background: "#fff7ed" },
  { name: "Charcoal Gold", primary: "#292524", secondary: "#eab308", background: "#1c1917" },
  { name: "Ocean Tech", primary: "#0369a1", secondary: "#38bdf8", background: "#0c4a6e" },
  { name: "Terracotta", primary: "#7c2d12", secondary: "#ea580c", background: "#fff7ed" },
];

const HEX = /^#?[0-9a-fA-F]{6}$/;

function normalise(value) {
  const text = value.trim();
  if (!HEX.test(text)) return null;
  return text.startsWith("#") ? text.toLowerCase() : `#${text.toLowerCase()}`;
}

/** Pick black or white text for a given fill — same rule the backend uses. */
function readableOn(hex) {
  const clean = (hex || "#ffffff").replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(clean.slice(i, i + 2), 16) / 255);
  const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const luminance = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return luminance > 0.45 ? "#111111" : "#ffffff";
}

function Swatch({ label, value, onChange }) {
  const id = useId();
  return (
    <label className="swatch-field" htmlFor={id}>
      <span>{label}</span>
      <span className="swatch-input">
        <input
          id={id}
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <input
          type="text"
          value={value}
          spellCheck={false}
          onChange={(e) => {
            const next = normalise(e.target.value);
            onChange(next ?? e.target.value);
          }}
        />
      </span>
    </label>
  );
}

export default function PalettePicker({ palette, onChange, fonts, fontId, onFontChange }) {
  const bodyText = readableOn(palette.background);
  const headerText = readableOn(palette.primary);

  const set = (key) => (value) => onChange({ ...palette, [key]: value });

  const activePreset = PRESETS.find(
    (p) =>p.primary === palette.primary &&
      p.secondary === palette.secondary &&
      p.background === palette.background
  );

  return (
    <div>
      <div className="palette-row">
        <Swatch label="Primary" value={palette.primary} onChange={set("primary")} />
        <Swatch label="Secondary" value={palette.secondary} onChange={set("secondary")} />
        <Swatch label="Background" value={palette.background} onChange={set("background")} />

        <label className="swatch-field">
          <span>Font pairing</span>
          <select
            value={fontId}
            onChange={(e) => onFontChange(e.target.value)}
            style={{ minWidth: 230, padding: "10px" }}
          >
            {fonts.map((font) => (
              <option key={font.id} value={font.id}>
                {font.label}
              </option>
            ))}
          </select>
        </label>

        {/* Live preview of exactly what the deck header/body will look like */}
        <div className="palette-preview" style={{ background: palette.background }}>
          <div className="pp-head" style={{ background: palette.primary, color: headerText }}>Slide Title
          </div>
          <div className="pp-body" style={{ color: bodyText }}>Body copy renders in the body face.
            <br />
            <span className="pp-chip" style={{ background: palette.secondary, color: readableOn(palette.secondary) }}>Accent / Takeaway
            </span>
          </div>
        </div>
      </div>

      <div className="preset-grid">
        {PRESETS.map((preset) => (
          <button
            key={preset.name}
            type="button"
            className="preset"
            title={preset.name}
            aria-label={preset.name}
            aria-pressed={activePreset?.name === preset.name}
            onClick={() => onChange({ ...preset })}
          >
            <i style={{ background: preset.primary }} />
            <i style={{ background: preset.secondary }} />
            <i style={{ background: preset.background }} />
          </button>
        ))}
      </div>
      <p className="muted" style={{ marginTop: 10 }}>Text colours are chosen automatically by contrast, so a dark primary never
        ends up with dark text on it.
      </p>
    </div>
  );
}
