import { existsSync } from "node:fs";

if (!existsSync("package.json")) {
  throw new Error("the Playwright command did not run from the consumer repository");
}

for (const pythonProjectFile of ["pyproject.toml", "uv.lock"]) {
  if (existsSync(pythonProjectFile)) {
    throw new Error(`consumer fixture must not contain ${pythonProjectFile}`);
  }
}

console.log("JavaScript-only action consumer passed");
