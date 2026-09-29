"""Synthetic demonstration dataset for eRTMAC-NWIS / SIH 2026.
No OIL confidential data is included. Replace repository adapters with authorized sources in production.
"""
import math, random
from datetime import datetime, timedelta

SEED = 42
random.seed(SEED)
ACTIVE = "W-125"
LAT0, LON0 = 27.30, 94.60

NAMED = {
    "W-125": (0, 0, "XYZ Formation", 3400, 1.20, 25, 12, 110, 285, "Sandstone"),
    "W-107": (2.1, 2.4, "XYZ Formation", 3300, 1.22, 22, 12, 110, 290, "Sandstone"),
    "W-113": (-3.5, 1.5, "XYZ Formation", 3300, 1.21, 26, 13, 105, 280, "Sandstone"),
    "W-118": (4.0, -3.0, "ABC Sandstone", 3600, 1.30, 20, 14, 95, 320, "Carbonate"),
    "W-121": (-2.0, -5.0, "Tipam Sandstone", 3100, 1.18, 28, 11, 120, 265, "Sandstone"),
    "W-109": (1.5, -3.8, "XYZ Formation", 3380, 1.22, 25, 12, 108, 288, "Sandstone"),
    "W-112": (-4.8, -1.0, "ABC Sandstone", 3250, 1.24, 23, 12, 100, 275, "Carbonate"),
}

WELLS = {}
def add_well(i, dx, dy, f, td, mw, rop, wob, rpm, p, reservoir):
    lat = LAT0 + dy / 111.0
    lon = LON0 + dx / (111.0 * math.cos(math.radians(lat)))
    WELLS[i] = {
        "well_id": i, "latitude": round(lat, 5), "longitude": round(lon, 5),
        "total_depth": td, "formation": f, "mud_weight": mw, "rop": rop,
        "wob": wob, "rpm": rpm, "pressure": p, "reservoir_type": reservoir,
        "dx": dx, "dy": dy, "trajectory": []
    }

for i, v in NAMED.items():
    add_well(i, *v)

for i in ["W-101","W-102","W-103","W-104","W-105","W-106","W-108","W-110","W-111","W-114","W-115","W-116","W-117"]:
    a, r = random.uniform(0, 2*math.pi), random.uniform(6, 22)
    add_well(i, r*math.cos(a), r*math.sin(a),
             random.choice(["XYZ Formation","ABC Sandstone","Tipam Sandstone"]),
             random.randint(2900,3700), round(random.uniform(1.15,1.32),2),
             random.randint(18,30), random.randint(10,15), random.randint(90,125),
             random.randint(260,330), random.choice(["Sandstone","Carbonate"]))

def traj_pt(w, d):
    k=(d/w["total_depth"])**2*300
    return [round(w["dx"]*1000+w["dx"]*0.04+k*0.4,1),
            round(w["dy"]*1000+w["dy"]*0.04+k*0.2,1), d]

for w in WELLS.values():
    w["trajectory"]=[traj_pt(w,d) for d in list(range(0,w["total_depth"],200))+[w["total_depth"]]]

EVENTS=[]
def add_event(well, depth, typ, sev, cause, action, outcome, date, doc, evidence=None):
    EVENTS.append({
        "event_id": f"EV-{len(EVENTS)+1:03d}", "well_id":well, "depth":depth,
        "formation":WELLS[well]["formation"], "event_type":typ, "severity":sev,
        "cause":cause, "action_taken":action, "outcome":outcome, "date":date,
        "source_document":f"{well}_{doc}.pdf",
        "evidence": evidence or [f"{well} historical report", f"Depth {depth} m"]
    })

add_event("W-107",2840,"MUD_LOSS","HIGH","Formation fracture","Increased mud weight","Loss stabilized","2024-08-14","DDR",
          ["Pit-volume decline","Losses at 2,840 m","Mud weight increased"])
add_event("W-113",2835,"MUD_LOSS","HIGH","Natural fractures in XYZ Formation","Pumped loss-control material (LCM) pill","Circulation restored","2025-02-02","WCR",
          ["Loss rate increased","Fractured XYZ interval","LCM pill restored circulation"])
add_event("W-109",2825,"MUD_LOSS","MEDIUM","Permeable fractured zone","Reduced pump rate and added LCM","Partial losses cured","2023-11-20","DDR",
          ["Partial losses","Reduced pump rate","LCM added"])
