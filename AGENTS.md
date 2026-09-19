# Codex Instructions — FA-IQM

This repository implements Ferro Alloy Incoming Quality Management for an integrated steel plant.

## Architecture
React/TypeScript frontend -> FastAPI backend -> SQLite for the initial application.

## Core invariant
A material batch must remain BLOCKED until an authorized quality disposition releases it. A failed result must never be silently overwritten.

## Engineering rules
- Do not hard-code new quality attributes or limits in UI logic.
- Specifications are data/configuration.
- Preserve historical results.
- Enforce workflow transitions in FastAPI.
- Use Decimal/Numeric for quality values.
- Add tests when changing quality evaluation or release rules.
- Keep frontend presentation separate from domain logic.
- Treat seed chemistry limits as illustrative only.
- Before declaring a change complete, run backend tests (when present) and `npm run build`.
