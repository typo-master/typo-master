import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const files = [
  "components/AIChat/index.tsx",
  "pages/IntegrationDocs.tsx",
  "pages/Settings.tsx",
].map((p) => resolve(__dirname, p));

const sources = files.map((f) => readFileSync(f, "utf8")).join("\n");

describe("flat UI inline style policy", () => {
  it("does not use large/pill borderRadius in inline styles", () => {
    expect(sources).not.toMatch(/borderRadius:\s*(?:10|1[1-9]|[2-9]\d)/);
    // borderRadius: "50%" is allowed for circular avatars
    expect(sources).not.toMatch(/borderRadius:\s*"999px"/);
  });

  it("avoids panel-like inline backgrounds", () => {
    expect(sources).not.toMatch(/background:\s*"#f8fafc"/);
    expect(sources).not.toMatch(/background:\s*"#f0fdf4"/);
    // background: "#fff" is allowed as it's not a tinted panel
  });
});
