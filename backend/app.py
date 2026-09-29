"""eRTMAC-NWIS prototype backend. SYNTHETIC DATA ONLY - decision support demo, not operational advice."""
import math, os, random, re
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE, "static"))
random.seed(7)
ACTIVE, LAT0, LON0 = "W-125", 27.30, 94.60
STATE = dict(depth=2810, status="DRILLING", torque=18.5, formation="XYZ Formation")
LAYERS = [dict(name="Alluvium", top=0, color="#8b7355"), dict(name="Tipam Sandstone", top=1200, color="#c9a227"),
          dict(name="XYZ Formation", top=2600, color="#2fa4a0"), dict(name="Basement", top=3200, color="#6b5b95")]

# id: (dx_km, dy_km, formation, total_depth, mud_weight, rop, wob, rpm, pressure, reservoir)
NAMED = {
    "W-125": (0, 0, "XYZ Formation", 3400, 1.20, 25, 12, 110, 285, "Sandstone"),
    "W-107": (2.1, 2.4, "XYZ Formation", 3300, 1.22, 22, 12, 110, 290, "Sandstone"),
    "W-113": (-3.5, 1.5, "XYZ Formation", 3300, 1.21, 26, 13, 105, 280, "Sandstone"),
    "W-118": (4.0, -3.0, "ABC Sandstone", 3600, 1.30, 20, 14, 95, 320, "Carbonate"),
    "W-121": (-2.0, -5.0, "Tipam Sandstone", 3100, 1.18, 28, 11, 120, 265, "Sandstone"),
    "W-109": (1.5, -3.8, "XYZ Formation", 3380, 1.22, 25, 12, 108, 288, "Sandstone"),
    "W-112": (-4.8, -1.0, "ABC Sandstone", 3250, 1.24, 23, 12, 100, 275, "Carbonate"),
}
W = {}
def add_well(i, dx, dy, f, td, mw, rop, wob, rpm, p, res):
    lat = LAT0 + dy / 111.0
    lon = LON0 + dx / (111.0 * math.cos(math.radians(lat)))
    W[i] = dict(well_id=i, latitude=round(lat, 5), longitude=round(lon, 5), total_depth=td, formation=f, mud_weight=mw,
                rop=rop, wob=wob, rpm=rpm, pressure=p, reservoir_type=res, dx=dx, dy=dy,
                sx=random.uniform(-1, 1), sy=random.uniform(-1, 1))
for i, v in NAMED.items(): add_well(i, *v)
for i in ["W-101", "W-102", "W-103", "W-104", "W-105", "W-106", "W-108", "W-110", "W-111", "W-114", "W-115", "W-116", "W-117"]:
    a, r = random.uniform(0, 6.28), random.uniform(6, 22)
    add_well(i, r * math.cos(a), r * math.sin(a), random.choice(["XYZ Formation", "ABC Sandstone", "Tipam Sandstone"]),
             random.randint(2900, 3700), round(random.uniform(1.15, 1.32), 2), random.randint(18, 30), random.randint(10, 15),
             random.randint(90, 125), random.randint(260, 330), random.choice(["Sandstone", "Carbonate"]))

def traj_pt(w, d):  # simple synthetic deviated path, metres relative to W-125 surface location
    k = (d / w["total_depth"]) ** 2 * 300
    return [round(w["dx"] * 1000 + w["sx"] * k), round(w["dy"] * 1000 + w["sy"] * k), d]
for w in W.values():
    w["trajectory"] = [traj_pt(w, d) for d in list(range(0, w["total_depth"], 200)) + [w["total_depth"]]]

EV = []
def ev(well, depth, typ, sev, cause, action, outcome, date, doc):
    EV.append(dict(event_id="EV-%03d" % (len(EV) + 1), well_id=well, depth=depth, formation=W[well]["formation"],
                   event_type=typ, severity=sev, cause=cause, action_taken=action, outcome=outcome, date=date,
                   source_document="%s_%s.pdf" % (well, doc)))
