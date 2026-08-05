// Thin API client. Same-origin in production (FastAPI serves the build); Vite
// proxies /api to :8000 in dev.
const BASE = "";

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

export const api = {
  categories: () => req("/api/categories"),
  summary: (category, fy) =>
    req(`/api/summary?category=${encodeURIComponent(category)}` + (fy ? `&fy=${fy}` : "")),
  previewUpload: (fd) => req("/api/upload/preview", { method: "POST", body: fd }),
  commitUpload: (fd) => req("/api/upload/commit", { method: "POST", body: fd }),
  getSettings: () => req("/api/settings"),
  putSettings: (payload) =>
    req("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  brands: (category) =>
    req(`/api/brands` + (category ? `?category=${encodeURIComponent(category)}` : "")),
  themes: (category) => req(`/api/themes?category=${encodeURIComponent(category)}`),
  putThemeEdits: (payload) =>
    req("/api/theme-edits", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  monthStatus: (category) =>
    req(`/api/month-status?category=${encodeURIComponent(category)}`),
  putMonthStatus: (payload) =>
    req("/api/month-status", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  brandRefs: (category) =>
    req(`/api/brand-refs?category=${encodeURIComponent(category)}`),
  putBrandRefs: (payload) =>
    req("/api/brand-refs", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  exportUrl: (category, fy) =>
    `/api/export?category=${encodeURIComponent(category)}` + (fy ? `&fy=${fy}` : ""),
  exportAllUrl: () => "/api/export_all",
};
