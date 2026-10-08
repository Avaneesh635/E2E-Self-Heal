import { expect, test } from "@playwright/test";

// GREEN on checkout. Paired with id-rename: the diff renames the same id the same way.
//
// change.patch also turns the button into type="button", so it no longer submits the form.
// Repairing `#submit-btn` -> `#submit` makes the click succeed, but `Thanks!` never appears.
// A healer that only looks at the id change would call this drift; it is a regression.
test("submits the form", async ({ page }) => {
  await page.goto("/");
  await page.click("#submit-btn");
  await expect(page.getByText("Thanks!")).toBeVisible();
});
