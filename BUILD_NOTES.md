# DRILLNEX SIH 2026 — Command Center Fix Build

This build preserves the existing feature set and addresses the observed UI/runtime issues:

- Copilot no longer leaves an unresolved “Retrieving evidence…” message without an actionable result.
- Copilot provides evidence, confidence, and context-aware follow-up suggestions.
- Search-backed fallback provides a grounded response if the Copilot endpoint errors.
- Sidebar has its own vertical scroll area and the workspace section remains reachable.
- Field Engineer and Office Engineer have distinct dashboard surfaces.
- Field Engineer emphasizes live operations, telemetry, alerts, risk and simulator workflows.
- Office Engineer emphasizes portfolio intelligence, historical incidents, formation patterns, documents and reporting.

Synthetic/demo data remains clearly identified; no OIL confidential data is included.


## September 29, 2026 interaction fixes
- Alert Investigate now uses delegated event handling and opens the Copilot with the selected alert context.
- Copilot follow-up suggestions use real button event listeners instead of fragile inline handlers, so they remain clickable after dynamic rendering.
- Copilot always replaces its loading state with an answer, fallback evidence, or a retry/error action.
- Report generation now has explicit loading/error states and a browser Download report action.
- The selected well is sent to the backend through `X-Drillnex-Well`, so Live, Risk, Alerts, Copilot, Reports, Map and 3D context stay aligned with the well selected in the top bar.
- Demo scenarios now surface a corresponding explainable risk pattern, so a controlled SIH scenario does not leave the Risk Intelligence page empty.
- Sidebar scrolling and Copilot suggestion containers have explicit interaction/overflow rules.

## Theme
Warm graphite surfaces with a flare-orange accent (oil & gas look). Risk colours are unchanged in meaning: red = high, amber = medium, green = low, blue = info/active well.

## Merged features
- **Drilling Performance** (`/api/performance`) — planned vs actual metrics, adherence, deviation drivers (from SIH2026 Classic Dark Brown build).
- **NPT & Cost** (`/api/npt-cost`) — NPT event register and transparent demo cost estimate (INR/hour assumption).
- **Shift Handover** (`/api/handover`) — evidence-backed handover sheet with downloadable text file (Field Engineer only).
- **Depth Risk Timeline** — ported from the drillnex-insights build; shown on the Field Engineer overview, filterable by risk pattern, zones link to evidence.

## UI changes
- Risk Intelligence page: "Why the model is concerned" replaced by a RISK AHEAD card (current depth, historical risk zone, distance, evidence, nearest similar well, formation, risk level). "View forecast" button removed from that page.
- Live Operations page and sidebar option removed.
- Copilot panel is draggable by its header; the floating button can also be dragged.
- Overview: "Most analogous historical wells" removed; Depth Risk Timeline now sits in its place beside the 500 m outlook.
- Wells page: added live search (ID, formation, reservoir, status).
- Copilot button reduced to a 46px circle.
- What-if Simulator rebuilt as an analytics view: sliders + presets, KPI cards, risk-by-driver chart, mud-weight window, NPT exposure, base vs simulated risk per pattern, sensitivity curves, saved-scenario comparison and recommendations (`/api/what-if` extended).
- Map fix: Leaflet panes/controls are isolated in their own stacking context so they no longer paint over modals (e.g. Current alerts), the top bar or Copilot; modal z-index raised; map resizes with its container.
- Dark scrollbars (removes the white scrollbar on modals/page).
- Overview: "Field engineer focus · live decision surface" card removed.
- Live telemetry redesigned: status header (pulsing state, bit depth, time), per-signal ring gauges, trend arrows, rolling sparklines and NORMAL / OUT OF BAND indicators.
- Risk Intelligence: "Risk categories" now appear only after clicking the button.
- Documents: "Repository" now appears only after clicking the button.
- Planned vs Actual Metrics redesigned: adherence dial, plan/tolerance/actual radar and per-metric deviation bullet gauges (`tolerance_pct` added to `/api/performance`).
- Overview layout: Depth Risk Timeline and Next 500 m risk outlook now sit at the bottom of the Nearby-well intelligence map card; the pressure trend graph moved to the bottom of the Explainable AI risk card (fills the empty space).
- Overview: Next 500 m risk outlook moved below the (now compact, undistorted) pressure trend in the Explainable AI risk card; Depth Risk Timeline stays under the map.
