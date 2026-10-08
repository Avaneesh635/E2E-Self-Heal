import { expect, test } from "@playwright/test";

// GREEN on checkout: the submit button is a direct child of the form.
//
// change.patch wraps it in a layout <div>, so the structural `form > button` selector no
// longer matches. The button, its id and its handler are unchanged: repair the selector only.
test("submits the form", async ({ page }) => {
  await page.goto("/");
  await page.click("form > button");
  await expect(page.getByText("Thanks!")).toBeVisible();
});
