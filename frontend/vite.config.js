import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/merchant": "http://127.0.0.1:8000",
      "/model": "http://127.0.0.1:8000",
      "/stream": "http://127.0.0.1:8000",
      "/demo": "http://127.0.0.1:8000",
      "/cue": "http://127.0.0.1:8000",
      "/act": "http://127.0.0.1:8000",
      "/scoreboard": "http://127.0.0.1:8000",
      "/budget": "http://127.0.0.1:8000",
    },
  },
});
