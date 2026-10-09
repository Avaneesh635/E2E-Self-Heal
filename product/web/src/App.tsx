import { useEffect, useState } from "react";

type Health = { status: "ok" | "degraded"; database: boolean };

type HealthState = { kind: "loading" } | { kind: "loaded"; health: Health } | { kind: "error" };

function statusTone(state: HealthState): string {
  if (state.kind === "loading") {
    return "border-gray-300 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300";
  }

  if (
    state.kind === "loaded" &&
    state.health.status === "ok" &&
    state.health.database
  ) {
    return "border-green-300 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200";
  }

  return "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200";
}

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
      <p
        className={`mt-4 rounded-lg border p-4 ${statusTone(state)}`}
        role="status"
        aria-live="polite">
        {state.kind === "loading" && "Checking the API…"}
        {state.kind === "error" && "The API is not reachable."}
        {state.kind === "loaded" &&
          `API: ${state.health.status} · database: ${state.health.database ? "reachable" : "unreachable"}`}
      </p>
    </main>
  );
}
