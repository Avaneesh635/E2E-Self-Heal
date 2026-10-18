import { useEffect, useState, type FormEvent } from "react";

import { SubmitButton } from "./components/SubmitButton";
import { CTAButton } from "./components/CTAButton";
import { AccountPage } from "./pages/AccountPage";
import { CatalogPage } from "./pages/CatalogPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { SettingsPage } from "./pages/SettingsPage";

type Route = "home" | "catalog" | "checkout" | "settings" | "account";

const PAGES: Route[] = ["catalog", "checkout", "settings", "account"];

// Hash routing, so every page is a static file the preview server already serves and a
// scenario can `page.goto("/#/catalog")` without adding a router dependency. An empty or
// unknown hash is the home page, so `/` keeps rendering the signup form the first
// scenarios were written against.
function routeFromHash(): Route {
  const name = window.location.hash.replace(/^#\/?/, "");
  return PAGES.includes(name as Route) ? (name as Route) : "home";
}

export function App() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  const [submitted, setSubmitted] = useState(false);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const onHashChange = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <main>
      <nav>
        <a href="#/">Home</a> <a href="#/catalog">Catalog</a> <a href="#/checkout">Checkout</a>{" "}
        <a href="#/settings">Settings</a> <a href="#/account">Account</a>
      </nav>

      {route === "home" && (
        <>
          <h1>Sign up</h1>
          <form onSubmit={handleSubmit}>
            <label>
              Name
              <input name="name" defaultValue="Ada" />
            </label>
            <SubmitButton />
          </form>
          {submitted && <p id="result">Thanks!</p>}

          <section aria-labelledby="cta-heading">
            <h2 id="cta-heading">Get started</h2>
            <CTAButton onClick={() => setStarted(true)} />
            {started && <p>Welcome!</p>}
          </section>
        </>
      )}

      {route === "catalog" && <CatalogPage />}
      {route === "checkout" && <CheckoutPage />}
      {route === "settings" && <SettingsPage />}
      {route === "account" && <AccountPage />}
    </main>
  );
}
