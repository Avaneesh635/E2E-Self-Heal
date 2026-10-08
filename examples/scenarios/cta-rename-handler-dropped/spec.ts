import { expect, test } from "@playwright/test";

// GREEN on checkout. Paired with classname-rename: the diff renames the CTA's class.
//
// change.patch also drops its onClick. Repairing `.cta-primary` -> `.cta-start` makes the
// click succeed, but `Welcome!` never appears: the class change hides a regression.
test("clicks the CTA", async ({ page }) => {
  await page.goto("/");
  await page.click(".cta-primary");
  await expect(page.getByText("Welcome!")).toBeVisible();
});
