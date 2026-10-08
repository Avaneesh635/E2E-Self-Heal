import { expect, test } from "@playwright/test";

// GREEN on checkout: the submit button is enabled.
//
// change.patch disables it. The click times out waiting for the element to be enabled, which
// reads like a timing failure, but no wait or force-click can submit a disabled button.
test("submits the form", async ({ page }) => {
  await page.goto("/");
  await page.click("#submit-btn");
  await expect(page.getByText("Thanks!")).toBeVisible();
});
