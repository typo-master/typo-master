# Flat UI No-Large-Radius Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove large rounded corners and panel-style background fills across frontend pages/components (CSS + TSX inline styles) while keeping behavior unchanged.

**Architecture:** Use component-level edits in existing files only. First capture/lock failing style expectations via targeted tests, then implement minimal CSS and inline-style changes per file group, and verify with focused test runs + route smoke checks. Keep visual semantics readable using transparent/white backgrounds and small/no radius.

**Tech Stack:** React + TypeScript + Ant Design + project CSS + Vitest (new focused tests)

---

## File Map

- Modify: `app/frontend/src/styles.css`
  - Responsibility: shared/global visual rules and per-page CSS classes.
- Modify: `app/frontend/src/components/AIChat/index.tsx`
  - Responsibility: chat panel/list/message inline visual styles.
- Modify: `app/frontend/src/pages/IntegrationDocs.tsx`
  - Responsibility: docs code block header/body inline visual styles.
- Modify: `app/frontend/src/pages/Settings.tsx`
  - Responsibility: warning card inline background style.
- Modify (only if needed): `app/frontend/src/pages/Workspace.tsx`
  - Responsibility: avatar/accent-only inline styles (retain non-panel state accents unless violating goal).
- Create: `app/frontend/src/styles.flat-ui.test.ts`
  - Responsibility: assert no large radii/pill radii and no panel-like CSS backgrounds.
- Create: `app/frontend/src/inline-styles.flat-ui.test.ts`
  - Responsibility: assert inline TSX style literals avoid large radii/panel backgrounds.

## Task 1: Add failing tests for flat UI policy

**Files:**
- Create: `app/frontend/src/styles.flat-ui.test.ts`
- Create: `app/frontend/src/inline-styles.flat-ui.test.ts`
- Test: `app/frontend/src/styles.flat-ui.test.ts`, `app/frontend/src/inline-styles.flat-ui.test.ts`

- [ ] **Step 1: Write failing CSS policy test**

```ts
// app/frontend/src/styles.flat-ui.test.ts
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
```

- [ ] **Step 2: Write failing TSX inline-style policy test**

```ts
// app/frontend/src/inline-styles.flat-ui.test.ts
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
    expect(sources).not.toMatch(/borderRadius:\s*"50%"/);
    expect(sources).not.toMatch(/borderRadius:\s*"999px"/);
  });

  it("avoids panel-like inline backgrounds", () => {
    expect(sources).not.toMatch(/background:\s*"#f8fafc"/);
    expect(sources).not.toMatch(/background:\s*"#f0fdf4"/);
    expect(sources).not.toMatch(/background:\s*"#fff"/);
  });
});
```

- [ ] **Step 3: Run tests to verify failures**

Run:
`npm --prefix app/frontend run test -- styles.flat-ui.test.ts inline-styles.flat-ui.test.ts`

Expected: FAIL due to existing large radii/background literals.

- [ ] **Step 4: Commit tests**

```bash
git add app/frontend/src/styles.flat-ui.test.ts app/frontend/src/inline-styles.flat-ui.test.ts
git commit -m "test(frontend): add flat UI visual policy tests"
```

## Task 2: Remove large radii and panel backgrounds in shared CSS

**Files:**
- Modify: `app/frontend/src/styles.css`
- Test: `app/frontend/src/styles.flat-ui.test.ts`

- [ ] **Step 1: Update large radii in marketing blocks**

Edit these selectors to 0-4px radii:
- `.home-page-marketing section` (18px -> 0 or 4)
- `.marketing-badge`, `.marketing-status-tags .ant-tag`, `.marketing-highlight-line span` (999px -> 2/4)
- `.marketing-metric-card`, `.marketing-value-card`, `.marketing-capability-card`, `.marketing-usecase-card`, `.marketing-integration-card`, `.marketing-steps-card`, `.marketing-final-card` (12/16px -> 0/4)
- `.marketing-value-icon`, `.marketing-capability-icon` (11px -> 2/4)

- [ ] **Step 2: Remove panel-like light fill backgrounds**

Replace panel backgrounds with transparent/white where possible:
- `body`, `.main-content`, `.features-section`, `.languages-section`, `.scenarios-section`
- `.home-page-marketing section`, `.marketing-section-alt`, `.marketing-final-card`
- `.settings-page .ant-tabs-card > .ant-tabs-nav .ant-tabs-tab` and active tab fills
- any `#f0fdf4/#f8fafc/#f8fff9` panel fills

