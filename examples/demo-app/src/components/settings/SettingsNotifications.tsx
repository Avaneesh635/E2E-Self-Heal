import { useState } from "react";

export function SettingsNotifications() {
  const [enabled, setEnabled] = useState(false);

  return (
    <section aria-labelledby="notifications-heading">
      <h2 id="notifications-heading">Notifications</h2>
      <label>
        Email notifications
        <input
          id="notifications-toggle"
          type="checkbox"
          checked={enabled}
          onChange={(event) => setEnabled(event.target.checked)}
        />
      </label>
      <p id="notifications-state">{enabled ? "On" : "Off"}</p>
    </section>
  );
}
