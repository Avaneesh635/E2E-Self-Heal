import { expect, test } from "@playwright/test";

test("clicks the CTA", async ({ page }) => {
  await page.goto("/");
  await page.click(".cta-primary");
  await expect(page.getByText("Welcome!")).toBeVisible();
});