ev("W-107", 2840, "MUD_LOSS", "HIGH", "Formation fracture", "Increased mud weight", "Loss stabilized", "2024-08-14", "DDR")
ev("W-113", 2835, "MUD_LOSS", "HIGH", "Natural fractures in XYZ Formation", "Pumped loss-control material (LCM) pill", "Circulation restored", "2025-02-02", "WCR")
ev("W-109", 2825, "MUD_LOSS", "MEDIUM", "Permeable fractured zone", "Reduced pump rate and added LCM", "Partial losses cured", "2023-11-20", "DDR")
ev("W-113", 2950, "STUCK_PIPE", "HIGH", "Differential sticking across permeable sand", "Spotted pipe-freeing pill and worked string", "Pipe freed after 9 h", "2025-02-19", "DDR")
ev("W-118", 2955, "STUCK_PIPE", "MEDIUM", "Hole pack-off", "Backreamed and circulated", "Pipe freed", "2024-05-09", "DDR")
ev("W-118", 3050, "KICK", "HIGH", "Unexpected pore-pressure increase", "Shut in and weighted up mud", "Well controlled", "2024-06-01", "MLR")
ev("W-121", 2905, "CEMENTING", "MEDIUM", "Channeling, poor cement bond", "Squeeze cementing", "Bond improved", "2023-09-12", "WCR")
ev("W-109", 2920, "CEMENTING", "MEDIUM", "Cement slurry loss to formation", "Two-stage cementing", "Zonal isolation achieved", "2023-12-02", "WCR")
ev("W-112", 2980, "OVERPRESSURE", "HIGH", "Sealed sand pressure compartment", "Raised mud weight in steps", "Pressure managed", "2024-03-18", "MLR")
ev("W-107", 2990, "TORQUE_SPIKE", "LOW", "Bit balling in shale", "Reduced WOB, increased flow rate", "Torque normalised", "2024-08-22", "DDR")
ev("W-121", 3010, "FISHING", "MEDIUM", "Twist-off of drill collar", "Overshot fishing run", "Fish recovered", "2023-10-05", "DDR")
ev("W-112", 2860, "NPT", "LOW", "Top-drive failure", "Rig repair", "12 h non-productive time", "2024-03-02", "DDR")
for i in W:
    if i in NAMED: continue
    t = random.choice(["KICK", "STUCK_PIPE", "TORQUE_SPIKE", "CEMENTING", "NPT", "MUD_LOSS", "OVERPRESSURE"])
    d = random.choice([random.randint(1800, 2700), random.randint(3150, 3300)])  # keep filler events out of the demo depth band
    ev(i, d, t, random.choice(["LOW", "MEDIUM", "HIGH"]), "Recorded in daily drilling report", "Standard mitigation procedure",
       "Resolved", "2024-%02d-%02d" % (random.randint(1, 12), random.randint(1, 28)), random.choice(["DDR", "WCR", "MLR"]))
BYID = {e["event_id"]: e for e in EV}

def nice(t): return t.replace("_", " ").title()
def steps(e):  # "What happened next" timeline
    if e["event_type"] == "MUD_LOSS":
        return ["Mud loss detected at %d m" % e["depth"], "Pit level drop confirmed", e["action_taken"], "Loss rate reduced", e["outcome"], "Drilling continued"]
    return ["%s detected at %d m" % (nice(e["event_type"]), e["depth"]), "Cause assessed: " + e["cause"], e["action_taken"], e["outcome"], "Operations resumed"]
for e in EV: e["steps"] = steps(e)

