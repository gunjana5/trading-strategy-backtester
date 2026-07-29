// tiny ? you click for a casual one-liner

import { useEffect, useId, useRef, useState } from "react";
import "./InfoTip.css";

export default function InfoTip({ text, align = "left" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const tipId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const onPointer = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!text) return null;

  return (
    <span className={`info-tip align-${align}`} ref={ref}>
      <button
        type="button"
        className="info-tip-btn"
        aria-label="what is this"
        aria-expanded={open}
        aria-controls={tipId}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
      >
        ?
      </button>
      {open && (
        <span className="info-tip-pop" id={tipId} role="tooltip">
          {text}
        </span>
      )}
    </span>
  );
}
