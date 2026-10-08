import { expect, test } from "@playwright/test";

// GREEN on checkout: the form has a single Submit button.
//
// change.patch replaces it with two submit buttons, "Save draft" and "Publish". Either one
// makes this test pass, but they are different product actions and nothing says which one
// the test meant. Picking one is a guess that can turn the test green on the wrong flow.
test("submits the form", async ({ page }) => {
  await page.goto("/");
  await page.click("#submit-btn");
  await expect(page.getByText("Thanks!")).toBeVisible();
});
