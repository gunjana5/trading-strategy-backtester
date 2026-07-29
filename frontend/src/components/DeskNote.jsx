// short judgment line saved onto the run

import { useEffect, useState } from "react";
import { saveRunNote } from "../api/client.js";
import InfoTip from "./InfoTip.jsx";
import "./DeskNote.css";

export default function DeskNote({ runId, initialNote = "" }) {
  const [note, setNote] = useState(initialNote || "");
  const [status, setStatus] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setNote(initialNote || "");
    setStatus(null);
  }, [runId, initialNote]);

  if (runId == null) return null;

  const onSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      await saveRunNote(runId, note);
      setStatus("saved");
    } catch (e) {
      setStatus(e?.message || "save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="desk-note">
      <div className="desk-note-head">
        <span className="label-row">
          desk note
          <InfoTip text="2-3 lines on what you think happened costs killed the edge folds disagreed etc" />
        </span>
      </div>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value.slice(0, 500))}
        rows={3}
        placeholder="eg costs ate the edge / walk-forward folds disagree / fine with size at 50%"
      />
      <div className="desk-note-actions">
        <button type="button" onClick={onSave} disabled={saving}>
          {saving ? "saving…" : "save note"}
        </button>
        <span className="desk-note-meta">{note.length}/500</span>
        {status && <span className="desk-note-status">{status}</span>}
      </div>
    </div>
  );
}