add_event("W-113",2950,"STUCK_PIPE","HIGH","Differential sticking across permeable sand","Spotted pipe-freeing pill and worked string","Pipe freed after 9 h","2025-02-19","DDR")
add_event("W-118",2955,"STUCK_PIPE","MEDIUM","Hole pack-off","Backreamed and circulated","Pipe freed","2024-05-09","DDR")
add_event("W-118",3050,"KICK","HIGH","Unexpected pore-pressure increase","Shut in and weighted up mud","Well controlled","2024-06-01","MLR")
add_event("W-121",2905,"CEMENTING","MEDIUM","Channeling, poor cement bond","Squeeze cementing","Bond improved","2023-09-12","WCR")
add_event("W-109",2920,"CEMENTING","MEDIUM","Cement slurry loss to formation","Two-stage cementing","Zonal isolation achieved","2023-12-02","WCR")
add_event("W-112",2980,"OVERPRESSURE","HIGH","Sealed sand pressure compartment","Raised mud weight in steps","Pressure managed","2024-03-18","MLR")
add_event("W-107",2990,"TORQUE_SPIKE","LOW","Bit balling in shale","Reduced WOB, increased flow rate","Torque normalised","2024-08-22","DDR")
add_event("W-121",3010,"FISHING","MEDIUM","Twist-off of drill collar","Overshot fishing run","Fish recovered","2023-10-05","DDR")
add_event("W-112",2860,"NPT","LOW","Top-drive failure","Rig repair","12 h non-productive time","2024-03-02","DDR")

for i in WELLS:
    if i in NAMED: continue
    t=random.choice(["KICK","STUCK_PIPE","TORQUE_SPIKE","CEMENTING","NPT","MUD_LOSS","OVERPRESSURE"])
    d=random.choice([random.randint(1800,2700),random.randint(3150,3300)])
    add_event(i,d,t,random.choice(["LOW","MEDIUM","HIGH"]),
              "Recorded in daily drilling report","Standard mitigation procedure","Resolved",
              f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",random.choice(["DDR","WCR","MLR"]))

DOCUMENTS=[]
for e in EVENTS:
    DOCUMENTS.append({
        "document_id": e["event_id"].replace("EV","DOC"),
        "well_id": e["well_id"], "type": e["source_document"].split("_")[-1].replace(".pdf",""),
        "title": e["source_document"], "date": e["date"], "depth": e["depth"],
        "text": (
            f"Well {e['well_id']}. Daily drilling record at depth {e['depth']} m. "
            f"Formation {e['formation']}. Incident {e['event_type'].replace('_',' ').title()}. "
            f"Cause: {e['cause']}. Action: {e['action_taken']}. Outcome: {e['outcome']}. "
            f"Historical evidence: {'; '.join(e['evidence'])}."
        )
    })

FORMATIONS=[
    {"name":"Alluvium","top":0,"bottom":1200,"risk":"LOW"},
    {"name":"Tipam Sandstone","top":1200,"bottom":2600,"risk":"MEDIUM"},
    {"name":"XYZ Formation","top":2600,"bottom":3200,"risk":"HIGH"},
    {"name":"Basement","top":3200,"bottom":3400,"risk":"LOW"},
]

def distance(a,b):
    p,q=WELLS[a],WELLS[b]
    la1,la2=math.radians(p["latitude"]),math.radians(q["latitude"])
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin(math.radians(q["longitude"]-p["longitude"])/2)**2
    return 2*6371*math.asin(math.sqrt(h))

def public_well(w):
    return {k:v for k,v in w.items() if k not in ("dx","dy")}

def event_xyz(e):
    return {**e,"xyz":traj_pt(WELLS[e["well_id"]],e["depth"])}

def _steps(e):
    t=e["event_type"].replace("_"," ").title()
    if e["event_type"]=="MUD_LOSS": return ["Mud loss detected at %d m"%e["depth"],"Pit level drop confirmed",e["action_taken"],"Loss rate reduced",e["outcome"],"Drilling continued"]
    return ["%s detected at %d m"%(t,e["depth"]),"Cause assessed: "+e["cause"],e["action_taken"],e["outcome"],"Operations resumed"]
for _e in EVENTS: _e["steps"]=_steps(_e)
LAYERS=[dict(name="Alluvium",top=0,color="#8b7355"),dict(name="Tipam Sandstone",top=1200,color="#c9a227"),dict(name="XYZ Formation",top=2600,color="#2fa4a0"),dict(name="Basement",top=3200,color="#6b5b95")]
