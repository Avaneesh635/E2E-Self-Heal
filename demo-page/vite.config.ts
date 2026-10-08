import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Port 4174 so it can run next to the examples demo app (4173) during a presentation.
export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: { port: 4174 },
    preview: { port: 4174 },
});
