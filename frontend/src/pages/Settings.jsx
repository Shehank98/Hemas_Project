import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export default function Settings({ categories, defaultCategory }) {
  const [settings, setSettings] = useState(null);
  const [allBrands, setAllBrands] = useState([]);
  const [newKw, setNewKw] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [cat, setCat] = useState(defaultCategory || "");

  async function loadGlobal() {
    setSettings(await api.getSettings());
    const { brands } = await api.brands();
    setAllBrands(brands);
  }

  useEffect(() => {
    loadGlobal();
  }, []);
  useEffect(() => {
    if (!cat && categories.length) setCat(categories[0]);
  }, [categories]);

  async function saveGlobal(next) {
    setErr("");
    try {
      const saved = await api.putSettings(next);
      setSettings(saved);
      setMsg("Settings saved.");
      setTimeout(() => setMsg(""), 1500);
    } catch (e) {
      setErr(e.message);
    }
  }

  if (!settings) return <div className="panel">Loading…</div>;

  const va = settings.va_keywords || [];
  const subcat = settings.brand_subcategory || {};

  return (
    <>
      {msg && <div className="notice ok">{msg}</div>}
      {err && <div className="notice err">{err}</div>}

      <div className="panel">
        <h2>Value-Add (VA) themes</h2>
        <p className="sub">
          Any theme whose (edited) text contains one of these words counts as a
          value-add. VA spend is excluded from <b>ACD (Com Only)</b> and rolled into
          the <b>Tag</b> / <b>Value Adds</b> rows.
        </p>
        <div style={{ marginBottom: 10 }}>
          {va.map((k) => (
            <span className="chip" key={k}>
              {k}
              <button
                onClick={() => saveGlobal({ va_keywords: va.filter((x) => x !== k) })}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div className="row">
          <input
            type="text"
            placeholder="Add keyword (e.g. Scroll)"
            value={newKw}
            onChange={(e) => setNewKw(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && newKw.trim()) {
                saveGlobal({ va_keywords: [...new Set([...va, newKw.trim()])] });
                setNewKw("");
              }
            }}
          />
          <button
            onClick={() => {
              if (newKw.trim()) {
                saveGlobal({ va_keywords: [...new Set([...va, newKw.trim()])] });
                setNewKw("");
              }
            }}
          >
            Add
          </button>
        </div>
        <div className="row" style={{ marginTop: 16 }}>
          <label className="field">
            "Tag" keyword (its own row; other VA → "Value Adds")
            <input
              type="text"
              value={settings.tag_keyword || ""}
              onChange={(e) => setSettings({ ...settings, tag_keyword: e.target.value })}
              onBlur={(e) => saveGlobal({ tag_keyword: e.target.value })}
            />
          </label>
          <label className="field">
            Summary year starts (January = calendar year, Jan–Dec)
            <select
              value={settings.fy_start_month || 4}
              onChange={(e) =>
                saveGlobal({ fy_start_month: Number(e.target.value) })
              }
            >
              {MONTHS.map((m, i) => (
                <option key={i} value={i + 1}>{m}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="panel">
        <h2>Brand → Sub-category</h2>
        <p className="sub">
          Group brands into sub-categories (column A in the export). Leave blank to
          skip. Brands appear here once their data has been uploaded.
        </p>
        {allBrands.length === 0 && (
          <p className="muted small">No brands yet — upload data first.</p>
        )}
        <table className="grid">
          <thead>
            <tr>
              <th>Brand</th>
              <th>Sub-category</th>
            </tr>
          </thead>
          <tbody>
            {allBrands.map((b) => (
              <tr key={b}>
                <td>{b}</td>
                <td>
                  <input
                    type="text"
                    value={subcat[b] || ""}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        brand_subcategory: { ...subcat, [b]: e.target.value },
                      })
                    }
                    onBlur={() => saveGlobal({ brand_subcategory: subcat })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {categories.length > 0 && (
        <div className="panel">
          <div className="row" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Per-category settings</h2>
            <label className="field">
              Category
              <select value={cat} onChange={(e) => setCat(e.target.value)}>
                {categories.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>
          {cat && <ThemeEdits key={"t" + cat} category={cat} />}
          {cat && <BrandRefs key={"r" + cat} category={cat} />}
        </div>
      )}
    </>
  );
}

function ThemeEdits({ category }) {
  const [themes, setThemes] = useState([]);
  const [dirty, setDirty] = useState({});
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.themes(category).then((r) => setThemes(r.themes));
  }, [category]);

  async function save() {
    const edits = Object.entries(dirty).map(([theme_raw, edit_text]) => ({
      theme_raw,
      edit_text,
    }));
    await api.putThemeEdits({ category, edits });
    setDirty({});
    setMsg("Theme edits saved.");
    setTimeout(() => setMsg(""), 1500);
  }

  return (
    <div style={{ marginTop: 20 }}>
      <h3 style={{ margin: "0 0 4px" }}>Theme editing</h3>
      <p className="muted small">
        Rename a theme's display text. Themes sharing the same edited text within a
        brand merge into one row.
      </p>
      {msg && <div className="notice ok">{msg}</div>}
      <div className="table-wrap" style={{ maxHeight: 360, overflowY: "auto" }}>
        <table className="grid">
          <thead>
            <tr>
              <th>Brand</th>
              <th>Raw theme</th>
              <th>Display text</th>
            </tr>
          </thead>
          <tbody>
            {themes.map((t) => (
              <tr key={t.theme_raw}>
                <td className="small">{t.brand}</td>
                <td className="small muted">{t.theme_raw}</td>
                <td>
                  <input
                    type="text"
                    style={{ width: "100%", minWidth: 260 }}
                    defaultValue={t.edit_text}
                    onChange={(e) =>
                      setDirty({ ...dirty, [t.theme_raw]: e.target.value })
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        <button
          className="primary"
          disabled={!Object.keys(dirty).length}
          onClick={save}
        >
          Save theme edits
        </button>
      </div>
    </div>
  );
}

function BrandRefs({ category }) {
  const [brands, setBrands] = useState([]);
  const [refs, setRefs] = useState({});
  const [msg, setMsg] = useState("");

  useEffect(() => {
    (async () => {
      const { brands } = await api.brands(category);
      setBrands(brands);
      const { refs } = await api.brandRefs(category);
      const map = {};
      refs.forEach((r) => (map[r.brand] = r));
      setRefs(map);
    })();
  }, [category]);

  async function save() {
    const payload = brands.map((b) => ({
      brand: b,
      mont_avg: refs[b]?.mont_avg ?? null,
      weekly_avg: refs[b]?.weekly_avg ?? null,
    }));
    await api.putBrandRefs({ category, refs: payload });
    setMsg("Reference values saved.");
    setTimeout(() => setMsg(""), 1500);
  }

  const upd = (b, k, v) =>
    setRefs({ ...refs, [b]: { ...refs[b], [k]: v === "" ? null : Number(v) } });

  return (
    <div style={{ marginTop: 24 }}>
      <h3 style={{ margin: "0 0 4px" }}>Reference columns (Mont Avg / Weekly Avg)</h3>
      <p className="muted small">
        Manually maintained per-brand reference spend shown in columns E/F.
      </p>
      {msg && <div className="notice ok">{msg}</div>}
      <table className="grid">
        <thead>
          <tr>
            <th>Brand</th>
            <th>Mont Avg Spend</th>
            <th>Weekly Avg Spend</th>
          </tr>
        </thead>
        <tbody>
          {brands.map((b) => (
            <tr key={b}>
              <td>{b}</td>
              <td>
                <input
                  type="number"
                  value={refs[b]?.mont_avg ?? ""}
                  onChange={(e) => upd(b, "mont_avg", e.target.value)}
                />
              </td>
              <td>
                <input
                  type="number"
                  value={refs[b]?.weekly_avg ?? ""}
                  onChange={(e) => upd(b, "weekly_avg", e.target.value)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="row" style={{ marginTop: 10 }}>
        <button className="primary" onClick={save}>Save reference values</button>
      </div>
    </div>
  );
}
