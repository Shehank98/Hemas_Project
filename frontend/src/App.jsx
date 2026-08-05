import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import Dashboard from "./pages/Dashboard.jsx";
import Upload from "./pages/Upload.jsx";
import Settings from "./pages/Settings.jsx";

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [categories, setCategories] = useState([]);
  const [category, setCategory] = useState("");

  async function loadCategories(select) {
    const { categories } = await api.categories();
    setCategories(categories);
    if (categories.length && (!category || select)) {
      setCategory(select && categories.includes(select) ? select : categories[0]);
    }
  }

  useEffect(() => {
    loadCategories();
  }, []);

  const tabs = [
    ["dashboard", "Dashboard"],
    ["upload", "Upload data"],
    ["settings", "Settings"],
  ];

  return (
    <>
      <div className="topbar">
        <div className="brand">
          <span className="dot" /> Media Tracking
        </div>
        <div className="tabs">
          {tabs.map(([id, label]) => (
            <div
              key={id}
              className={"tab" + (tab === id ? " active" : "")}
              onClick={() => setTab(id)}
            >
              {label}
            </div>
          ))}
        </div>
      </div>
      <div className="container">
        {tab === "dashboard" && (
          <Dashboard
            categories={categories}
            category={category}
            setCategory={setCategory}
          />
        )}
        {tab === "upload" && (
          <Upload
            onCommitted={(cat) => {
              loadCategories(cat);
              setTab("dashboard");
            }}
          />
        )}
        {tab === "settings" && (
          <Settings categories={categories} defaultCategory={category} />
        )}
      </div>
    </>
  );
}
