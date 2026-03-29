# 2026-03-24 Flat UI No-Large-Radius Design

## Goal
Apply component-level visual adjustments across the frontend so the app avoids large rounded corners and avoids panel-like background fills. Keep interaction/logic unchanged.

## Scope
- Files: `app/frontend/src/styles.css` and TSX files that use inline panel backgrounds/radius.
- In scope: visual tokens and inline style values for radius/background.
- Out of scope: functional behavior, layout flow logic, API/data behavior.

## Confirmed constraints from user
1. Banner full-width was previously handled separately.
2. For this task: remove large corner radii globally in practice (component-by-component edits), and reduce panel backgrounds significantly.
3. Preference level: close to white/transparent overall page feel.
4. Chosen implementation approach: **component-level refactor (TSX inline + CSS)**.

## Candidate approaches reviewed
1. Global override layer (fast, broad) — not selected.
2. Module-only CSS edits (moderate) — not selected.
3. Component-level edits in CSS + TSX inline styles (precise) — **selected by user**.

## Design

### Visual rules
- Radius policy:
  - Disallow obvious large radii (`>= 12px`, and pill styles like `999px`).
  - Prefer `0-4px` for controls and cards.
- Background policy:
  - Remove panel-like fill backgrounds where possible.
  - Prefer `transparent`; if needed for readability, use plain `#fff`.
  - Keep gradients only where intentional brand hero requires contrast and user has not requested removal for that specific element.

### Edit strategy
1. Update CSS blocks with large radii and panel fills in `styles.css`.
2. Update TSX inline style objects containing panel backgrounds or large radii in:
   - `app/frontend/src/components/AIChat/index.tsx`
   - `app/frontend/src/pages/IntegrationDocs.tsx`
   - `app/frontend/src/pages/Workspace.tsx`
   - `app/frontend/src/components/TriggerManager/index.tsx`
   - `app/frontend/src/components/SkillList/index.tsx`
   - other files found by search if they define panel-like inline backgrounds.
3. Keep color accents used as state indicators if they are not panel backgrounds.

### Validation
- Manual smoke review routes:
  - `/`
  - `/workspace`
  - `/settings`
  - `/docs`
- Confirm no major pill/large-card radius remains and page look is predominantly white/transparent.
- Ensure no runtime errors from style edits.

### Risks and mitigations
- Risk: readability loss where panel background carried contrast.
  - Mitigation: fallback to white fill (`#fff`) only where needed.
- Risk: CSS vs inline precedence mismatch.
  - Mitigation: update inline style values directly in TSX for key components.

## Test plan
- Open major pages and visually verify radius/background policy.
- Confirm interactions still work (tabs, list selection, chat messages, docs code blocks).

## Expected output
- Pure visual cleanup PR-sized change set with no behavior change.
