import { Link } from "react-router-dom";

const SOCIALS = ["GitHub", "LinkedIn", "YouTube", "Docs"];
const LINKS = [
  ["Studio", "/studio"],
  ["My Decks", "/decks"],
  ["Features", "/#features"],
  ["Contact", "/#contact"],
];

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-grid">
        <div className="footer-col">
          {SOCIALS.map((name) => (
            <a key={name} href="#contact">
              {name}
            </a>
          ))}
        </div>

        <div className="footer-brand">
          <div className="footer-logo">LEARN
            <br />OVA
          </div>
          <div className="footer-tag">AI Presentation Transformation Engine</div>
        </div>

        <div className="footer-col right">
          {LINKS.map(([label, href]) =>href.startsWith("/#") ? (
              <a key={label} href={href}>
                {label}
              </a>
            ) : (
              <Link key={label} to={href}>
                {label}
              </Link>
            )
          )}
        </div>
      </div>

      <div className="footer-rule" />

      <div className="footer-bottom">
        <span>© {new Date().getFullYear()} Learnova · AI Presentation Engine</span>
        <div className="footer-stats">
          <span>10 Design Themes</span>
          <span className="marquee-sep">◆</span>
          <span>16 Visual Types</span>
          <span className="marquee-sep">◆</span>
          <span>Zero-LLM Fallback</span>
        </div>
      </div>
    </footer>
  );
}
