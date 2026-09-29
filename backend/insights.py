"""eRTMAC-NWIS "Insights" add-on. SYNTHETIC DATA ONLY - decision support, never an operational drilling recommendation.

Purely additive: it reads the objects already built in app.py (wells, events, risk engine, similarity) and exposes
new read-only endpoints under /api/insights/*. Nothing in the original API is modified.
"""
import math
from flask import jsonify, request

SEV_W = {"HIGH": .55, "MEDIUM": .40, "LOW": .20}
SAFETY = ("Decision support only. Historical actions are records from offset wells, not drilling recommendations. "
          "Synthetic data.")
# Information-gathering prompts only (what to READ / COMPARE) - never parameter changes.
REVIEW = {
    "MUD_LOSS": ["Compare the planned mud-weight window with loss depths and outcomes recorded in offset wells",
                 "Read the loss-control treatments logged in offsets and their recorded results",
                 "Check pit-level and flow-out trends logged in offset reports for this interval"],
    "STUCK_PIPE": ["Review offset differential-sticking and pack-off records for this interval",
                   "Compare hole-cleaning and overbalance history recorded in offsets"],
    "KICK": ["Review offset pore-pressure trends and how the influx was recorded",
             "Confirm well-control preparedness with the responsible team under site procedures"],
    "CEMENTING": ["Review offset cement-bond and slurry-loss results",
                  "Compare cementing design notes with the recorded loss history"],
    "OVERPRESSURE": ["Review offset pressure-compartment records and mud-log signatures",
                     "Compare pore-pressure interpretations across offsets"],
    "TORQUE_SPIKE": ["Review offset torque and bit-balling records for this interval"],
    "FISHING": ["Review offset string-failure and recovery records for this interval"],
    "NPT": ["Review offset non-productive-time causes recorded near this depth"],
}
DOC = {"DDR": "Daily Drilling Report", "WCR": "Well Completion Report", "MLR": "Mud Logging Report"}


