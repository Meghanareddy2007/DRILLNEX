# eRTMAC-NWIS (prototype) — Nearby Wells Intelligence System
Decision-support demo using **synthetic data only**. Not real OIL data, not an operational drilling recommendation.

## Run
    cd nwis
    python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    cd backend && python app.py
Open http://127.0.0.1:5000 (internet needed for map tiles / CDN libraries).

## Demo flow
Overview (W-125 @ 2810 m, RISK AHEAD) → Why? → View Similar Wells (W-107 ≈91%) → click W-107 → timeline → View Evidence
→ 3D Subsurface → What-If (mud weight 1.20→1.25: 82→68) → NWIS Copilot: "What happened around 2840m?"

## API
GET /api/wells | /api/wells/<id> | /api/wells/<id>/events | /api/wells/nearby?radius=10 | /api/wells/similar/<id>
GET /api/risk/<id> | /api/timeline/<id> | /api/evidence/<event_id> | /api/events | /api/3d
POST /api/search {query} | /api/copilot {query} | /api/what-if {mud_weight,rop,wob,rpm}
