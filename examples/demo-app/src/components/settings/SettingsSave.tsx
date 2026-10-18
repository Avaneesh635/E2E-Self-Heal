import { useState } from "react";

export function SettingsSave() {
  const [status, setStatus] = useState("Unsaved");

  return (
    <section aria-labelledby="save-heading">
      <h2 id="save-heading">Save changes</h2>
      <button id="save-settings" type="button" onClick={() => setStatus("Saved")}>
        Save settings
      </button>
      <p id="save-status">{status}</p>
    </section>
  );
}
