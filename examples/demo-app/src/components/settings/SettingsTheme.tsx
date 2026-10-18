import { useState } from "react";

export function SettingsTheme() {
  const [theme, setTheme] = useState("light");

  return (
    <section aria-labelledby="theme-heading">
      <h2 id="theme-heading">Theme</h2>
      <label>
        Theme
        <select id="theme-select" value={theme} onChange={(event) => setTheme(event.target.value)}>
          <option value="light">light</option>
          <option value="dark">dark</option>
        </select>
      </label>
      <p id="theme-indicator">{theme}</p>
    </section>
  );
}
