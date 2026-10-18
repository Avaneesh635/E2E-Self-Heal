import { useState } from "react";

export function AccountAvatar() {
  const [fileName, setFileName] = useState("No file");

  return (
    <section aria-labelledby="account-avatar-heading">
      <h2 id="account-avatar-heading">Avatar</h2>
      <input
        id="avatar-input"
        aria-label="Avatar image"
        type="file"
        onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "No file")}
      />
      <p id="avatar-name">{fileName}</p>
    </section>
  );
}