def dist(a, b):
    p, q = W[a], W[b]
    la1, la2 = math.radians(p["latitude"]), math.radians(q["latitude"])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(math.radians(q["longitude"] - p["longitude"]) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
def public(w): return {k: v for k, v in w.items() if k not in ("trajectory", "sx", "sy", "dx", "dy")}
def with_xyz(e): return {**e, "xyz": traj_pt(W[e["well_id"]], e["depth"])}

# ---------------- similarity ----------------
def similar(wid):
    a, out = W[wid], []
    top = risk()["zones"][0]["event_type"]  # active well's main risk pattern
    for b in W.values():
        if b["well_id"] == wid: continue
        d = dist(wid, b["well_id"])
        sim = lambda k, s: max(0, 1 - abs(a[k] - b[k]) / s)
        params = (sim("mud_weight", .2) + sim("rop", 20) + sim("wob", 10) + sim("rpm", 60)) / 4
        types = {e["event_type"] for e in EV if e["well_id"] == b["well_id"]}
        same, dsim = a["formation"] == b["formation"], sim("total_depth", 1500)
        pat = 1 if top in types else (.3 if types else 0)
        score = .25 * math.exp(-d / 10) + .2 * same + .15 * dsim + .15 * params + .25 * pat
        reasons = (["Same formation"] if same else []) + (["Similar depth"] if dsim > .85 else []) + ["%.1f km away" % d] + \
                  (["Similar drilling parameters"] if params > .85 else []) + (["Same historical risk pattern (%s)" % nice(top)] if pat == 1 else [])
        out.append(dict(well_id=b["well_id"], similarity=round(score * 100), distance_km=round(d, 1), reasons=reasons))
    return sorted(out, key=lambda x: -x["similarity"])

# ---------------- risk engine ----------------
def risk(wid=ACTIVE, ahead=300):
    d = STATE["depth"] if wid == ACTIVE else W[wid]["total_depth"]
    groups = {}
    for e in EV:
        if e["well_id"] != wid and d <= e["depth"] <= d + ahead and dist(wid, e["well_id"]) <= 20:
            groups.setdefault(e["event_type"], []).append(e)
    zones = []
    for t, es in groups.items():
        lo, hi = min(e["depth"] for e in es), max(e["depth"] for e in es) + 10
        dd, n = lo - d, len({e["well_id"] for e in es})
        same = sum(e["formation"] == W[wid]["formation"] for e in es)
        sc = 35 + 10 * n + round(.15 * max(0, 100 - dd)) + (4 if any(e["severity"] == "HIGH" for e in es) else 0) - (0 if same else 10)
        sc = max(5, min(99, sc))
        nearest = min(es, key=lambda e: dist(wid, e["well_id"]))["well_id"]
        zones.append(dict(event_type=t, lo=lo, hi=hi, distance=dd, score=sc, level="HIGH" if sc >= 75 else "MEDIUM" if sc >= 50 else "LOW",
                          wells=sorted({e["well_id"] for e in es}), n_wells=n, same_formation=same, nearest_well=nearest,
                          event_ids=[e["event_id"] for e in es], formation=W[wid]["formation"]))
    zones.sort(key=lambda z: -z["score"])
    return dict(well_id=wid, depth=d, score=zones[0]["score"] if zones else 0, zones=zones)

# ---------------- search (TF-IDF + depth/type boosts) ----------------
TYPES = {"mud loss": "MUD_LOSS", "loss": "MUD_LOSS", "kick": "KICK", "stuck": "STUCK_PIPE", "overpressure": "OVERPRESSURE",
         "torque": "TORQUE_SPIKE", "cement": "CEMENTING", "fishing": "FISHING", "npt": "NPT"}
docs = ["%s %s %s %s %s %s" % (e["well_id"], nice(e["event_type"]), e["formation"], e["cause"], e["action_taken"], e["outcome"]) for e in EV]
VEC = TfidfVectorizer(stop_words="english"); X = VEC.fit_transform(docs)
def search(q, k=6):
    ql, cos = q.lower(), cosine_similarity(VEC.transform([q]), X)[0]
    m = re.search(r"(\d{3,4})\s*m", ql)
    typ = next((v for key, v in TYPES.items() if key in ql), None)
    res = []
    for e, c in zip(EV, cos):
        s = .5 * c + (0.8 * max(0, 1 - abs(e["depth"] - int(m.group(1))) / 100) if m else 0) + (1 if typ and e["event_type"] == typ else 0)
        if typ and e["event_type"] != typ: continue
        if s > .25: res.append({**e, "score": round(s, 2)})
    return sorted(res, key=lambda r: -r["score"])[:k]

# ---------------- API ----------------
@app.get("/")
def index(): return send_from_directory(os.path.join(BASE, "static"), "index.html")
@app.get("/api/wells")
def wells(): return jsonify([public(w) for w in W.values()])
@app.get("/api/wells/nearby")
def nearby():
    r, out = float(request.args.get("radius", 10)), []
    for w in W.values():
        d = dist(ACTIVE, w["well_id"])
        if d <= r:
            es = [e for e in EV if e["well_id"] == w["well_id"]]
            out.append({**public(w), "distance_km": round(d, 1), "event_count": len(es), "types": sorted({e["event_type"] for e in es}),
                        "active": w["well_id"] == ACTIVE})
    return jsonify(out)
@app.get("/api/wells/similar/<wid>")
def sim(wid): return jsonify(similar(wid))
@app.get("/api/wells/<wid>")
def well(wid): return jsonify({**public(W[wid]), **(STATE if wid == ACTIVE else {})})
@app.get("/api/wells/<wid>/events")
def well_events(wid): return jsonify([e for e in EV if e["well_id"] == wid])
@app.get("/api/events")
def events(): return jsonify(EV)
@app.get("/api/risk/<wid>")
def risk_api(wid): return jsonify(risk(wid))
@app.get("/api/timeline/<wid>")
def timeline(wid): return jsonify(sorted([e for e in EV if e["well_id"] == wid], key=lambda e: e["depth"]))
@app.get("/api/evidence/<eid>")
def evidence(eid):
    e = BYID[eid]
    return jsonify({**e, "document_type": {"DDR": "Daily Drilling Report", "WCR": "Well Completion Report", "MLR": "Mud Logging Report"}[e["source_document"][6:9]],
                    "note": "Synthetic document generated for demonstration."})
@app.get("/api/3d")
def d3():
    ws = [w for w in W.values() if dist(ACTIVE, w["well_id"]) <= 10]
    return jsonify(wells=[{**public(w), "trajectory": w["trajectory"], "active": w["well_id"] == ACTIVE} for w in ws],
                   events=[with_xyz(e) for e in EV if e["well_id"] in {w["well_id"] for w in ws}], layers=LAYERS)
@app.post("/api/search")
def search_api(): return jsonify(search(request.get_json().get("query", "")))
@app.post("/api/copilot")
def copilot():
    q = request.get_json().get("query", ""); ql = q.lower()
    if "similar" in ql:
        s = similar(ACTIVE)[:3]
        return jsonify(answer="Most similar wells to %s (prototype score): %s." % (ACTIVE, "; ".join("%s %d%%" % (x["well_id"], x["similarity"]) for x in s)), sources=[])
    mit = any(k in ql for k in ("mitigat", "action", "handle", "fix", "used"))
    if mit and not any(k in ql for k in TYPES):  # follow-up style question: assume the active alert's risk type
        q += " " + nice(risk()["zones"][0]["event_type"]).lower()
    res = search(q, 5)
    if not res: return jsonify(answer="No matching records in the synthetic knowledge base.", sources=[])
    t = res[0]["event_type"]; grp = [e for e in res if e["event_type"] == t]
    grp = [e for e in grp if abs(e["depth"] - STATE["depth"]) <= 300] or grp  # prefer records near the current depth
    closest = min(grp, key=lambda e: dist(ACTIVE, e["well_id"]))
    if mit: ans = "; ".join("%s: %s (%s)" % (e["well_id"], e["action_taken"].lower(), e["outcome"].lower()) for e in grp) + "."
    else:
        ans = "%d nearby wells recorded %s events between %d m and %d m (%s). Closest comparable case is %s at %d m: %s; outcome: %s." % (
            len({e["well_id"] for e in grp}), nice(t).lower(), min(e["depth"] for e in grp), max(e["depth"] for e in grp),
            ", ".join(sorted({e["well_id"] for e in grp})), closest["well_id"], closest["depth"], closest["cause"].lower(), closest["outcome"].lower())
    src = [dict(event_id=e["event_id"], label="%s %s - %s - %dm" % (e["well_id"], e["source_document"][6:9],
           datetime.strptime(e["date"], "%Y-%m-%d").strftime("%d %b %Y"), e["depth"])) for e in grp]
    return jsonify(answer=ans, sources=src)
@app.post("/api/what-if")
def what_if():
    p = request.get_json()
    mw, rop, wob, rpm = (float(p.get(k, d)) for k, d in (("mud_weight", 1.20), ("rop", 25), ("wob", 12), ("rpm", 110)))
    base = risk()["score"]
    # Toy heuristic: heavier mud helps up to an assumed fracture window (1.28 SG), then hurts; aggressive drilling adds risk.
    delta = -(min(mw, 1.28) - 1.20) * 280 + max(0, mw - 1.28) * 400 + (rop - 25) * .3 + (wob - 12) * .5 + (rpm - 110) * .05
    load = abs(mw - 1.2) * 10 + abs(rop - 25) / 25 + abs(wob - 12) / 12 + abs(rpm - 110) / 110
    return jsonify(base=base, simulated=round(max(5, min(99, base + delta))), impact="Low" if load < .5 else "Moderate" if load < 1.2 else "High",
                   warning="Mud weight above assumed fracture window" if mw > 1.28 else None,
                   note="Prototype simulation - not an operational drilling recommendation.")

if __name__ == "__main__":
    print("Open http://127.0.0.1:5050"); app.run(port=5050, debug=True)
