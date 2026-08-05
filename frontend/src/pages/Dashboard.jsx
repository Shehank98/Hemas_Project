import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const fmtInt = (v) =>
  v === null || v === undefined ? "" : Math.round(v).toLocaleString("en-US");
const fmtPct = (v) =>
  v === null || v === undefined ? "" : Math.round(v * 100) + "%";
// Blank when zero/empty (theme + VA rows); Total rows show "-" for zero.
const cell = (v, { blankZero = false, dash = false } = {}) => {
  if (v === null || v === undefined) return dash ? "-" : "";
  if (blankZero && v === 0) return "";
  if (dash && v === 0) return "-";
  return Math.round(v).toLocaleString("en-US");
};

export default function Dashboard({ categories, category, setCategory }) {
  const [summary, setSummary] = useState(null);
  const [fy, setFy] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(cat, fyYear) {
    if (!cat) {
      setSummary(null);
      return;
    }
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
    let next;
    const cur = m.override;
    if (cur === null || cur === undefined) next = m.complete ? false : true;
    else if (cur === true) next = false;
    else next = null;
    await api.putMonthStatus({
      category: summary.category,
      month: m.key,
      complete_override: next,
    });
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

  return (
    <>
      <div className="panel">
        <div className="row">
          <label className="field">
            Product group
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          {summary && (
            <label className="field">
              Year
              <select
                value={fy || ""}
                onChange={(e) => {
                  setFy(Number(e.target.value));
                  load(category, Number(e.target.value));
                }}
              >
                {summary.available_fy_years.map((y, i) => (
                  <option key={y} value={y}>
                    {summary.available_fys[i]}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="spacer" />
          <a href={api.exportUrl(category, fy)}>
            <button className="primary">⬇ Export this category</button>
          </a>
          <a href={api.exportAllUrl()}>
            <button>⬇ Export all (zip)</button>
          </a>
        </div>
      </div>

      {err && <div className="notice err">{err}</div>}
      {loading && <div className="panel">Loading…</div>}
      {summary && !loading && <Kpis summary={summary} />}

      {summary && !loading && (
        <div className="panel">
          <div className="row" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>
              {summary.category} — {summary.fy}
            </h2>
            <div className="spacer" />
            <span className="small muted">
              Click a month header to cycle complete / partial / auto.
            </span>
          </div>
          <div className="table-wrap">
            <table className="summary">
              <thead>
                <tr>
                  <th className="txt">CATEGORY</th>
                  <th className="txt">BRAND</th>
                  <th className="txt">COMMERCIAL</th>
                  {months.map((m) => (
                    <th
                      key={m.key}
                      className={m.partial ? "partial" : ""}
                      style={{ cursor: "pointer" }}
                      title="Click to toggle completion"
                      onClick={() => toggleMonth(m)}
                    >
                      {m.header}
                    </th>
                  ))}
                  <th>YTD</th>
                </tr>
              </thead>
              <tbody>
                {summary.groups.map((g, gi) => (
                  <Group
                    key={gi}
                    g={g}
                    months={months}
                    category={summary.category}
                    showCat={gi === 0}
                  />
                ))}
                <tr className="cattotal">
                  <td className="txt" colSpan={3}>TOTAL CATEGORY SPEND</td>
                  {months.map((m) => (
                    <td key={m.key}>{cell(summary.category_total[m.key], { dash: true })}</td>
                  ))}
                  <td>{cell(summary.category_total.ytd, { dash: true })}</td>
                </tr>
                {summary.sos.map((s, si) => (
                  <tr className="sos" key={si}>
                    <td className="txt" />
                    <td className="txt">{s.mother_brand}</td>
                    <td className="txt">{si === 0 ? "SOS %" : ""}</td>
                    {months.map((m) => (
                      <td key={m.key}>{fmtPct(s[m.key])}</td>
                    ))}
                    <td>{fmtPct(s.ytd)}</td>
                  </tr>
                ))}
                <tr className="sos">
                  <td className="txt" /><td className="txt" /><td className="txt" />
                  {months.map((m) => (
                    <td key={m.key}>
                      {summary.sos.some((s) => s[m.key]) ? "100%" : ""}
                    </td>
                  ))}
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

function Group({ g, months, category, showCat }) {
  return (
    <>
      {g.brands.map((b, bi) => (
        <Brand
          key={bi}
          b={b}
          months={months}
          category={showCat && bi === 0 ? category : ""}
        />
      ))}
      {g.show_total && (
        <>
          <tr className="mbtotal">
            <td /><td />
            <td className="txt">Total {g.mother_brand}</td>
            {months.map((m) => (
              <td key={m.key}>{cell(g.total[m.key], { dash: true })}</td>
            ))}
            <td>{cell(g.total.ytd, { dash: true })}</td>
          </tr>
          <tr className="acd">
            <td /><td />
            <td className="txt">Total {g.mother_brand} - ACD</td>
            {months.map((m) => (
              <td key={m.key}>{cell(g.total_acd[m.key])}</td>
            ))}
            <td />
          </tr>
        </>
      )}
    </>
  );
}

function Brand({ b, months, category }) {
  const themes = b.themes.filter((t) => (t.ytd || 0) !== 0);
  const rows = [];
  const themeRows = themes.length ? themes : [{ text: "", ytd: 0 }];
  themeRows.forEach((th, i) => {
    rows.push(
      <tr className="theme" key={"t" + i}>
        <td className="txt">{i === 0 ? category : ""}</td>
        <td className="brand txt">{i === 0 ? b.brand : ""}</td>
        <td className="txt">{th.text}</td>
        {months.map((m) => (
          <td key={m.key}>{cell(th[m.key], { blankZero: true })}</td>
        ))}
        <td>{cell(th.ytd, { blankZero: true })}</td>
      </tr>
    );
  });
  const simpleRow = (cls, label, data, opts = {}) => (
    <tr className={cls}>
      <td /><td />
      <td className="label">{label}</td>
      {months.map((m) => (
        <td key={m.key}>{cell(data[m.key], opts)}</td>
      ))}
      <td>{opts.noYtd ? "" : cell(data.ytd, opts)}</td>
    </tr>
  );
  const hasTag = (b.tag.ytd || 0) !== 0;
  const hasVa = (b.value_adds.ytd || 0) !== 0;
  return (
    <>
      {rows}
      {hasTag && simpleRow("tag", "Tag", b.tag, { blankZero: true })}
      {hasVa && simpleRow("va", "Value Adds", b.value_adds, { blankZero: true })}
      {simpleRow("total", "Total Spends (000)", b.total, { dash: true })}
      {simpleRow("acd", "ACD (Com Only)", b.acd_com, { noYtd: true })}
      {simpleRow("acd", "ACD (All Exp)", b.acd_all, { noYtd: true })}
    </>
  );
}

function Kpis({ summary }) {
  const total = summary.category_total.ytd || 0;
  const brands = summary.groups.length;
  const activeMonths = summary.months.filter((m) => m.has_data).length;
  const top = [...summary.sos].sort((a, b) => (b.ytd || 0) - (a.ytd || 0))[0];
  return (
    <div className="kpis">
      <div className="kpi">
        <div className="k-label">YTD spend (000 Rs)</div>
        <div className="k-val">{fmtInt(total)}</div>
      </div>
      <div className="kpi">
        <div className="k-label">Brands</div>
        <div className="k-val">{brands}</div>
      </div>
      <div className="kpi">
        <div className="k-label">Months with data</div>
        <div className="k-val">{activeMonths}</div>
      </div>
      <div className="kpi">
        <div className="k-label">Top SOS</div>
        <div className="k-val" style={{ fontSize: 18 }}>
          {top ? `${top.mother_brand} · ${fmtPct(top.ytd)}` : "-"}
        </div>
      </div>
    </div>
  );
}