def register(app, C):
    W, EV, BYID, STATE, ACTIVE = C["W"], C["EV"], C["BYID"], C["STATE"], C["ACTIVE"]
    risk, similar, dist, nice = C["risk"], C["similar"], C["dist"], C["nice"]

    def rop():
        return W[ACTIVE]["rop"]

    def simmap():
        return {s["well_id"]: s for s in similar(ACTIVE)}

    def eta(metres):  # plain distance / ROP arithmetic, constant-ROP assumption
        return round(max(0, metres) / rop(), 1)

    def lvl(v):
        return "HIGH" if v >= 75 else "MEDIUM" if v >= 50 else "LOW"

    def slim(e, sm=None):
        out = dict(event_id=e["event_id"], well_id=e["well_id"], depth=e["depth"], date=e["date"],
                   severity=e["severity"], event_type=e["event_type"], cause=e["cause"],
                   action_taken=e["action_taken"], outcome=e["outcome"], source_document=e["source_document"],
                   document_type=DOC[e["source_document"][6:9]], formation=e["formation"])
        if sm and e["well_id"] in sm:
            out["similarity"] = sm[e["well_id"]]["similarity"]
            out["distance_km"] = sm[e["well_id"]]["distance_km"]
        return out

    # ------------------------------------------------------------------ Historical-to-Future Bridge
    @app.get("/api/insights/bridge", endpoint="ix_bridge")
    def bridge():
        R, sm, a = risk(), simmap(), W[ACTIVE]
        d = R["depth"]
        zones = []
        for z in R["zones"][:4]:
            es = [BYID[i] for i in z["event_ids"]]
            past = [{**slim(e, sm), "offset_m": e["depth"] - d} for e in sorted(es, key=lambda e: -sm[e["well_id"]]["similarity"])]
            sims = [sm[w]["similarity"] for w in z["wells"]]
            same_share = 100 * z["same_formation"] / len(es)
            strength = round(.5 * sum(sims) / len(sims) + .3 * same_share + .2 * min(100, 34 * z["n_wells"]))
            ws = [W[w] for w in z["wells"]]

            def rng(k):
                v = [w[k] for w in ws]
                return min(v), max(v)
            matches = [
                dict(label="Formation", now=a["formation"], past="%d of %d offset events in the same formation" % (z["same_formation"], len(es))),
                dict(label="Mud weight", now="%.2f SG" % a["mud_weight"], past="%.2f-%.2f SG in offsets" % rng("mud_weight")),
                dict(label="ROP", now="%d m/hr" % a["rop"], past="%d-%d m/hr in offsets" % rng("rop")),
                dict(label="WOB", now="%d t" % a["wob"], past="%d-%d t in offsets" % rng("wob")),
                dict(label="RPM", now="%d" % a["rpm"], past="%d-%d in offsets" % rng("rpm")),
                dict(label="Distance", now="-", past="%.1f-%.1f km from W-125" % (min(sm[w]["distance_km"] for w in z["wells"]), max(sm[w]["distance_km"] for w in z["wells"]))),
            ]
            zones.append(dict(
                event_type=z["event_type"], level=z["level"], score=z["score"], strength=strength,
                strength_label="Strong" if strength >= 75 else "Moderate" if strength >= 55 else "Limited",
                past=past, present=dict(depth=d, formation=a["formation"], matches=matches),
                future=dict(lo=z["lo"], hi=z["hi"], distance=z["distance"], eta_lo_h=eta(z["distance"]),
                            eta_hi_h=eta(z["hi"] - d), in_zone=z["distance"] <= 0),
                review=REVIEW.get(z["event_type"], ["Review offset well reports"])))
        return jsonify(active=dict(well_id=ACTIVE, depth=d, formation=a["formation"], rop=rop(), mud_weight=a["mud_weight"],
                                   wob=a["wob"], rpm=a["rpm"]), zones=zones, rop=rop(), safety=SAFETY,
                       note="ETA = distance / current ROP, constant-ROP assumption. Informational only.")

    # ------------------------------------------------------------------ Risk Horizon
    @app.get("/api/insights/horizon", endpoint="ix_horizon")
    def horizon():
        ahead = max(100, min(900, int(request.args.get("ahead", 600))))
        step = 25
        d = STATE["depth"]
        evs = [e for e in EV if e["well_id"] != ACTIVE and dist(ACTIVE, e["well_id"]) <= 20]
        af = W[ACTIVE]["formation"]

        def weight(e):
            return SEV_W[e["severity"]] * math.exp(-dist(ACTIVE, e["well_id"]) / 12) * (1 if e["formation"] == af else .6)

        bins = []
        for k in range(0, ahead // step + 1):
            c = d + k * step
            keep, contrib = 1.0, {}
            for e in evs:
                p = weight(e) * math.exp(-(((c - e["depth"]) / 40) ** 2))
                if p < .005:
                    continue
                keep *= (1 - p)
                contrib[e["event_type"]] = contrib.get(e["event_type"], 0) + p
            idx = round(min(99, (1 - keep) * 100))
            bins.append(dict(depth=c, index=idx, level=lvl(idx), dominant=max(contrib, key=contrib.get) if contrib else None,
                             eta_h=eta(c - d)))
        marks = [dict(event_id=e["event_id"], well_id=e["well_id"], event_type=e["event_type"], depth=e["depth"], severity=e["severity"])
                 for e in evs if d <= e["depth"] <= d + ahead]
        wins = []
        for lo, hi in ((0, 100), (100, 300), (300, ahead)):
            if lo >= ahead:
                continue
            bs = [b for b in bins if lo <= b["depth"] - d <= min(hi, ahead)]
            pk = max(bs, key=lambda b: b["index"])
            wins.append(dict(label="%d-%d m ahead" % (lo, min(hi, ahead)), peak=pk["index"], level=pk["level"],
                             peak_depth=pk["depth"], dominant=pk["dominant"], eta_h=pk["eta_h"]))
        return jsonify(depth=d, ahead=ahead, rop=rop(), bins=bins, markers=marks, windows=wins,
                       official_score=risk()["score"], safety=SAFETY,
                       note="Exposure index = smoothed density of severity-weighted offset events (closer wells and same formation count more). "
                            "Prototype metric, separate from the headline Risk Score.")

    # ------------------------------------------------------------------ Institutional Memory Graph
    @app.get("/api/insights/graph", endpoint="ix_graph")
    def graph():
        ftype = request.args.get("type") or None
        sm, d = simmap(), STATE["depth"]
        top = risk()["zones"][0]["event_type"]
        sev = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        cand = [e for e in EV if e["well_id"] != ACTIVE and e["well_id"] in sm and sm[e["well_id"]]["distance_km"] <= 15
                and (not ftype or e["event_type"] == ftype)]
        cand.sort(key=lambda e: (e["event_type"] != top, sev[e["severity"]], abs(e["depth"] - d)))
        cand = cand[:12]
        nodes, edges, seen = [], [], {}

        def node(key, col, label, **kw):
            if key not in seen:
                seen[key] = dict(id=key, col=col, label=label, **kw)
                nodes.append(seen[key])
            return key

        def edge(a, b, **kw):
            if not any(x["source"] == a and x["target"] == b for x in edges):
                edges.append(dict(source=a, target=b, **kw))
        a = node("well:" + ACTIVE, 0, ACTIVE, kind="active", sub="depth %d m" % d)
        for e in cand:
            w = e["well_id"]
            wn = node("well:" + w, 1, w, kind="well", sub="similarity %d%%" % sm[w]["similarity"], well_id=w)
            edge(a, wn, weight=sm[w]["similarity"])
            en = node("ev:" + e["event_id"], 2, "%s - %d m" % (nice(e["event_type"]), e["depth"]), kind="event",
                      sub=e["source_document"], event_id=e["event_id"], pattern=e["event_type"] == top, etype=e["event_type"], severity=e["severity"])
            edge(wn, en)
            cn = node("cause:" + e["cause"], 3, e["cause"], kind="cause")
            an = node("act:" + e["action_taken"], 4, e["action_taken"], kind="action")
            on = node("out:" + e["outcome"], 5, e["outcome"], kind="outcome")
            edge(en, cn); edge(cn, an); edge(an, on)
            for k in (cn, an, on):
                seen[k].setdefault("event_ids", [])
                if e["event_id"] not in seen[k]["event_ids"]:
                    seen[k]["event_ids"].append(e["event_id"])
        docs = {BYID[n["event_id"]]["source_document"] for n in nodes if n["kind"] == "event"}
        return jsonify(nodes=nodes, edges=edges, top_type=top, types=sorted({e["event_type"] for e in EV if e["well_id"] != ACTIVE}),
                       filter=ftype, meta=dict(nodes=len(nodes), edges=len(edges), documents=len(docs),
                                               wells=len([n for n in nodes if n["kind"] == "well"])),
                       events={e["event_id"]: slim(e, sm) for e in cand}, safety=SAFETY)

    # ------------------------------------------------------------------ ranking / Twin / Why
    @app.get("/api/insights/ranking", endpoint="ix_ranking")
    def ranking():
        return jsonify([s for s in similar(ACTIVE)][:10])

    def parts(bid):
        a, b = W[ACTIVE], W[bid]
        top = risk()["zones"][0]["event_type"]
        d = dist(ACTIVE, bid)

        def s(k, sc):
            return max(0, 1 - abs(a[k] - b[k]) / sc)
        pr = [("Mud weight", "mud_weight", .2, "%.2f SG"), ("ROP", "rop", 20, "%d m/hr"), ("WOB", "wob", 10, "%d t"), ("RPM", "rpm", 60, "%d")]
        params = sum(s(k, sc) for _, k, sc, _ in pr) / 4
        types = {e["event_type"] for e in EV if e["well_id"] == bid}
        same, dsim = a["formation"] == b["formation"], s("total_depth", 1500)
        pat = 1 if top in types else (.3 if types else 0)
        comps = [
            dict(key="proximity", title="Geographic proximity", weight=25, value=.25 * math.exp(-d / 10) * 100,
                 finding="%.1f km from W-125 (influence fades with distance)" % d),
            dict(key="formation", title="Same formation", weight=20, value=20 * same,
                 finding="%s vs %s" % (b["formation"], a["formation"])),
            dict(key="depth", title="Similar total depth", weight=15, value=15 * dsim,
                 finding="TD %d m vs %d m" % (b["total_depth"], a["total_depth"])),
            dict(key="params", title="Similar drilling parameters", weight=15, value=15 * params,
                 finding="; ".join("%s %s vs %s" % (n, f % b[k], f % a[k]) for n, k, _, f in pr)),
            dict(key="pattern", title="Same historical risk pattern", weight=25, value=25 * pat,
                 finding=("Recorded %s in this well" % nice(top)) if pat == 1 else ("Has other recorded events, but not %s" % nice(top)) if pat else "No recorded events"),
        ]
        for c in comps:
            c["value"] = round(c["value"], 1)
            c["ratio"] = round(c["value"] / c["weight"], 2)
            c["verdict"] = "Strong" if c["ratio"] >= .75 else "Partial" if c["ratio"] >= .4 else "Weak"
        return comps, top, d

    @app.get("/api/insights/why/<bid>", endpoint="ix_why")
    def why(bid):
        if bid not in W or bid == ACTIVE:
            return jsonify(error="unknown well"), 404
        comps, top, d = parts(bid)
        rank = [s["well_id"] for s in similar(ACTIVE)]
        row = next(s for s in similar(ACTIVE) if s["well_id"] == bid)
        total = round(sum(c["value"] for c in comps))
        matched = [slim(e) for e in EV if e["well_id"] == bid and e["event_type"] == top]
        weak = [c for c in comps if c["verdict"] == "Weak"]
        lowers = ["%s is weak (%s)" % (c["title"], c["finding"]) for c in weak] or ["No component is weak; the match is broad-based"]
        strong = sum(c["verdict"] == "Strong" for c in comps)
        conf = "High" if strong >= 4 else "Moderate" if strong >= 2 else "Low"
        return jsonify(well_id=bid, similarity=row["similarity"], computed_total=total, rank=rank.index(bid) + 1, of=len(rank),
                       steps=comps, matched_events=matched, reasons=row["reasons"], confidence=conf, lowers_confidence=lowers,
                       top_type=top, safety=SAFETY,
                       note="Transparent rule-based scoring: every point in the trail is arithmetic on synthetic well attributes. "
                            "It shows why the wells look alike; it does not claim they will behave alike.")

    @app.get("/api/insights/twin", endpoint="ix_twin")
    def twin():
        sm_list = similar(ACTIVE)
        tid = request.args.get("well") or sm_list[0]["well_id"]
        if tid not in W or tid == ACTIVE:
            return jsonify(error="unknown well"), 404
        a, b, row = W[ACTIVE], W[tid], next(s for s in sm_list if s["well_id"] == tid)
        d = STATE["depth"]

        def line(label, k, sc, f):
            close = None if sc is None else round(max(0, 1 - abs(a[k] - b[k]) / sc) * 100)
            return dict(label=label, active=f % a[k], twin=f % b[k], closeness=close)
        metrics = [line("Total depth", "total_depth", 1500, "%d m"), line("Mud weight", "mud_weight", .2, "%.2f SG"),
                   line("ROP", "rop", 20, "%d m/hr"), line("WOB", "wob", 10, "%d t"), line("RPM", "rpm", 60, "%d"),
                   line("Pressure (not scored)", "pressure", None, "%d bar")]
        metrics.insert(0, dict(label="Formation", active=a["formation"], twin=b["formation"], closeness=100 if a["formation"] == b["formation"] else 0))
        metrics.append(dict(label="Reservoir type (not scored)", active=a["reservoir_type"], twin=b["reservoir_type"], closeness=None))
        events = [{**slim(e), "offset_m": e["depth"] - d, "steps": e["steps"]} for e in sorted(EV, key=lambda e: e["depth"]) if e["well_id"] == tid]
        return jsonify(twin=tid, similarity=row["similarity"], distance_km=row["distance_km"], reasons=row["reasons"], metrics=metrics,
                       events=events, active_depth=d, candidates=[dict(well_id=s["well_id"], similarity=s["similarity"]) for s in sm_list[:4]],
                       safety=SAFETY)

    # ------------------------------------------------------------------ Replay the Well
    @app.get("/api/insights/replay/<wid>", endpoint="ix_replay")
    def replay(wid):
        if wid not in W:
            return jsonify(error="unknown well"), 404
        es = sorted([e for e in EV if e["well_id"] == wid], key=lambda e: e["depth"])
        w = W[wid]
        lo = 2600 if not es else min(2600, (min(e["depth"] for e in es) - 100) // 100 * 100)
        return jsonify(well_id=wid, formation=w["formation"], start=max(0, lo), end=w["total_depth"], active_depth=STATE["depth"],
                       layers=C["LAYERS"], mud_weight=w["mud_weight"],
                       events=[{**slim(e), "steps": e["steps"]} for e in es], safety=SAFETY,
                       note="Replay is depth-driven: the synthetic records hold events, not continuous time-series.")

    # ------------------------------------------------------------------ Next Best Investigation
    @app.get("/api/insights/investigations", endpoint="ix_next")
    def investigations():
        R, sm, d = risk(), simmap(), STATE["depth"]
        items = []
        for z in R["zones"][:4]:
            es = [BYID[i] for i in z["event_ids"]]
            best = max(es, key=lambda e: sm[e["well_id"]]["similarity"])
            bsim = sm[best["well_id"]]["similarity"]
            urgency = 1 - min(max(z["distance"], 0), 300) / 300
            base = .5 * z["score"] + .3 * bsim + 20 * urgency
            common = dict(event_type=z["event_type"], zone="%d-%d m" % (z["lo"], z["hi"]), eta_h=eta(z["distance"]))

            def add(kind, title, why_, ids, bonus=0):
                items.append(dict(kind=kind, title=title, why=why_, event_ids=ids, priority=round(min(99, base + bonus)), **common))
            add("Read source record",
                "Open %s for %s at %d m" % (best["source_document"], best["well_id"], best["depth"]),
                "Most similar offset (%d%%) with a %s event %d m from the current depth; the record holds cause, action and outcome." % (bsim, nice(z["event_type"]).lower(), abs(best["depth"] - d)),
                [best["event_id"]], 4)
            outs = {e["outcome"] for e in es}
            acts = {e["action_taken"] for e in es}
            if len(acts) > 1:
                add("Compare offsets", "Compare how %d offsets handled %s" % (z["n_wells"], nice(z["event_type"]).lower()),
                    "%d different historical actions were recorded with %d different outcomes; reading them side by side shows what varied." % (len(acts), len(outs)),
                    [e["event_id"] for e in es], 0)
            if z["n_wells"] == 1:
                add("Corroborate", "Look for a second source for the %s signal" % nice(z["event_type"]).lower(),
                    "Only one offset well backs this zone, so the pattern is thin.", [es[0]["event_id"]], -8)
            if z["same_formation"] < len(es):
                add("Check context", "Check formation match for %s evidence" % nice(z["event_type"]).lower(),
                    "%d of %d events are outside %s, which weakens the analogy." % (len(es) - z["same_formation"], len(es), z["formation"]), [e["event_id"] for e in es if e["formation"] != z["formation"]], -4)
            for r in REVIEW.get(z["event_type"], [])[:2]:
                add("Review", r, "Standard information-gathering step for a %s pattern (%d offset wells)." % (nice(z["event_type"]).lower(), z["n_wells"]),
                    z["event_ids"][:3], -10)
        items.sort(key=lambda i: -i["priority"])
        for i, it in enumerate(items):
            it["rank"], it["level"] = i + 1, lvl(it["priority"])
        return jsonify(items=items[:8], safety=SAFETY,
                       note="Ranked by expected information value (zone risk, similarity of the source well, closeness to the zone). "
                            "Every item is something to READ, COMPARE or ASK - never a parameter change.")
