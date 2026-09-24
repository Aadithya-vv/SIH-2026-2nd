import { env } from "node:process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } },
  },
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": env.FIP_API_TARGET ?? "http://127.0.0.1:8000",
      "/health": env.FIP_API_TARGET ?? "http://127.0.0.1:8000",
    },
  },
});
