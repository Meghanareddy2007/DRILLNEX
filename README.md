# DRILLNEX — SIH 2026 Deployment Build

DRILLNEX is a deployment-oriented demonstration platform for SIH 2026 problem statement SIH26121. It combines offset-well intelligence, synthetic live drilling telemetry, explainable risk analysis, predictive look-ahead, document intelligence, incident replay, what-if simulation and an evidence-grounded engineering Copilot.

## Important data note

This package contains **synthetic demonstration data only**. It does not contain or claim to contain confidential Oil India data. Replace the demo repository and telemetry adapter with authorized organizational sources before production use.

## Roles

### Field Engineer
Demo account:
- Email: `field@drillnex.demo`
- Password: `DrillNex@2026`

Focus: live operations, current-well risk, alerts, offset wells, formation context, forecast, incident replay and Copilot.

### Office Engineer
Demo account:
- Email: `office@drillnex.demo`
- Password: `DrillNex@2026`

Focus: cross-well analysis, historical evidence, knowledge graph, portfolio intelligence, documents, reporting and Copilot.

For real deployment, configure `FIELD_DEMO_PASSWORD` and `OFFICE_DEMO_PASSWORD` or replace the demo authentication with the organization's identity provider.

## Features

- Direct login screen (role-based auto-fill, no landing page)
- Role-based Field Engineer / Office Engineer experience
- Persistent collapsible sidebar
- Real-time synthetic telemetry
- Similar-Well Intelligence
- Explainable AI risk scores and confidence
- Formation-aware analysis
- Next 500 m look-ahead forecast
- Grouped alert center
- Incident replay
- 3D well trajectories and incident markers
- WCR/DDR PDF/TXT ingestion with PDF text extraction and optional OCR fallback
- Institutional-memory knowledge graph
- Evidence search
- Engineering Copilot with retrieved evidence
- What-if drilling parameter simulator
- Data-quality view
- Controlled SIH demo scenarios
- Engineering report generation
- Docker / Compose / Gunicorn deployment
- `/health` and `/api/health` health endpoints

## Run on Windows

From the project root:

```powershell
py -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
cd backend
py app.py
```

Open:

`http://localhost:8080`

Or double-click:

`scripts/run_windows.bat`

## Docker

From the project root:

```bash
docker compose up --build
```

Open:

`http://localhost:8080`

Stop:

```bash
docker compose down
```

## Environment

Copy `.env.example` to `.env` and configure values as needed. Demo passwords should be changed before any non-demo deployment.

## Demo scenario flow

1. Login as Field Engineer.
2. Open **Demo & Settings**.
3. Select `MUD LOSS`, `STUCK PIPE`, `OVERPRESSURE`, or `TORQUE SPIKE`.
4. Return to **Overview** or **Live Operations**.
5. Observe telemetry changes and risk/alert context.
6. Open the floating **DRILLNEX Copilot** and ask why the risk changed.
7. Open **Offset Wells**, **500 m Forecast**, **Incident Replay**, and **Knowledge & Evidence** to show the evidence chain.
8. Login as Office Engineer to demonstrate the broader analytical workflow.

## Production boundary

The current risk calculations and what-if simulator are demonstration logic, not validated drilling engineering models. A production implementation should connect approved data sources, validated models, identity/access management, audit logging, observability and engineering review workflows.

## UX fixes in this build
- Sidebar navigation is independently scrollable on short screens; workspace items no longer disappear behind the user footer.
- Field Engineer and Office Engineer now have distinct command-center dashboards and role-specific navigation emphasis.
- Copilot returns grounded answers, evidence cards, confidence, and suggested follow-up questions.
- Copilot has a search-backed fallback if the primary copilot route fails, so the UI does not remain stuck on “Retrieving evidence…”.
- Copilot errors are rendered as actionable retry states rather than silent failures.
- Demo telemetry, risk, evidence, alerts, and historical data remain intact.

## Integrated build (DRILLNEX + eRTMAC-NWIS Insights)
New sidebar pages: **Insights** (Historical-to-Future Bridge, Risk Horizon, Institutional Memory Graph, Historical Twin Well, Why This Well?, Replay the Well, Next Best Investigation) and **3D Subsurface** (formation blocks, labelled trajectories, incident markers, full screen).
Upgraded shared features: Leaflet satellite well map with risk pins and history popups, animated risk gauge, evidence and well-history modals ("what happened next"), clickable Copilot sources, incident replay with timeline, fracture-window warning in the simulator, similarity scoring that follows the live risk pattern.
Deployment: signed stateless login tokens (set `SECRET_KEY`), single gunicorn worker with threads (telemetry state is in-process), `/api/health`, container healthcheck, pause/restart drilling clock in Demo & Settings, looping telemetry.
