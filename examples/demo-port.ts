// The port the demo app is served on, shared by the Vite and Playwright configs.
// `E2E_DEMO_PORT` lets two checkouts run the suite at once without one reusing the other's
// preview server (and therefore its build). A value that is not a usable TCP port fails
// here instead of turning into port 0 or NaN further down.
export function demoPort(): number {
  const raw = process.env.E2E_DEMO_PORT ?? "4173";
  const port = Number(raw);
  if (!/^\d+$/.test(raw) || port < 1 || port > 65_535) {
    throw new Error(`E2E_DEMO_PORT must be an integer between 1 and 65535, got "${raw}"`);
  }
  return port;
}
