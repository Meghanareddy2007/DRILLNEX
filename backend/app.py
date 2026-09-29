"""DRILLNEX SIH 2026 - production-style demo API."""
import os, re, time, secrets
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory
from itsdangerous import URLSafeTimedSerializer
from data import LAYERS, WELLS, EVENTS, DOCUMENTS, ACTIVE, FORMATIONS, distance, public_well, event_xyz
from intelligence import INTEL
from services.live import telemetry, set_scenario, get_scenario, set_clock
from services.documents import save_upload

BASE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(BASE)
UPLOAD_DIR=os.path.join(ROOT,"data","documents")
app=Flask(__name__,static_folder=os.path.join(ROOT,"frontend"),static_url_path="")
app.config["MAX_CONTENT_LENGTH"]=15*1024*1024
SER=URLSafeTimedSerializer(os.getenv("SECRET_KEY") or secrets.token_hex(32),salt="drillnex")

USERS={
    "field@drillnex.demo":{"password":os.getenv("FIELD_DEMO_PASSWORD","DrillNex@2026"),"role":"FIELD_ENGINEER","name":"Arjun Rao"},
    "office@drillnex.demo":{"password":os.getenv("OFFICE_DEMO_PASSWORD","DrillNex@2026"),"role":"OFFICE_ENGINEER","name":"Meera Iyer"},
}

@app.after_request
def headers(r):
    origin=request.headers.get("Origin")
    allowed=os.getenv("FRONTEND_ORIGIN","*")
    if allowed=="*" or origin==allowed:
        r.headers["Access-Control-Allow-Origin"]=origin if origin else allowed
        r.headers["Vary"]="Origin"
    r.headers["Access-Control-Allow-Headers"]="Content-Type, Authorization, X-Drillnex-Well"
    r.headers["Access-Control-Allow-Methods"]="GET, POST, OPTIONS"
    r.headers["X-Content-Type-Options"]="nosniff"
    r.headers["X-Frame-Options"]="SAMEORIGIN"
    r.headers["Cache-Control"]="no-store" if request.path.startswith("/api/") or request.path in ("/","/health") else "no-cache"
    return r

def current_user():
    token=request.headers.get("Authorization","").replace("Bearer ","").strip()
    if not token: return None
    try: return SER.loads(token,max_age=12*3600)
    except Exception: return None

def selected_well():
    wid=request.headers.get("X-Drillnex-Well","").strip()
    return wid if wid in WELLS else ACTIVE

