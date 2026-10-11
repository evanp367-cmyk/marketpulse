# MarketPulse 0.4.6 — QA report

## Implemented
- Replaced compact native currency dropdowns in the converter with large, full-width currency picker buttons.
- Added a searchable modal listing currency code, full name and symbol, with clear selected-state indication.
- Added close button, Escape key handling, backdrop dismissal, background-scroll locking, and responsive mobile presentation.
- Increased the touch targets: selector triggers are at least 62 px high, result rows 68 px, and search field 54 px.
- Added light/dark theme colors to the portaled dialog so it follows the app theme.
- Kept currency conversion logic and the 250 Telegram Stars / 30-day default Pro price unchanged.

## Checks that passed
- `python3 -m compileall -q backend` passed.
- `python3 -m pytest -q`: **51 passed**.
- TypeScript/TSX syntax transpilation passed for `App.tsx`, `Chart.tsx`, `api.ts`, and `main.tsx`.
- Python AST parsing passed for backend files.
- `frontend/package.json` and `frontend/tsconfig.json` JSON parsing passed; frontend package version is `0.4.6`.
- Static checks confirmed that the picker markup and large touch-target CSS are present.

## Limitations
- `npm install --no-audit --no-fund` timed out in the isolated build environment, so the full frontend dependency-backed `npm run build` / TypeScript semantic type-check could not be verified here.
- No interactive real-browser screenshot/regression test was available in this environment. Please run `npm install`, `npm run build`, and `npm run dev` locally before deployment.
- Real Telegram invoice/payment lifecycle still requires a configured bot and an HTTPS Telegram Mini App deployment.
