import React, { useRef, useState } from "react";
import { api } from "../api.js";

const todayISO = () => new Date().toISOString().slice(0, 10);

export default function Upload({ onCommitted }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [asOf, setAsOf] = useState(todayISO());
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef();

  async function choose(f) {
    setErr("");
    setMsg("");
    setPreview(null);
    setFile(f);
    if (!f) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const p = await api.previewUpload(fd);
      setPreview(p);
      // Default the as-of date to the last day of the latest month in the file.
      if (p.months && p.months.length) {
        const last = p.months[p.months.length - 1];
        const [y, m] = last.split("-").map(Number);
        const end = new Date(y, m, 0).getDate();
        setAsOf(`${last}-${String(end).padStart(2, "0")}`);
      }
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("as_of_date", asOf);
      const r = await api.commitUpload(fd);
      setMsg(
        `Stored ${r.rows_stored} aggregated rows for ${r.categories.join(", ")} (${r.media_type.toUpperCase()}).`
      );
      setPreview(null);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      setTimeout(() => onCommitted(r.categories[0]), 800);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  const mediaLabel = { tv: "TV", radio: "Radio", press: "Press" };

  return (
    <>
      <div className="panel">
        <h2>Upload data</h2>
        <p className="sub">
          Drop a TV, Radio or Press export (.xlsx). The media type is detected from the
          columns. Re-uploading the same media type for a month <b>replaces</b> that
          month's numbers (other media types stay).
        </p>
        <div
          className={"dropzone" + (drag ? " drag" : "")}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            choose(e.dataTransfer.files[0]);
          }}
        >
          {file ? (
            <div>
              <b>{file.name}</b>
              <div className="small muted">Click to choose a different file</div>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: 28 }}>⬆</div>
              Click or drop an .xlsx file here
            </div>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls"
            style={{ display: "none" }}
            onChange={(e) => choose(e.target.files[0])}
          />
        </div>
      </div>

      {err && <div className="notice err">{err}</div>}
      {msg && <div className="notice ok">{msg}</div>}
      {busy && <div className="panel">Working…</div>}

      {preview && (
        <div className="panel">
          <h2>Preview</h2>
          <div className="kpis">
            <div className="kpi">
              <div className="k-label">Detected media</div>
              <div className="k-val">{mediaLabel[preview.media_type]}</div>
            </div>
            <div className="kpi">
              <div className="k-label">Rows read</div>
              <div className="k-val">{preview.row_count}</div>
            </div>
            <div className="kpi">
              <div className="k-label">Aggregated rows stored</div>
              <div className="k-val">{preview.aggregated_rows}</div>
            </div>
            <div className="kpi">
              <div className="k-label">Total spend (000)</div>
              <div className="k-val">
                {Math.round(preview.total_spend).toLocaleString()}
              </div>
            </div>
          </div>

          <div className="row">
            <div>
              <div className="small muted">Product groups</div>
              {preview.categories.map((c) => (
                <span className="chip" key={c}>{c}</span>
              ))}
            </div>
            <div>
              <div className="small muted">Months</div>
              {preview.months.map((m) => (
                <span className="chip" key={m}>{m}</span>
              ))}
            </div>
          </div>

          {preview.warnings?.length > 0 &&
            preview.warnings.map((w, i) => (
              <div className="notice warn" key={i}>{w}</div>
            ))}

          {preview.replacements?.length > 0 && (
            <div className="notice warn">
              This will replace existing {mediaLabel[preview.media_type]} data for:{" "}
              {preview.replacements
                .map((r) => `${r.category} ${r.month} (${r.existing_rows} rows)`)
                .join(", ")}
              .
            </div>
          )}

          <div className="row" style={{ marginTop: 12 }}>
            <label className="field">
              Data is complete up to (as-of date)
              <input
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
              />
            </label>
            <div className="spacer" />
            <button className="primary" disabled={busy} onClick={commit}>
              Confirm &amp; store
            </button>
          </div>
          <p className="small muted">
            The as-of date sets whether the latest month shows as partial
            (e.g. "1st to 14th July") or complete.
          </p>
        </div>
      )}
    </>
  );
}
