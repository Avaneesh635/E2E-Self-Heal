import { AccountAvatar } from "../components/account/AccountAvatar";
import { AccountEmail } from "../components/account/AccountEmail";
import { AccountPassword } from "../components/account/AccountPassword";
import { AccountSignOut } from "../components/account/AccountSignOut";

export function AccountPage() {
  return (
    <section aria-labelledby="account-heading">
      <h1 id="account-heading">Account</h1>
      <AccountEmail />
      <AccountPassword />
      <AccountAvatar />
      <AccountSignOut />
    </section>
  );
}
