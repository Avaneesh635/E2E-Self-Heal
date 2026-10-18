import { SettingsDeleteAccount } from "../components/settings/SettingsDeleteAccount";
import { SettingsNotifications } from "../components/settings/SettingsNotifications";
import { SettingsSave } from "../components/settings/SettingsSave";
import { SettingsTheme } from "../components/settings/SettingsTheme";

export function SettingsPage() {
  return (
    <section aria-labelledby="settings-heading">
      <h1 id="settings-heading">Settings</h1>
      <SettingsNotifications />
      <SettingsSave />
      <SettingsDeleteAccount />
      <SettingsTheme />
    </section>
  );
}
