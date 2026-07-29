// scrolling paper tape across the top of the desk

import "./TickerTape.css";

const ITEMS = [
  "PAPER ONLY",
  "NOT LIVE MONEY",
  "COSTS FIRST",
  "WALK-FORWARD ON ML",
  "COMPARE UNDER SAME FEES",
  "YAHOO HISTORY",
  "LONG ONLY",
  "DESK NOTES WELCOME",
];

export default function TickerTape() {
  const line = [...ITEMS, ...ITEMS].map((t, i) => (
    <span key={`${t}-${i}`} className="tape-item">
      <span className="tape-dot" aria-hidden />
      {t}
    </span>
  ));

  return (
    <div className="ticker-tape" aria-hidden>
      <div className="tape-track">{line}</div>
    </div>
  );
}
