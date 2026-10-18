import { useState } from "react";

export function SettingsDeleteAccount() {
  const [confirming, setConfirming] = useState(false);

  return (
    <section aria-labelledby="delete-account-heading">
      <h2 id="delete-account-heading">Delete account</h2>
      <p>This removes the account and everything in it.</p>
      <button id="delete-account" type="button" onClick={() => setConfirming(true)}>
        Delete account
      </button>
      {confirming && (
        <div id="delete-confirm" role="alertdialog">
          <p>Delete this account?</p>
        </div>
      )}
    </section>
  );
}
