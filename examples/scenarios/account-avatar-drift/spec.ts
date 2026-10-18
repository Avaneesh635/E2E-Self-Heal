import { expect, test } from "@playwright/test";

test("shows the chosen avatar file name", async ({ page }) => {
  await page.goto("/#/account");
  await page.setInputFiles("#avatar-input", { name: "avatar.png", mimeType: "image/png", buffer: Buffer.from("png") });
  await expect(page.locator("#avatar-name")).toHaveText("avatar.png");
});
