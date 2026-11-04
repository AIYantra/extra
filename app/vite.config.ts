import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@/src": path.resolve(__dirname, "./src"),
      "@": path.resolve(__dirname, "./src"),
    },
  },
  clearScreen: false,
  server: {
    port: 5173,
    watch: {
      usePolling: true,
      interval: 1000,
      ignored: [
        "**/src-tauri/**",
        "**/qa*/**",
        "**/qa-*/**",
        "**/qa-profile/**",
        "**/.extra/**",
        "**/dist/**",
        "**/*.png",
        "**/*.log",
        "**/*.db*",
        "**/*.sqlite*",
      ],
    },
  },
});
