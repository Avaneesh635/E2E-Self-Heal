import { expect, test } from "@playwright/test";

test("clicks the CTA", async ({ page }) => {
  await page.goto("/");
  await page.click(".cta-button");
  await expect(page.getByText("Welcome!")).toBeVisible();
});