Keep only purposeful brand gradients (header/hero/cta) unless they are used as panel fills.

- [ ] **Step 3: Keep readability separators**

Where background removal reduces contrast, keep 1px border (`var(--line)` or green neutral) and mild shadow only if necessary.

- [ ] **Step 4: Run CSS policy test**

Run:
`npm --prefix app/frontend run test -- styles.flat-ui.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit CSS changes**

```bash
git add app/frontend/src/styles.css
git commit -m "style(frontend): flatten shared css radii and panel backgrounds"
```

## Task 3: Remove large radii/panel backgrounds from inline styles

**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx`
- Modify: `app/frontend/src/pages/IntegrationDocs.tsx`
- Modify: `app/frontend/src/pages/Settings.tsx`
- Modify: `app/frontend/src/pages/Workspace.tsx` (only if needed)
- Test: `app/frontend/src/inline-styles.flat-ui.test.ts`

- [ ] **Step 1: Update AIChat inline styles**

In `app/frontend/src/components/AIChat/index.tsx`, change:
- `borderRadius: 6/8/10` -> `0/2/4`
- `borderRadius: "50%"` -> `2` (or small fixed radius)
- `background: "#f8fafc"` -> `"transparent"`
- `background: "#fff"` panel wrappers -> `"transparent"` (or `"#fff"` only if readability breaks)
- chat bubble color accents can remain if they indicate user/assistant role and are not panel fills.

- [ ] **Step 2: Update IntegrationDocs inline styles**

In `app/frontend/src/pages/IntegrationDocs.tsx`:
- replace `borderRadius: "8px 8px 0 0"` and `"8px"` with small/flat values.
- replace panel-like backgrounds where possible with transparent/white while preserving code readability contrast.

- [ ] **Step 3: Update Settings inline warning card**

In `app/frontend/src/pages/Settings.tsx`:
- replace `backgroundColor: "#fff7e6"` with transparent/white approach consistent with new visual rule.

- [ ] **Step 4: Re-check workspace inline styles**

In `app/frontend/src/pages/Workspace.tsx`:
- keep Avatar accent background if it is status/accent and not panel-like;
- only adjust if it visually violates agreed style target.

- [ ] **Step 5: Run inline policy test**

Run:
`npm --prefix app/frontend run test -- inline-styles.flat-ui.test.ts`

Expected: PASS.

- [ ] **Step 6: Commit inline style changes**

```bash
git add app/frontend/src/components/AIChat/index.tsx app/frontend/src/pages/IntegrationDocs.tsx app/frontend/src/pages/Settings.tsx app/frontend/src/pages/Workspace.tsx
git commit -m "style(frontend): flatten inline panel styles in key pages"
```

## Task 4: End-to-end verification and cleanup

**Files:**
- Modify: (only if fixes required after verification)
- Test: all tests above + app smoke

- [ ] **Step 1: Run focused tests together**

Run:
`npm --prefix app/frontend run test -- styles.flat-ui.test.ts inline-styles.flat-ui.test.ts`

Expected: PASS.

- [ ] **Step 2: Run frontend build or lint check (whichever project uses)**

Run one of:
- `npm --prefix app/frontend run build`
- or `npm --prefix app/frontend run lint`

Expected: PASS (no type/style regression).

- [ ] **Step 3: Manual route smoke checks**

Open and visually verify:
- `/`
- `/workspace`
- `/settings`
- `/docs`

Checks:
- No obvious large radius/pill surfaces.
- Panel backgrounds mostly transparent/white.
- Readability preserved.
- No behavior change.

- [ ] **Step 4: Final commit for verification fixes (if any)**

```bash
git add app/frontend/src/styles.css app/frontend/src/components/AIChat/index.tsx app/frontend/src/pages/IntegrationDocs.tsx app/frontend/src/pages/Settings.tsx app/frontend/src/pages/Workspace.tsx
git commit -m "chore(frontend): finalize flat UI verification adjustments"
```

## Notes for execution

- Keep edits minimal and local; no refactor/restructure.
- Do not change business logic or API behavior.
- If a background is required for readability, prefer `#fff` over tinted panel colors.
- If any test regex is too strict for legitimate exceptions, narrow the regex with explicit allowlist comments in test file.
