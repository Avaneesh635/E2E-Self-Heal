import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { demoPort } from "./demo-port";

// The demo app lives under `demo-app/`. Both the dev server (`npm run dev`) and the
// static preview server (`npm run preview`, used by Playwright's webServer) bind to the
// same port so specs can target a single stable baseURL; `E2E_DEMO_PORT` overrides it (see
// demo-port.ts).
const port = demoPort();

export default defineConfig({
  root: "demo-app",
  plugins: [react()],
  server: { port, strictPort: true },
  preview: { port, strictPort: true },
});
