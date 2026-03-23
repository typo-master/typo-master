import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const cssPath = resolve(__dirname, "styles.css");
const css = readFileSync(cssPath, "utf8");

describe("flat UI css policy", () => {
  it("does not contain large radius or pill radius", () => {
    expect(css).not.toMatch(/border-radius:\s*(?:1[2-9]|[2-9]\d)px/);
    expect(css).not.toMatch(/border-radius:\s*999px/);
  });

  it("avoids panel-like light fill backgrounds", () => {
    expect(css).not.toMatch(/background:\s*#f0fdf4/);
    expect(css).not.toMatch(/background:\s*#f8fafc/);
    expect(css).not.toMatch(/background:\s*#f8fff9/);
  });
});
