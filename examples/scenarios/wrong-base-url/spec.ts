import { expect, test } from "@playwright/test";

// GREEN on checkout.
//
// change.patch points the Playwright baseURL at a port nothing listens on, so navigation
// fails before any selector runs. The app and the test are fine; the environment is not.
// Nothing in the test should change.
test("submits the form", async ({ page }) => {
  await page.goto("/");
  await page.click("#submit-btn");
  await expect(page.getByText("Thanks!")).toBeVisible();
});
