import { useState } from "react";

export function AccountPassword() {
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("Unchanged");

  return (
    <section aria-labelledby="account-password-heading">
      <h2 id="account-password-heading">Password</h2>
      <input
        id="password-input"
        aria-label="New password"
        type="password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      <button id="save-password" type="button" onClick={() => setStatus("Password updated")}>
        Save password
      </button>
      <p id="password-status">{status}</p>
    </section>
  );
}
