import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const fmtInt = (v) =>
  v === null || v === undefined ? "" : Math.round(v).toLocaleString("en-US");
const fmtPct = (v) =>
  v === null || v === undefined ? "" : (v * 100).toFixed(1) + "%";
const fmtDec = (v) =>
  v === null || v === undefined ? "" : v.toLocaleString("en-US", { maximumFractionDigits: 2 });

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

  async function toggleMonth(mKey, current) {
    // Cycle: auto -> complete -> incomplete -> auto
    let next;
    if (current.override === null) next = current.complete ? false : true;
    else if (current.override === true) next = false;
    else next = null;
    await api.putMonthStatus({
      category: summary.category,
      month: mKey,
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
  const monthCols = months;

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
              Financial year
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
              <colgroup>
                <col /><col /><col /><col /><col /><col />
                {monthCols.map((m) => (
                  <col key={m.key} className="month-col" />
                ))}
                <col />
              </colgroup>
              <thead>
                <tr>
                  <th className="txt">Sub-cat</th>
                  <th className="txt">Category</th>
                  <th className="txt">Brand</th>
                  <th className="txt">Commercial</th>
                  <th>Mont Avg</th>
                  <th>Wk Avg</th>
                  {monthCols.map((m) => (
                    <th
                      key={m.key}
                      className={m.partial ? "partial" : ""}
                      title="Click to toggle completion"
                      style={{ cursor: "pointer" }}
                      onClick={() =>
                        toggleMonth(m.key, {
                          complete: m.complete,
                          override:
                            m.override === undefined ? null : m.override,
                        })
                      }
                    >
                      {m.header}
                    </th>
                  ))}
                  <th>YTD</th>
                </tr>
              </thead>
              <tbody>
                {summary.groups.map((g, gi) => (
                  <Group key={gi} g={g} months={monthCols} category={summary.category} />
                ))}
                <tr className="cattotal">
                  <td className="txt" colSpan={4}>TOTAL CATEGORY SPEND</td>
                  <td /><td />
                  {monthCols.map((m) => (
                    <td key={m.key}>{fmtInt(summary.category_total[m.key])}</td>
                  ))}
                  <td>{fmtInt(summary.category_total.ytd)}</td>
                </tr>
                {summary.sos.map((s, si) => (
                  <tr className="sos" key={si}>
                    <td className="txt" colSpan={3}>{s.mother_brand}</td>
                    <td className="txt">SOS %</td>
                    <td /><td />
                    {monthCols.map((m) => (
                      <td key={m.key}>{fmtPct(s[m.key])}</td>
                    ))}
                    <td>{fmtPct(s.ytd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}

function Group({ g, months }) {
  return (
    <>
      {g.brands.map((b, bi) => (
        <Brand key={bi} b={b} g={g} months={months} first={bi === 0} />
      ))}
      {g.show_total && (
        <>
          <tr className="mbtotal">
            <td /><td />
            <td className="txt">Total {g.mother_brand}</td>
            <td />
            <td>{fmtDec(g.total.mont_avg)}</td>
            <td>{fmtDec(g.total.weekly_avg)}</td>
            {months.map((m) => (
              <td key={m.key}>{fmtInt(g.total[m.key])}</td>
            ))}
            <td>{fmtInt(g.total.ytd)}</td>
          </tr>
          <tr className="acd">
            <td /><td />
            <td className="txt">Total {g.mother_brand} - ACD</td>
            <td /><td /><td />
            {months.map((m) => (
              <td key={m.key}>{fmtInt(g.total_acd[m.key])}</td>
            ))}
            <td>{fmtInt(g.total_acd.ytd)}</td>
          </tr>
        </>
      )}
    </>
  );
}

function Brand({ b, g, months, first }) {
  const rows = [];
  const themeRows = b.themes.length ? b.themes : [{ text: "—", ytd: 0 }];
  themeRows.forEach((th, i) => {
    rows.push(
      <tr className="theme" key={"t" + i}>
        <td className="txt">{first && i === 0 ? g.subcategory : ""}</td>
        <td className="txt">{i === 0 ? "" : ""}</td>
        <td className="brand txt">{i === 0 ? b.brand : ""}</td>
        <td className="txt">{th.text}</td>
        <td>{i === 0 ? fmtDec(b.mont_avg) : ""}</td>
        <td>{i === 0 ? fmtDec(b.weekly_avg) : ""}</td>
        {months.map((m) => (
          <td key={m.key}>{fmtInt(th[m.key])}</td>
        ))}
        <td>{fmtInt(th.ytd)}</td>
      </tr>
    );
  });
  const simpleRow = (cls, label, data, fmt = fmtInt) => (
    <tr className={cls}>
      <td /><td /><td />
      <td className="label">{label}</td>
      <td /><td />
      {months.map((m) => (
        <td key={m.key}>{fmt(data[m.key])}</td>
      ))}
      <td>{fmt(data.ytd)}</td>
    </tr>
  );
  return (
    <>
      {rows}
      {simpleRow("tag", "Tag", b.tag)}
      {simpleRow("va", "Value Adds", b.value_adds)}
      {simpleRow("total", "Total Spends (000)", b.total)}
      {simpleRow("acd", "ACD (Com Only)", b.acd_com)}
      {simpleRow("acd", "ACD (All Exp)", b.acd_all)}
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
        <div className="k-label">Mother brands</div>
        <div className="k-val">{brands}</div>
      </div>
      <div className="kpi">
        <div className="k-label">Months with data</div>
        <div className="k-val">{activeMonths}</div>
      </div>
      <div className="kpi">
        <div className="k-label">Top SOS</div>
        <div className="k-val" style={{ fontSize: 18 }}>
          {top ? `${top.mother_brand} · ${fmtPct(top.ytd)}` : "—"}
        </div>
      </div>
    </div>
  );
}
