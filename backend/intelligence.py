"""Engineering intelligence services. Synthetic/demo logic; replace ML models with validated models and authorized data."""
import math, re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from data import WELLS, EVENTS, DOCUMENTS, ACTIVE, distance, FORMATIONS
from services.live import get_scenario, telemetry

TYPE_ALIASES={"mud loss":"MUD_LOSS","loss":"MUD_LOSS","kick":"KICK","stuck":"STUCK_PIPE",
              "overpressure":"OVERPRESSURE","torque":"TORQUE_SPIKE","cement":"CEMENTING",
              "fishing":"FISHING","npt":"NPT","pressure":"OVERPRESSURE"}

class Intelligence:
    def __init__(self):
        self.vectorizer=TfidfVectorizer(stop_words="english")
        self.matrix=self.vectorizer.fit_transform([d["text"] for d in DOCUMENTS])

    def similar(self,wid):
        a=WELLS[wid]; rows=[]
        for b in WELLS.values():
            if b["well_id"]==wid: continue
            d=distance(wid,b["well_id"])
            def sim(k,s): return max(0,1-abs(a[k]-b[k])/s)
            param=sum(sim(k,s) for k,s in [("mud_weight",.2),("rop",20),("wob",10),("rpm",60)])/4
            same=a["formation"]==b["formation"]
            depth_sim=sim("total_depth",1500)
            _z=self.risk(wid,telemetry()["depth"])["zones"]
            active_types={e["event_type"] for e in EVENTS if e["well_id"]==wid}|({_z[0]["event_type"]} if _z else set())
            other_types={e["event_type"] for e in EVENTS if e["well_id"]==b["well_id"]}
            shared=active_types & other_types
            geo=math.exp(-d/10)
            score=.25*geo+.20*int(same)+.15*depth_sim+.15*param+.25*(1 if shared else .3 if other_types else 0)
            reasons=[]
            if same: reasons.append("same formation")
            if depth_sim>.85: reasons.append("similar total depth")
            if param>.82: reasons.append("similar drilling parameters")
            if shared: reasons.append("shared historical risk: "+", ".join(x.replace("_"," ").title() for x in shared))
            reasons.append(f"{d:.1f} km away")
            rows.append({"well_id":b["well_id"],"similarity":round(score*100),
                         "distance_km":round(d,1),"reasons":reasons,
                         "shared_risks":sorted(shared)})
        return sorted(rows,key=lambda x:-x["similarity"])

    def risk(self,wid=ACTIVE,depth=2810,ahead=500):
        # Combine historical evidence, formation, live demo scenario and depth proximity.
        zones=[]
        scenario=get_scenario()
        scenario_type={"MUD_LOSS":"MUD_LOSS","STUCK_PIPE":"STUCK_PIPE","OVERPRESSURE":"OVERPRESSURE","TORQUE_SPIKE":"TORQUE_SPIKE"}.get(scenario)

        end=depth+ahead
        for typ in sorted({e["event_type"] for e in EVENTS}):
            es=[e for e in EVENTS if e["well_id"]!=wid and depth-30<=e["depth"]<=end and distance(wid,e["well_id"])<=20 and e["event_type"]==typ]
            if not es: continue
            near=sum(max(0,1-distance(wid,e["well_id"])/20) for e in es)
            depthmatch=sum(max(0,1-abs(e["depth"]-depth)/450) for e in es)/len(es)
            same=sum(e["formation"]==WELLS[wid]["formation"] for e in es)/len(es)
            high=sum(e["severity"]=="HIGH" for e in es)
            score=28+12*min(3,len({e["well_id"] for e in es}))+14*depthmatch+14*same+6*min(3,high)+10*near/len(es)
            score=max(5,min(98,round(score)))
            lo=min(e["depth"] for e in es); hi=max(e["depth"] for e in es)+20
            nearest=min(es,key=lambda e:distance(wid,e["well_id"]))
            zones.append({"event_type":typ,"lo":lo,"hi":hi,"score":score,
                          "level":"HIGH" if score>=75 else "MEDIUM" if score>=50 else "LOW",
                          "wells":sorted({e["well_id"] for e in es}),
                          "n_wells":len({e["well_id"] for e in es}),
                          "same_formation":round(same*100),"nearest_well":nearest["well_id"],
                          "event_ids":[e["event_id"] for e in es],"formation":WELLS[wid]["formation"],
                          "evidence_count":len(es)})
        if scenario_type:
            matches=[e for e in EVENTS if e["event_type"]==scenario_type and e["well_id"]!=wid]
            if matches:
                same=sum(e["formation"]==WELLS[wid]["formation"] for e in matches)/len(matches)
                nearest=min(matches,key=lambda e:distance(wid,e["well_id"]))
                score=max(72, min(96, round(76 + 12*same + min(8,len({e["well_id"] for e in matches}))*0.8)))
                zones.append({"event_type":scenario_type,"lo":max(depth,nearest["depth"]-40),"hi":nearest["depth"]+40,"score":score,
                              "level":"CRITICAL" if score>=90 else "HIGH","wells":sorted({e["well_id"] for e in matches}),
                              "n_wells":len({e["well_id"] for e in matches}),"same_formation":round(same*100),
                              "nearest_well":nearest["well_id"],"event_ids":[e["event_id"] for e in matches],
                              "formation":WELLS[wid]["formation"],"evidence_count":len(matches),"demo_scenario":scenario})
        zones.sort(key=lambda z:-z["score"])
        top=zones[0] if zones else {"score":0,"level":"LOW","event_type":"NONE"}
        return {"well_id":wid,"depth":depth,"lookahead_m":ahead,"score":top["score"],"zones":zones,
                "confidence":min(96,58+5*top.get("evidence_count",0)+10*(top.get("same_formation",0)/100))}

    def explain(self,wid,depth):
        r=self.risk(wid,depth)
        if not r["zones"]:
            return {"headline":"No strong historical pattern detected","factors":[],"confidence":r["confidence"]}
        z=r["zones"][0]
        factors=[
            {"factor":"Historical analog wells","value":f"{z['n_wells']} wells","weight":"high"},
            {"factor":"Formation match","value":f"{z['same_formation']}%","weight":"high"},
            {"factor":"Depth proximity","value":f"{z['lo']}–{z['hi']} m","weight":"high"},
            {"factor":"Nearest analog","value":f"{z['nearest_well']}","weight":"medium"},
            {"factor":"Evidence records","value":f"{z['evidence_count']} events","weight":"medium"},
        ]
        return {"headline":f"{z['level']} {z['event_type'].replace('_',' ').title()} pattern",
                "risk_score":z["score"],"confidence":r["confidence"],"factors":factors,
                "why":f"{z['n_wells']} nearby historical well(s) show this event in the next {r['lookahead_m']} m; "
                       f"{z['same_formation']}% share the current formation."}

    def forecast(self,wid,depth,step=100):
        bands=[]; depth=int(depth)
        for start in range(depth,depth+501,step):
            rr=self.risk(wid,start,step+80)
            z=rr["zones"][0] if rr["zones"] else None
            bands.append({"from":start,"to":min(start+step,depth+500),
                          "score":rr["score"],"level":rr["zones"][0]["level"] if z else "LOW",
                          "risk_type":z["event_type"] if z else "NONE"})
        return bands

    def search(self,q,k=8):
        ql=q.lower()
        vec=cosine_similarity(self.vectorizer.transform([q]),self.matrix)[0]
        m=re.search(r"(\d{3,4})\s*m",ql)
        typ=next((v for key,v in TYPE_ALIASES.items() if key in ql),None)
        out=[]
        for d,c in zip(DOCUMENTS,vec):
            if typ:
                e=next((x for x in EVENTS if x["event_id"]==d["document_id"].replace("DOC","EV")),None)
                if not e or e["event_type"]!=typ: continue
            s=float(c)
            if m: s+=.8*max(0,1-abs(d["depth"]-int(m.group(1)))/150)
            if s>.12: out.append({**d,"score":round(s,3)})
        return sorted(out,key=lambda x:-x["score"])[:k]

    def copilot(self,q,depth=2810,wid=ACTIVE):
        """Evidence-grounded drilling copilot. Never invents records; every answer is based on retrieved demo evidence."""
        q=(q or '').strip()
        if not q:
            return {"answer":"Ask a question about the current well, risk, formation, offset wells or historical evidence.","sources":[],"confidence":0,"suggestions":["Why is the current risk high?","Which well is most similar?","What happened near this depth?","What should I review next?"]}

        results=self.search(q,8)
        if not results:
            results=self.search(f"{q} {WELLS[wid]['formation']} {round(depth)} m",8)
        if not results:
            # Fall back to the current risk explanation so alert questions still produce a useful grounded response.
            risk=self.risk(wid,depth)
            z=risk['zones'][0] if risk.get('zones') else None
            if z:
                results=self.search(z['event_type'].replace('_',' ') + ' ' + WELLS[wid]['formation'],8)

        if not results:
            return {
                "answer":"No matching evidence exists in the current demonstration knowledge base. Try asking about mud loss, stuck pipe, kick, overpressure, torque spike, a formation, a well ID, or a depth.",
                "sources":[],"confidence":30,
                "suggestions":["Why is the current risk high?","Which well is most similar?","What happened near this depth?","What incidents occurred in this formation?"]
            }

        best=results[:5]
        event_by_doc={e['event_id']:e for e in EVENTS}
        records=[]
        for d in best:
            ev=event_by_doc.get(d['document_id'].replace('DOC','EV'))
            if ev: records.append(ev)
        common=max((e['event_type'] for e in records),key=lambda t:sum(e['event_type']==t for e in records)) if records else 'HISTORICAL_EVENT'
        rel=[d for d in best if d['document_id'].replace('DOC','EV') in {e['event_id'] for e in records if e['event_type']==common}]

        ql=q.lower()
        if any(k in ql for k in ['why','risk','alert','pattern','concern']):
            answer=(f"The retrieved evidence indicates a {common.replace('_',' ').title()} pattern. "
                    f"I found {len(rel) or len(best)} relevant historical record(s) around the current engineering context. "
                    f"The strongest examples are " + ", ".join(f"{d['well_id']} at {d['depth']} m" for d in (rel or best)[:4]) + ".")
        elif any(k in ql for k in ['action','mitigat','handle','what did','response']):
            actions=[]
            for d in (rel or best)[:4]:
                ev=event_by_doc.get(d['document_id'].replace('DOC','EV'))
                if ev: actions.append(f"{d['well_id']} at {d['depth']} m — {ev['action_taken']}")
            answer=f"Historical response patterns for {common.replace('_',' ').title()}: " + "; ".join(actions) + "."
        elif any(k in ql for k in ['similar','analog','compare']):
            analogs=self.similar(wid)[:4]
            answer="The strongest technical analogs are " + ", ".join(f"{a['well_id']} ({a['similarity']}% similarity, {a['distance_km']} km)" for a in analogs) + "."
        else:
            answer=f"I retrieved {len(best)} evidence record(s). The dominant historical pattern is {common.replace('_',' ').title()}, with examples at " + ", ".join(f"{d['well_id']} ({d['depth']} m)" for d in (rel or best)[:4]) + "."

        suggestions={
            'MUD_LOSS':["What action was taken in these mud-loss cases?","Which formation did these losses occur in?","Which well is the closest analog?","What should I review before entering this zone?"],
            'STUCK_PIPE':["What indicators preceded the stuck-pipe event?","What mitigation was used?","Which well had the closest pattern?","Show the incident timeline"],
            'KICK':["What pressure evidence supports this pattern?","How was the historical kick controlled?","Which well is the closest analog?","Show the evidence records"],
            'OVERPRESSURE':["What historical pressure evidence exists?","How was mud weight adjusted?","Which formations show this pattern?","Show the next 500 m risk"],
            'TORQUE_SPIKE':["What drilling parameters changed?","What action normalized torque?","Which analog well is closest?","Show the incident replay"]
        }.get(common,["Explain the strongest evidence","Which well is most similar?","What happened near this depth?","What should I review next?"])

        return {
            "answer":answer,
            "confidence":min(95,55+8*len(best)),
            "sources":[{"event_id":d["document_id"].replace("DOC","EV"),"document_id":d["document_id"],"title":d["title"],"well_id":d["well_id"],"depth":d["depth"],"date":d["date"],"type":d["type"]} for d in best],
            "suggestions":suggestions,
            "context":{"well_id":wid,"depth":depth,"formation":WELLS[wid]['formation']}
        }

    def graph(self,wid=ACTIVE):
        nodes=[]; edges=[]
        def node(i,label,kind): nodes.append({"id":i,"label":label,"kind":kind})
        node(wid,wid,"well")
        for e in EVENTS:
            if e["well_id"]==wid or distance(wid,e["well_id"])<=8:
                wn="well:"+e["well_id"]; fn="formation:"+e["formation"]; en="event:"+e["event_type"]
                if not any(n["id"]==wn for n in nodes): node(wn,e["well_id"],"well")
                if not any(n["id"]==fn for n in nodes): node(fn,e["formation"],"formation")
                if not any(n["id"]==en for n in nodes): node(en,e["event_type"].replace("_"," ").title(),"risk")
                edges += [{"source":wn,"target":fn,"label":"encountered"},
                          {"source":wn,"target":en,"label":"experienced"}]
        # de-duplicate
        seen=set(); ee=[]
        for x in edges:
            key=(x["source"],x["target"],x["label"])
            if key not in seen: seen.add(key); ee.append(x)
        return {"nodes":nodes,"edges":ee}

INTEL=Intelligence()
