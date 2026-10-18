import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The demo app lives under `demo-app/`. Both the dev server (`npm run dev`) and the
// static preview server (`npm run preview`, used by Playwright's webServer) bind to the
// same port so specs can target a single stable baseURL. `E2E_DEMO_PORT` overrides it so
// two checkouts can run the suite at the same time without one reusing the other's build.
const port = Number(process.env.E2E_DEMO_PORT ?? "4173");

export default defineConfig({
  root: "demo-app",
  plugins: [react()],
  server: { port, strictPort: true },
  preview: { port, strictPort: true },
});
