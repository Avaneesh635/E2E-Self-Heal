import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// /api/* goes to the FastAPI dev server, so the browser never needs CORS during development.
const api = { "/api": { target: "http://localhost:8000", rewrite: (path: string) => path.replace(/^\/api/, "") } };

export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: { proxy: api },
    preview: { proxy: api },
});
