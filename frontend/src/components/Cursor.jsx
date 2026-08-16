import { useEffect, useRef, useState } from "react";

// Custom pointer: a dark blue dot that follows the mouse and swells to a light
// cyan ring over anything clickable.
//
// Position is written straight to the DOM node rather than held in state — a
// setState per mousemove would re-render the tree on every pixel of travel.
// Only the boolean "is over something clickable" goes through React, because
// that changes a handful of times per session, not a thousand times a second.
//
// The write happens in the handler rather than on a requestAnimationFrame
// loop: there is no interpolation to smooth, so a rAF hop would only add a
// frame of lag between the real pointer and the dot. mousemove already fires
// at most once per frame.

const INTERACTIVE = 'a, button, input, textarea, select, label, summary, [role="button"], [role="tab"], .btn, .tab, .density-option, .palette-swatch, .feature-cell, .file-btn';

// Third-party UI that renders in its own portal above the page. The dot cannot
// reliably paint over it, so it stands down and lets the native cursor take
// over there (see the matching rule in styles.css).
const THIRD_PARTY = '[class*="cl-"]';

export default function Cursor() {
  const dotRef = useRef(null);
  const [active, setActive] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // A touch device has no hovering pointer to replace, and a device that
    // respects reduced motion should not get a lagging follower.
    const fine = window.matchMedia("(pointer: fine)").matches;
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || calm) return;

    document.body.classList.add("has-custom-cursor");

    const onMove = (e) => {
      const node = dotRef.current;
      if (node) {
        node.style.transform =
          `translate3d(${e.clientX}px, ${e.clientY}px, 0) translate(-50%, -50%)`;
      }
      const inThirdParty = Boolean(e.target.closest?.(THIRD_PARTY));
      setVisible(!inThirdParty);
      setActive(!inThirdParty && Boolean(e.target.closest?.(INTERACTIVE)));
    };
    const onLeave = () => setVisible(false);
    const onEnter = () => setVisible(true);

    window.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseleave", onLeave);
    document.addEventListener("mouseenter", onEnter);

    return () => {
      window.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeave);
      document.removeEventListener("mouseenter", onEnter);
      document.body.classList.remove("has-custom-cursor");
    };
  }, []);

  return (
    <div
      ref={dotRef}
      aria-hidden="true"
      className={`cursor-dot${active ? " is-active" : ""}${visible ? "" : " is-hidden"}`}
    />
  );
}
