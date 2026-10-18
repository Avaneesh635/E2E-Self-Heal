import { useState } from "react";

export function AccountEmail() {
  const [email, setEmail] = useState("ada@example.com");
  const [status, setStatus] = useState("Unchanged");

  return (
    <section aria-labelledby="account-email-heading">
      <h2 id="account-email-heading">Email</h2>
      <input
        id="email-input"
        aria-label="Email address"
        type="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <button id="save-email" type="button" onClick={() => setStatus(`Saved ${email}`)}>
        Save email
      </button>
      <p id="email-status">{status}</p>
    </section>
  );
}
