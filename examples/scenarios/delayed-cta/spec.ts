import { expect, test } from "@playwright/test";

// GREEN on checkout: the CTA renders immediately.
//
// change.patch renders it only after its config loads (about four seconds), longer than the
// 3s action timeout. The selector is still correct: the fix is a longer wait on the click,
// never a different selector or assertion.
test("clicks the CTA once it has loaded", async ({ page }) => {
  await page.goto("/");
  await page.click(".cta-primary");
  await expect(page.getByText("Welcome!")).toBeVisible();
});
