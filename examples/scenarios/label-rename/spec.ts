import { expect, test } from "@playwright/test";

test("opens onboarding from the CTA", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Get started" }).click();
  await expect(page.getByText("Welcome!")).toBeVisible();
});