def auth_required(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        if not current_user(): return jsonify(error="Authentication required"),401
        return fn(*args,**kwargs)
    return wrapped

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            u=current_user()
            if not u:return jsonify(error="Authentication required"),401
            if u["role"] not in roles:return jsonify(error="This role cannot access the requested resource"),403
            return fn(*args,**kwargs)
        return wrapped
    return deco

@app.before_request
def _guard():
    if request.path.startswith("/api/") and request.path not in ("/api/auth/login","/api/health") and not current_user():
        return jsonify(error="Authentication required"),401

@app.get("/api/health")
def api_health(): return health()

@app.get("/")
def index(): return send_from_directory(app.static_folder,"index.html")
@app.get("/health")
def health(): return jsonify(status="ok",service="drillnex",version="2.0.0",timestamp=time.time(),telemetry="online",data="synthetic-demo")

@app.post("/api/auth/login")
def login():
    body=request.get_json(silent=True) or {}; email=str(body.get("email","")).lower().strip(); password=str(body.get("password",""))
    u=USERS.get(email)
    if not u or not secrets.compare_digest(password,u["password"]): return jsonify(error="Invalid demo credentials"),401
    token=SER.dumps({"email":email,"role":u["role"],"name":u["name"]})
    return jsonify(token=token,user={"email":email,"role":u["role"],"name":u["name"]})

@app.post("/api/auth/logout")
def logout():
    return jsonify(ok=True)

@app.get("/api/auth/me")
@auth_required
def me(): return jsonify(user=current_user())

@app.get("/api/summary")
@auth_required
def summary():
    wid=selected_well(); live=telemetry(); rr=INTEL.risk(wid,live["depth"])
    nearby=sum(distance(wid,w["well_id"])<=5 and w["well_id"]!=wid for w in WELLS.values())
    return jsonify(active_well=wid,live=live,risk=rr,nearby_count=nearby,events=len(EVENTS),documents=len(DOCUMENTS),
                   formation=next((f for f in FORMATIONS if f["top"]<=live["depth"]<f["bottom"]),None),scenario=get_scenario())

@app.get("/api/live")
@auth_required
def live():
    wid=selected_well(); l=telemetry(); return jsonify({**l,"well_id":wid,"risk":INTEL.risk(wid,l["depth"]),"explain":INTEL.explain(wid,l["depth"]),"scenario":get_scenario()})

@app.get("/api/wells")
@auth_required
def wells(): return jsonify([public_well(w) for w in WELLS.values()])
@app.get("/api/wells/<wid>")
@auth_required
def well(wid):
    if wid not in WELLS:return jsonify(error="Unknown well"),404
    return jsonify(public_well(WELLS[wid]))
@app.get("/api/wells/<wid>/events")
@auth_required
def well_events(wid): return jsonify([e for e in EVENTS if e["well_id"]==wid])
@app.get("/api/wells/nearby")
@auth_required
def nearby():
    radius=float(request.args.get("radius",10)); out=[]; center=selected_well()
    for w in WELLS.values():
        d=distance(center,w["well_id"])
        if d<=radius:
            es=[e for e in EVENTS if e["well_id"]==w["well_id"]]
            out.append({**public_well(w),"distance_km":round(d,1),"event_count":len(es),"risk_types":sorted({e["event_type"] for e in es}),"active":w["well_id"]==center})
    return jsonify(sorted(out,key=lambda x:x["distance_km"]))

@app.get("/api/similar/<wid>")
@auth_required
def similar(wid):
    if wid not in WELLS:return jsonify(error="Unknown well"),404
    return jsonify(INTEL.similar(wid)[:10])
@app.get("/api/risk/<wid>")
@auth_required
def risk(wid):
    if wid not in WELLS:return jsonify(error="Unknown well"),404
    depth=telemetry()["depth"] if wid==ACTIVE else WELLS[wid]["total_depth"]
    return jsonify(INTEL.risk(wid,depth))
@app.get("/api/risk/<wid>/explain")
@auth_required
def explain(wid):
    depth=telemetry()["depth"] if wid==ACTIVE else WELLS[wid]["total_depth"]
    return jsonify(INTEL.explain(wid,depth))
@app.get("/api/risk/<wid>/forecast")
@auth_required
def forecast(wid):
    depth=telemetry()["depth"] if wid==ACTIVE else WELLS[wid]["total_depth"]
    return jsonify(INTEL.forecast(wid,depth))
@app.get("/api/events")
@auth_required
def events(): return jsonify(EVENTS)
@app.get("/api/timeline/<wid>")
@auth_required
def timeline(wid): return jsonify(sorted([e for e in EVENTS if e["well_id"]==wid],key=lambda e:e["depth"]))
@app.get("/api/evidence/<eid>")
@auth_required
def evidence(eid):
    e=next((x for x in EVENTS if x["event_id"]==eid),None)
    if not e:return jsonify(error="Evidence not found"),404
    return jsonify({**e,"document_type":{"DDR":"Daily Drilling Report","WCR":"Well Completion Report","MLR":"Mud Logging Report"}.get(e["source_document"].split("_")[-1].replace(".pdf",""),"Historical Report"),"verification":"Synthetic demonstration evidence; replace with authorized OIL document references."})
@app.get("/api/graph")
@auth_required
def graph(): return jsonify(INTEL.graph(selected_well()))
@app.get("/api/3d")
@auth_required
def d3():
    center=selected_well(); ws=[w for w in WELLS.values() if distance(center,w["well_id"])<=10]
    ids={w["well_id"] for w in ws}
    return jsonify(wells=[{**public_well(w),"trajectory":w["trajectory"],"active":w["well_id"]==center} for w in ws],events=[event_xyz(e) for e in EVENTS if e["well_id"] in ids],layers=FORMATIONS)

@app.get("/api/formations")
@auth_required
def formations():
    out=[]
    for f in FORMATIONS:
        es=[e for e in EVENTS if e["formation"]==f["name"]]
        out.append({**f,"event_count":len(es),"wells":sorted({e["well_id"] for e in es}),"event_types":sorted({e["event_type"] for e in es})})
    return jsonify(out)

@app.get("/api/alerts")
@auth_required
def alerts():
    wid=selected_well(); l=telemetry(); r=INTEL.risk(wid,l["depth"]); alerts=[]
    for z in r["zones"][:4]:
        alerts.append({"id":"ALT-"+z["event_type"],"severity":"CRITICAL" if z["score"]>=85 else "HIGH" if z["score"]>=70 else "MEDIUM","title":f"Potential {z['event_type'].replace('_',' ').title()} pattern","score":z["score"],"depth":round(l["depth"],1),"evidence":z["evidence_count"],"nearest":z["nearest_well"]})
    alerts.append({"id":"ALT-DATA","severity":"INFO","title":"Synthetic telemetry stream healthy","score":100,"depth":round(l["depth"],1),"evidence":0,"nearest":"â€”"})
    return jsonify(alerts)

@app.get("/api/data-quality")
@auth_required
def data_quality():
    return jsonify(overall=96,signals=[{"name":"Depth","value":100},{"name":"ROP","value":98},{"name":"Torque","value":97},{"name":"Pressure","value":99},{"name":"Flow rate","value":95},{"name":"Mud weight","value":96}],document_extraction=92,last_update=telemetry()["timestamp"],note="Synthetic demonstration stream; production should report actual sensor freshness and missingness.")

@app.post("/api/search")
@auth_required
def search():
    q=(request.get_json(silent=True) or {}).get("query",""); return jsonify(INTEL.search(q))
@app.post("/api/copilot")
@auth_required
def copilot():
    q=str((request.get_json(silent=True) or {}).get("query","")).strip()
    try:
        result=INTEL.copilot(q,telemetry()["depth"],selected_well())
        return jsonify(result)
    except Exception as exc:
        # Keep the UI contract JSON even if an optional intelligence dependency fails.
        return jsonify({"error":"Copilot evidence retrieval failed","detail":str(exc),"suggestions":["Why is the current risk high?","Which well is most similar?","What happened near this depth?"]}),500
# What-if simulator: transparent, simplified demonstration model (reference: MW 1.20 SG, ROP 25 m/hr, WOB 12 t, RPM 110)
WHATIF_REF={"mud_weight":1.20,"rop":25.0,"wob":12.0,"rpm":110.0}
WHATIF_WINDOW={"lo":1.14,"hi":1.28}
WHATIF_W={"MUD_LOSS":(1.0,.6,.5,.3),"KICK":(1.4,.5,.2,.2),"OVERPRESSURE":(1.2,.6,.3,.2),"STUCK_PIPE":(.6,1.0,1.5,1.2),"TORQUE_SPIKE":(.3,.8,1.6,1.6),"CEMENTING":(.7,.3,.3,.3),"FISHING":(.4,.5,1.2,1.0)}
def _wi_terms(mw,rop,wob,rpm):
    hi=WHATIF_WINDOW["hi"]
    return {"mud_weight":-(min(mw,hi)-1.20)*280+max(0,mw-hi)*400,"rop":(rop-25)*.3,"wob":(wob-12)*.5,"rpm":(rpm-110)*.05}
def _wi_score(base,mw,rop,wob,rpm): return max(5,min(99,round(base+sum(_wi_terms(mw,rop,wob,rpm).values()))))
@app.post("/api/what-if")
@auth_required
def whatif():
    p=request.get_json(silent=True) or {}
    def num(k,d,lo,hi):
        try: v=float(p.get(k,d))
        except (TypeError,ValueError): v=d
        return max(lo,min(hi,v))
    mw=num("mud_weight",1.20,.8,2.2); rop=num("rop",25,0,300); wob=num("wob",12,0,60); rpm=num("rpm",110,0,400)
    r=INTEL.risk(selected_well(),telemetry()["depth"]); base=r["score"]
    simulated=_wi_score(base,mw,rop,wob,rpm); delta=simulated-base
    terms=_wi_terms(mw,rop,wob,rpm); labels={"mud_weight":"Mud weight","rop":"ROP","wob":"WOB","rpm":"RPM"}
    contributions=[{"key":k,"label":labels[k],"points":round(v,1)} for k,v in terms.items()]
    win=WHATIF_WINDOW; status="BELOW WINDOW" if mw<win["lo"] else "ABOVE FRACTURE LIMIT" if mw>win["hi"] else "IN WINDOW"
    patterns=[]
    for z in r.get("zones",[])[:6]:
        w=WHATIF_W.get(z["event_type"],(1,1,1,1)); d=sum(w[i]*terms[k] for i,k in enumerate(["mud_weight","rop","wob","rpm"]))
        patterns.append({"event_type":z["event_type"],"base":z["score"],"simulated":max(5,min(99,round(z["score"]+d)))})
    def sweep(key,lo,hi,step):
        pts=[];v=lo
        while v<=hi+1e-9:
            a=dict(mud_weight=mw,rop=rop,wob=wob,rpm=rpm); a[key]=v
            pts.append({"x":round(v,3),"y":_wi_score(base,a["mud_weight"],a["rop"],a["wob"],a["rpm"])}); v+=step
        return pts
    sens={"mud_weight":sweep("mud_weight",1.00,1.45,.025),"rop":sweep("rop",5,60,2.5),"wob":sweep("wob",4,24,1),"rpm":sweep("rpm",40,180,5)}
    hours_per_100=round(100/rop,1) if rop>0 else None
    exp_b=round(base/100*12,1); exp_s=round(simulated/100*12,1)
    recs=[]
    worst=max(contributions,key=lambda c:c["points"]); best=min(contributions,key=lambda c:c["points"])
    if mw>win["hi"]: recs.append({"level":"HIGH","text":f"Mud weight {mw:.2f} SG exceeds the assumed {win['hi']:.2f} SG fracture limit; losses become more likely. Reduce toward the window."})
    if mw<win["lo"]: recs.append({"level":"HIGH","text":f"Mud weight {mw:.2f} SG is below the assumed {win['lo']:.2f} SG pore-pressure floor; influx/kick exposure increases."})
    if worst["points"]>=3: recs.append({"level":"MEDIUM","text":f"{worst['label']} is the largest risk driver (+{worst['points']:.1f} pts). Consider moving it back toward the reference value."})
    if best["points"]<=-3: recs.append({"level":"LOW","text":f"{best['label']} is the biggest risk reducer ({best['points']:.1f} pts) in this scenario."})
    if abs(delta)<3 and not recs: recs.append({"level":"LOW","text":"Scenario stays close to the reference envelope; no material change in modelled risk."})
    if not recs: recs.append({"level":"LOW","text":"Review the sensitivity curves to find the steepest lever before changing parameters."})
    return jsonify(base=base,simulated=simulated,delta=delta,impact="Low" if abs(delta)<10 else "Moderate" if abs(delta)<22 else "High",
        warning="Demonstration model only; validate against approved engineering models.",fracture_warning=mw>win["hi"],
        inputs={"mud_weight":mw,"rop":rop,"wob":wob,"rpm":rpm},reference=WHATIF_REF,window={**win,"status":status},contributions=contributions,
        patterns=patterns,sensitivity=sens,hours_per_100m=hours_per_100,npt_exposure={"base_hours":exp_b,"simulated_hours":exp_s,"base_inr":round(exp_b*2500),"simulated_inr":round(exp_s*2500),"rate_inr":2500},
        recommendations=recs,well_id=selected_well(),depth=r.get("depth"))

@app.post("/api/demo/scenario")
@role_required("FIELD_ENGINEER","OFFICE_ENGINEER")
def scenario():
    name=(request.get_json(silent=True) or {}).get("scenario","NORMAL")
    allowed={"NORMAL","MUD_LOSS","STUCK_PIPE","OVERPRESSURE","TORQUE_SPIKE"}
    if name not in allowed:return jsonify(error="Unknown scenario"),400
    set_scenario(name); return jsonify(scenario=name,ok=True)

@app.post("/api/demo/clock")
@role_required("FIELD_ENGINEER","OFFICE_ENGINEER")
def clock():
    b=request.get_json(silent=True) or {}
    return jsonify(ok=True,**set_clock(paused=b.get("paused"),reset=bool(b.get("reset"))))

@app.post("/api/documents/upload")
@role_required("FIELD_ENGINEER","OFFICE_ENGINEER")
def upload():
    if "file" not in request.files:return jsonify(error="Attach a PDF or TXT file as 'file'"),400
    try:return jsonify(save_upload(request.files["file"],UPLOAD_DIR))
    except Exception as e:return jsonify(error=str(e)),400
@app.get("/api/documents")
@auth_required
def documents(): return jsonify(DOCUMENTS)

@app.get("/api/performance")
@auth_required
def performance():
    wid=selected_well(); l=telemetry(); w=WELLS[wid]
    def metric(label,unit,actual,planned,tol):
        dev=(actual-planned)/planned*100 if planned else 0
        status="ON TRACK" if abs(dev)<=tol else "WATCH" if abs(dev)<=tol*1.8 else "REVIEW"
        return {"label":label,"unit":unit,"actual":round(actual,3),"planned":round(planned,3),"deviation_pct":round(dev,1),"tolerance_pct":tol,"status":status}
    ms=[metric("ROP","m/hr",l["rop"],w["rop"],12),metric("WOB","t",l["wob"],w["wob"],12),metric("RPM","rpm",l["rpm"],w["rpm"],12),metric("Mud weight","SG",l["mud_weight"],w["mud_weight"],3),metric("Pressure","bar",l["pressure"],w["pressure"],8)]
    npt=sum(float(e.get("npt_hours",0)) for e in EVENTS if e["event_type"]=="NPT")
    adherence=max(0,round(100-sum(min(35,abs(m["deviation_pct"])) for m in ms)/len(ms),1)); progress=round(min(100,l["depth"]/w["total_depth"]*100),1)
    drivers=[]
    for m in ms:
        if m["status"]!="ON TRACK": drivers.append({"label":m["label"],"detail":f"{m['actual']} {m['unit']} vs {m['planned']} {m['unit']} baseline ({m['deviation_pct']:+.1f}%)."})
    if not drivers: drivers=[{"label":"Stable baseline","detail":"Current parameters remain within the demonstration tolerance bands."}]
    state="ON TRACK" if adherence>=92 else "WATCH" if adherence>=80 else "REVIEW"
    return jsonify(well_id=wid,metrics=ms,adherence=adherence,depth_progress=progress,npt_hours=round(npt,1),state=state,note="Baseline comparison only",drivers=drivers,review={"what_changed":drivers[0]["detail"],"where_to_look":"Review live telemetry, formation context and historical analog evidence."},disclaimer="Synthetic planned-vs-actual comparison for SIH demonstration. Production use requires an approved well plan and validated performance model.")

@app.get("/api/npt-cost")
@auth_required
def npt_cost():
    # Transparent demonstration assumption; production should use approved cost accounting.
    hourly=2500
    rows=[]
    for e in EVENTS:
        hours=0
        if e["event_type"]=="NPT": hours=12.0
        else:
            m=re.search(r"(\d+(?:\.\d+)?)\s*h",e.get("outcome","").lower())
            if m: hours=float(m.group(1))
        if hours>0: rows.append({"event_id":e["event_id"],"well_id":e["well_id"],"depth":e["depth"],"event_type":e["event_type"],"date":e["date"],"hours":round(hours,1),"impact_inr":round(hours*hourly)})
    total=sum(x["hours"] for x in rows)
    return jsonify(events=rows,total_hours=round(total,1),total_impact_inr=round(total*hourly),event_count=len(rows),average_hours=round(total/len(rows),1) if rows else 0,hourly_rate_inr=hourly,method="Event outcome hours where explicitly recorded; NPT records use the recorded 12 h demonstration value.",disclaimer="Cost values are synthetic demonstration estimates and do not represent actual Oil India economics.")

@app.get("/api/handover")
@auth_required
def handover():
    wid=selected_well(); l=telemetry(); r=INTEL.risk(wid,l["depth"]); w=WELLS[wid]
    nearby=sorted([e for e in EVENTS if e["well_id"]!=wid and abs(e["depth"]-l["depth"])<=120 and distance(wid,e["well_id"])<=12],key=lambda e:abs(e["depth"]-l["depth"]))[:4]
    open_items=[]
    if r.get("zones"):
        z=r["zones"][0]; open_items.append({"title":f"Review {z['event_type'].replace('_',' ').title()} zone","detail":f"Historical zone {z['lo']}â€“{z['hi']} m; nearest analog {z['nearest_well']}."})
    open_items += [{"title":"Monitor live telemetry","detail":"Continue reviewing ROP, torque, pressure and flow against the active baseline."},{"title":"Check supporting evidence","detail":"Use Copilot or evidence search to review the closest historical records."}]
    return jsonify(well_id=wid,formation=w["formation"],depth=l["depth"],telemetry=l,risk={"score":r["score"],"level":r["zones"][0]["level"] if r.get("zones") else "LOW"},events=nearby,open_items=open_items[:4],evidence=[{"event_id":e["event_id"],"well_id":e["well_id"],"depth":e["depth"],"event_type":e["event_type"]} for e in nearby],generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),disclaimer="Synthetic shift-handover draft. Engineer review is required before operational use.")

@app.get("/api/reports/well-summary")
@auth_required
def report_summary():
    wid=selected_well(); l=telemetry(); r=INTEL.risk(wid,l["depth"]); return jsonify(title="DRILLNEX Well Intelligence Summary",well=wid,depth=l["depth"],formation=WELLS[wid]["formation"],risk=r,generated_at=time.time(),disclaimer="Synthetic demonstration report.")

import insights
class _St:
    def __getitem__(self,k): return telemetry()["depth"]
def _risk():
    d=telemetry()["depth"]; r=INTEL.risk(ACTIVE,d); zs=[]
    for z in r["zones"]:
        n=len(z["event_ids"]); zs.append({**z,"distance":z["lo"]-d,"same_formation":round(z["same_formation"]*n/100),"level":"HIGH" if z["level"]=="CRITICAL" else z["level"]})
    return {**r,"zones":zs}
insights.register(app,dict(W=WELLS,EV=EVENTS,BYID={e["event_id"]:e for e in EVENTS},STATE=_St(),ACTIVE=ACTIVE,LAYERS=LAYERS,risk=_risk,similar=INTEL.similar,dist=distance,nice=lambda t:t.replace("_"," ").title()))

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","8080")),debug=False)


