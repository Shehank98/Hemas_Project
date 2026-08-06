import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const fmtInt = (v) =>
  v === null || v === undefined ? "" : Math.round(v).toLocaleString("en-US");
const fmtPct = (v) =>
  v === null || v === undefined ? "" : Math.round(v * 100) + "%";
const fmtDec = (v) =>
  v === null || v === undefined ? "" : v.toLocaleString("en-US", { maximumFractionDigits: 2 });
const cell = (v, { blankZero = false, dash = false } = {}) => {
  if (v === null || v === undefined) return dash ? "-" : "";
  if (blankZero && v === 0) return "";
  if (dash && v === 0) return "-";
  return Math.round(v).toLocaleString("en-US");
};
const hex = (c) => (c ? "#" + c : undefined);
const LEAD = 7; // sub-cat, category, mother brand, brand, commercial, mont avg, weekly avg

export default function Dashboard({ categories, category, setCategory }) {
  const [summary, setSummary] = useState(null);
  const [fy, setFy] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(cat, fyYear) {
    if (!cat) return setSummary(null);
    setLoading(true);
    setErr("");
    try {
      const s = await api.summary(cat, fyYear);
      setSummary(s);
      setFy(s.fy_start_year);
    } catch (e) {
      setErr(e.message);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(category, null);
  }, [category]);

  async function toggleMonth(m) {
    const cur = m.override;
    let next;
    if (cur === null || cur === undefined) next = m.complete ? false : true;
    else if (cur === true) next = false;
    else next = null;
    await api.putMonthStatus({ category: summary.category, month: m.key, complete_override: next });
    load(category, fy);
  }

  if (!categories.length) {
    return (
      <div className="panel">
        <h2>No data yet</h2>
        <p className="sub">
          Head to <b>Upload data</b> and add a TV, Radio or Press export to get started.
        </p>
      </div>
    );
  }

  const months = summary?.months || [];
  const pal = summary?.palette || {};

  return (
    <>
      <div className="panel">
        <div className="row">
          <label className="field">
            Product group
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {categories.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          {summary && (
            <label className="field">
              Year
              <select
                value={fy || ""}
                onChange={(e) => { setFy(Number(e.target.value)); load(category, Number(e.target.value)); }}
              >
                {summary.available_fy_years.map((y, i) => (
                  <option key={y} value={y}>{summary.available_fys[i]}</option>
                ))}
              </select>
            </label>
          )}
          <div className="spacer" />
          <a href={api.exportUrl(category, fy)}>
            <button className="primary">⬇ Export this category</button>
          </a>
          <a href={api.exportAllUrl()}><button>⬇ Export all (zip)</button></a>
        </div>
      </div>

      {err && <div className="notice err">{err}</div>}
      {loading && <div className="panel">Loading…</div>}
      {summary && !loading && <Kpis summary={summary} pal={pal} />}

      {summary && !loading && (
        <div className="panel">
          <div className="row" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>
              <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: 3,
                background: hex(pal.head), marginRight: 8, verticalAlign: "middle" }} />
              {summary.category} · {summary.fy}
            </h2>
            <div className="spacer" />
            <span className="small muted">Click a month header to cycle complete / partial / auto.</span>
          </div>
          <div className="table-wrap">
            <table className="summary">
              <thead>
                <tr style={{ background: hex(pal.head), color: "#fff" }}>
                  <th className="txt" style={{ background: hex(pal.head), color: "#fff" }}>Sub-cat</th>
                  <th className="txt" style={{ background: hex(pal.head), color: "#fff" }}>Category</th>
                  <th className="txt" style={{ background: hex(pal.head), color: "#fff" }}>Mother Brand</th>
                  <th className="txt" style={{ background: hex(pal.head), color: "#fff" }}>Brand</th>
                  <th className="txt" style={{ background: hex(pal.head), color: "#fff" }}>Commercial</th>
                  <th style={{ background: hex(pal.head), color: "#fff" }}>Mont Avg</th>
                  <th style={{ background: hex(pal.head), color: "#fff" }}>Wk Avg</th>
                  {months.map((m) => (
                    <th key={m.key} className={m.partial ? "partial" : ""}
                        style={{ background: hex(pal.month), color: "#1f2430", cursor: "pointer" }}
                        title="Click to toggle completion" onClick={() => toggleMonth(m)}>
                      {m.header}
                    </th>
                  ))}
                  <th style={{ background: hex(pal.head), color: "#fff" }}>YTD</th>
                </tr>
              </thead>
              <tbody>
                {buildBodyRows(summary, months, pal)}
                <tr style={{ background: hex(pal.head), color: "#fff", fontWeight: 700 }}>
                  <td className="txt" colSpan={LEAD} style={{ color: "#fff" }}>TOTAL CATEGORY SPEND</td>
                  {months.map((m) => <td key={m.key} style={{ color: "#fff" }}>{cell(summary.category_total[m.key], { dash: true })}</td>)}
                  <td style={{ color: "#fff" }}>{cell(summary.category_total.ytd, { dash: true })}</td>
                </tr>
                {summary.sos.map((s, si) => (
                  <tr key={si} style={{ background: hex(pal.sos) }}>
                    <td className="txt" /><td className="txt" />
                    <td className="txt">{s.mother_brand}</td>
                    <td className="txt" />
                    <td className="txt">{si === 0 ? "SOS %" : ""}</td>
                    <td /><td />
                    {months.map((m) => <td key={m.key}>{fmtPct(s[m.key])}</td>)}
                    <td>{fmtPct(s.ytd)}</td>
                  </tr>
                ))}
                <tr style={{ background: hex(pal.sos) }}>
                  <td className="txt" colSpan={LEAD} />
                  {months.map((m) => <td key={m.key}>{summary.sos.some((s) => s[m.key]) ? "100%" : ""}</td>)}
                  <td>{summary.sos.length ? "100%" : ""}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

// Build the table body using rowSpan-merged cells (Category / Mother Brand /
// Brand span their blocks) so the hierarchy reads exactly like the Excel and the
// columns can never visually drift.
function buildBodyRows(summary, months, pal) {
  const brandRowCount = (b) => Math.max(b.themes.length, 1) + 4; // themes + VA + Total + 2×ACD
  const groupRowCount = (g) =>
    g.brands.reduce((s, b) => s + brandRowCount(b), 0) + (g.show_total ? 2 : 0);
  const catRows = summary.groups.reduce((s, g) => s + groupRowCount(g), 0);
  const dataCells = (data, opts) =>
    months.map((m) => <td key={m.key}>{cell(data[m.key], opts)}</td>);

  const out = [];
  let key = 0;
  let firstGlobal = true;

  summary.groups.forEach((g) => {
    const gRows = groupRowCount(g);
    let firstOfGroup = true;

    g.brands.forEach((b) => {
      const themeRows = b.themes.length ? b.themes : [{ text: "" }];
      const bRows = brandRowCount(b);

      themeRows.forEach((th, ti) => {
        const tds = [];
        if (firstOfGroup && ti === 0) {
          tds.push(<td key="sub" className="txt" rowSpan={gRows}>{g.subcategory || ""}</td>);
          if (firstGlobal)
            tds.push(<td key="cat" className="txt" rowSpan={catRows}>{summary.category}</td>);
          tds.push(<td key="mb" className="brand txt" rowSpan={gRows}>{g.mother_brand}</td>);
        }
        if (ti === 0)
          tds.push(<td key="br" className="brand txt" rowSpan={bRows}>{b.brand}</td>);
        tds.push(<td key="com" className="txt">{th.text}</td>);
        if (ti === 0) {
          tds.push(<td key="mo" rowSpan={bRows}>{fmtDec(b.mont_avg)}</td>);
          tds.push(<td key="wk" rowSpan={bRows}>{fmtDec(b.weekly_avg)}</td>);
        }
        out.push(
          <tr className="theme" key={key++}>
            {tds}
            {dataCells(th, { blankZero: true })}
            <td>{cell(th.ytd, { blankZero: true })}</td>
          </tr>
        );
        firstOfGroup = false;
      });

      out.push(
        <tr key={key++}>
          <td className="label">Value Adds</td>
          {dataCells(b.value_adds, { blankZero: true })}
          <td>{cell(b.value_adds.ytd, { blankZero: true })}</td>
        </tr>
      );
      out.push(
        <tr key={key++} style={{ background: hex(pal.total), fontWeight: 700 }}>
          <td className="label">Total Spends (000)</td>
          {dataCells(b.total, { dash: true })}
          <td>{cell(b.total.ytd, { dash: true })}</td>
        </tr>
      );
      out.push(
        <tr key={key++} style={{ background: hex(pal.acd), fontWeight: 600 }}>
          <td className="label">ACD (Com Only)</td>
          {dataCells(b.acd_com)}<td />
        </tr>
      );
      out.push(
        <tr key={key++} style={{ background: hex(pal.acd), fontWeight: 600 }}>
          <td className="label">ACD (All Exp)</td>
          {dataCells(b.acd_all)}<td />
        </tr>
      );
    });

    if (g.show_total) {
      out.push(
        <tr key={key++} style={{ background: hex(pal.mbtotal), fontWeight: 700 }}>
          <td className="txt">Total {g.mother_brand}</td>
          <td className="txt" />
          <td>{fmtDec(g.total.mont_avg)}</td>
          <td>{fmtDec(g.total.weekly_avg)}</td>
          {months.map((m) => <td key={m.key}>{cell(g.total[m.key], { dash: true })}</td>)}
          <td>{cell(g.total.ytd, { dash: true })}</td>
        </tr>
      );
      out.push(
        <tr key={key++} style={{ background: hex(pal.acd) }}>
          <td className="txt">Total {g.mother_brand} - ACD</td>
          <td className="txt" /><td /><td />
          {months.map((m) => <td key={m.key}>{cell(g.total_acd[m.key])}</td>)}
          <td />
        </tr>
      );
    }
    firstGlobal = false;
  });

  return out;
}

function Kpis({ summary, pal }) {
  const total = summary.category_total.ytd || 0;
  const brands = summary.groups.length;
  const activeMonths = summary.months.filter((m) => m.has_data).length;
  const top = [...summary.sos].sort((a, b) => (b.ytd || 0) - (a.ytd || 0))[0];
  const border = { borderTop: `3px solid ${hex(pal.head)}` };
  return (
    <div className="kpis">
      <div className="kpi" style={border}><div className="k-label">YTD spend (000 Rs)</div><div className="k-val">{fmtInt(total)}</div></div>
      <div className="kpi" style={border}><div className="k-label">Brands</div><div className="k-val">{brands}</div></div>
      <div className="kpi" style={border}><div className="k-label">Months with data</div><div className="k-val">{activeMonths}</div></div>
      <div className="kpi" style={border}><div className="k-label">Top SOS</div>
        <div className="k-val" style={{ fontSize: 18 }}>{top ? `${top.mother_brand} · ${fmtPct(top.ytd)}` : "-"}</div>
      </div>
    </div>
  );
}
