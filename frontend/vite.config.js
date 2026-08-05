import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output goes into the backend so FastAPI can serve it as one service.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../backend/app/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
