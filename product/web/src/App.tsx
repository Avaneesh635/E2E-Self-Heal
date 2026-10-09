import { useEffect, useState } from "react";

type Health = { status: "ok" | "degraded"; database: boolean };

type HealthState = { kind: "loading" } | { kind: "loaded"; health: Health } | { kind: "error" };

export function App() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    // /healthz answers 503 with a body when the database is down, so read the body either way.
    fetch("/api/healthz")
      .then((response) => response.json() as Promise<Health>)
      .then((health) => setState({ kind: "loaded", health }))
      .catch(() => setState({ kind: "error" }));
  }, []);

  return (
    <main className="mx-auto max-w-xl p-8 font-sans">
      <h1 className="text-2xl font-semibold">E2E Self-Heal</h1>
      <p className="mt-4" role="status">
        {state.kind === "loading" && "Checking the API…"}
        {state.kind === "error" && "The API is not reachable."}
        {state.kind === "loaded" &&
          `API: ${state.health.status} · database: ${state.health.database ? "reachable" : "unreachable"}`}
      </p>
    </main>
  );
}
