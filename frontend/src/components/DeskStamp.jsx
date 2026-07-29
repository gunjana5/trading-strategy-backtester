// small live desk clock + paper date stamp

import { useEffect, useState } from "react";
import "./DeskStamp.css";

function pad(n) {
  return String(n).padStart(2, "0");
}

export default function DeskStamp() {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const stamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const clock = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  return (
    <div className="desk-stamp" aria-hidden>
      <span className="desk-stamp-label">desk open</span>
      <span className="desk-stamp-date">{stamp}</span>
      <span className="desk-stamp-clock">{clock}</span>
    </div>
  );
}
