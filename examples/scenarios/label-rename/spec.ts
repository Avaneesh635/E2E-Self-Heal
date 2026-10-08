import { expect, test } from "@playwright/test";

// GREEN on checkout: the CTA button's accessible name is "Get started".
//
// change.patch renames the visible label to "Get started". The role, class and click handler
// are unchanged, so the accessible-name locator is the only thing to repair.
test("opens onboarding from the CTA", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Get started" }).click();
  await expect(page.getByText("Welcome!")).toBeVisible();
});
