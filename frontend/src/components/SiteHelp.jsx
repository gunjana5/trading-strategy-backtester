// corner site info + first-visit welcome

import { useEffect, useState } from "react";
import InfoTip from "./InfoTip.jsx";
import "./SiteHelp.css";

const WELCOME_KEY = "tsb-welcome-seen-v1";

const SITE_BLURB =
  "paper trading desk in the browser. pick a ticker dates and a strategy then hit run. nothing here is live money. see the little ? next to stuff if a word looks weird";

export default function SiteHelp() {
  const [welcome, setWelcome] = useState(false);
  const [panel, setPanel] = useState(false);

  useEffect(() => {
    try {
      // only show the welcome once per browser
      if (!localStorage.getItem(WELCOME_KEY)) setWelcome(true);
    } catch {
      setWelcome(true);
    }
  }, []);

  const dismissWelcome = () => {
    setWelcome(false);
    try {
      localStorage.setItem(WELCOME_KEY, "1");
    } catch {
      /* ignore */
    }
  };

  return (
    <>
      {welcome && (
        <div className="welcome-banner" role="dialog" aria-label="welcome">
          <div className="welcome-card">
            <p className="welcome-title">hey</p>
            <p className="welcome-body">
              this is a paper backtester not real trading. use the left panel to set stuff up then
              press run. anywhere you see a small ? click it for a plain english note. the ? in the
              bottom right is the general site info
            </p>
            <button type="button" className="welcome-ok" onClick={dismissWelcome}>
              got it
            </button>
          </div>
        </div>
      )}

      <div className="site-help-corner">
        <button
          type="button"
          className="site-help-fab"
          aria-label="site info"
          aria-expanded={panel}
          onClick={() => setPanel((v) => !v)}
        >
          ?
        </button>
        {panel && (
          <div className="site-help-panel" role="dialog">
            <div className="site-help-panel-head">
              <span>site info</span>
              <button type="button" className="site-help-close" onClick={() => setPanel(false)}>
                close
              </button>
            </div>
            <p>{SITE_BLURB}</p>
            <ul>
              <li>left side = controls</li>
              <li>run history = past runs you can reopen</li>
              <li>right side = charts metrics and trade list after a run</li>
              <li>click any small ? for what that bit means</li>
            </ul>
            <p className="site-help-foot">
              still stuck
              <InfoTip text="yeah same energy just poke the ? icons they are everywhere on purpose" />
            </p>
          </div>
        )}
      </div>
    </>
  );
}
