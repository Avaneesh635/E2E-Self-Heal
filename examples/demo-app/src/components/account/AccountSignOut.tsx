import { useState } from "react";

export function AccountSignOut() {
  const [status, setStatus] = useState("Signed in");

  return (
    <section aria-labelledby="account-signout-heading">
      <h2 id="account-signout-heading">Session</h2>
      <p id="signed-out">{status}</p>
      <button id="sign-out" type="button" onClick={() => setStatus("Signed out")}>
        Sign out
      </button>
    </section>
  );
}
