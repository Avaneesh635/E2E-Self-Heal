# Examples — a real React app the engine heals

A runnable **React + Vite** demo app plus a set of **scenarios** that reproduce the
situation the engine is built for: a component changes, a selector breaks, a Playwright
test fails, and the healer repairs it — end to end, against a real running app.

Unlike a hand-written static page, editing a component here produces a **real `git diff`**,
that diff **actually breaks** a test, and the healer patches the spec's selector while
leaving assertions untouched.

## Layout

```
examples/
  demo-app/                 # the React + Vite app under test
    index.html
    src/
      main.tsx
      App.tsx               # hash routing; `/` is the signup page
      components/           # actually-rendered components
        SubmitButton.tsx
        catalog/ checkout/ settings/ account/   # widgets for the four routed pages
      pages/                # CatalogPage, CheckoutPage, SettingsPage, AccountPage
  scenarios/
    id-rename/              # one scenario = component + breaking change + failing spec
      spec.ts              # the test for this scenario
      change.patch         # the real component change that breaks it
      README.md            # reproduce + heal steps
  vite.config.ts           # serves demo-app on :4173 (E2E_DEMO_PORT overrides)
  playwright.config.ts      # webServer = `pnpm build && pnpm preview`
  package.json
```

Each scenario is a **set of three**: a working component → a breaking change (a real
`git diff`) → a failing spec. The demo app is committed **green** — every spec passes on
a clean checkout — and a scenario is triggered by applying its `change.patch`.

## Setup

Requires Node and [pnpm](https://pnpm.io). From this folder:

```bash
pnpm install
pnpm exec playwright install chromium
```

## Run the tests against the real app

```bash
pnpm exec playwright test          # builds the app, serves it via vite preview, runs specs
```

Playwright's `webServer` runs `pnpm build && pnpm preview`, so the specs always run
against the freshly built app. On a clean checkout everything is green.

To develop the app interactively:

```bash
pnpm dev                            # http://localhost:4173
```

## Scenarios

Each scenario's `meta.json` labels its class and whether the right answer is to **repair** or
to **refuse** (see the
[safety benchmark reference](../docs-site/docs/reference/safety-benchmark.mdx)).

| Scenario | Class | Breakage | Expected |
| --- | --- | --- | --- |
| [`id-rename/`](scenarios/id-rename/) | `selector_drift` | button `id` renamed (`submit-btn` → `submit`) | repair |
| [`classname-rename/`](scenarios/classname-rename/) | `selector_drift` | CTA class renamed (shipped pre-applied) | repair |
| [`wrapper-added/`](scenarios/wrapper-added/) | `selector_drift` | layout wrapper breaks `form > button` | repair |
| [`jsx-context/`](scenarios/jsx-context/) | `selector_drift` | static token-benchmark fixture (not run) | repair |
| [`label-rename/`](scenarios/label-rename/) | `accessible_name_drift` | CTA label "Get started" → "Start now" | repair |
| [`delayed-cta/`](scenarios/delayed-cta/) | `timing` | CTA renders after ~4 s, past the 3 s action timeout | repair (wait only) |
| [`split-submit/`](scenarios/split-submit/) | `ambiguous` | one Submit becomes "Save draft" and "Publish" | refuse |
| [`product-regression/`](scenarios/product-regression/) | `product_regression` | form submit handler removed | refuse |
| [`id-rename-submit-dropped/`](scenarios/id-rename-submit-dropped/) | `product_regression` | same id rename as `id-rename`, but the button no longer submits | refuse |
| [`cta-rename-handler-dropped/`](scenarios/cta-rename-handler-dropped/) | `product_regression` | CTA class renamed and its `onClick` dropped | refuse |
| [`disabled-submit/`](scenarios/disabled-submit/) | `product_regression` | submit button disabled (fails like a timeout) | refuse |
| [`wrong-base-url/`](scenarios/wrong-base-url/) | `environment` | Playwright `baseURL` points at the wrong port | refuse |

### The four paired pages

Four routed pages carry four `<page>-<behaviour>-drift` / `-regression` **pairs** each. Both
twins ship the same `spec.ts` and the same failing selector: the drift patch renames the selector
and should be repaired, and the regression patch makes the same rename *and* breaks the behavior
the spec asserts, so the run should end in a refusal. The renames (id, class, `data-testid`,
`name`) and the breaks (deleted handler, wrong computation, wrong value or field, wrong event,
inverted condition, output detached from state) vary across the pairs. That pairing is what lets
the benchmark measure whether the engine can tell the two apart rather than how hard the corpus
is. Every one of these scenarios is class `selector_drift` (repair) or `product_regression`
(refuse).

| Page | Route | Scenario pairs |
| --- | --- | --- |
| [catalog](scenarios/catalog-search-drift/) | `#/catalog` | `catalog-search`, `catalog-sort`, `catalog-pagination`, `catalog-detail` |
| [checkout](scenarios/checkout-quantity-drift/) | `#/checkout` | `checkout-quantity`, `checkout-coupon`, `checkout-place-order`, `checkout-remove-item` |
| [settings](scenarios/settings-save-drift/) | `#/settings` | `settings-notifications`, `settings-save`, `settings-delete`, `settings-theme` |
| [account](scenarios/account-email-drift/) | `#/account` | `account-email`, `account-password`, `account-avatar`, `account-signout` |

The corpus is therefore 44 scenarios, 43 of them runnable, which is enough for every rate gate
in the safety benchmark to be enforced rather than reported as `insufficient_sample`.

## Heal a scenario

Only the original scenarios carry a README documenting the full reproduce-and-heal flow; the
paired page scenarios hold just `spec.ts`, `change.patch` and `meta.json`. In short, from
`examples/`:

```bash
git apply scenarios/id-rename/change.patch                     # break the app for real
pnpm exec playwright test scenarios/id-rename 2>&1 | tee scenarios/id-rename/playwright.log
e2e-healer scenarios/id-rename/spec.ts --log scenarios/id-rename/playwright.log --dry-run
```

The healer defaults to `git diff`, so the applied change is picked up automatically; pass
`--diff scenarios/<name>/change.patch` to be explicit. See
[`scenarios/id-rename/README.md`](scenarios/id-rename/README.md) for the detailed walkthrough.

## Reset after experimenting

```bash
git checkout -- demo-app scenarios      # undo applied patches and any written fixes
```
