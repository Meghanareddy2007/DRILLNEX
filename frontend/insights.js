/* eRTMAC-NWIS Insights add-on. Self-contained: only reads /api/insights/*, /api/events and the existing
   evidence()/showWell() helpers. Nothing from the original script is modified. SYNTHETIC DATA ONLY. */
(() => {
  const q = s => document.querySelector(s);
  const j = p => api('/api/insights/' + p);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const N = t => String(t).split('_').map(w => w[0] + w.slice(1).toLowerCase()).join(' ');
  const trunc = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
  const TC = { MUD_LOSS: '#ffc65b', KICK: '#ff5968', STUCK_PIPE: '#a78bfa', OVERPRESSURE: '#ff7a3d', TORQUE_SPIKE: '#c07740', CEMENTING: '#d6d64a', FISHING: '#a7a19b', NPT: '#aaaaaa' };
  const LV = { HIGH: '#ff5968', MEDIUM: '#ffc65b', LOW: '#e88c46' };
  const lvOf = v => v >= 75 ? 'HIGH' : v >= 50 ? 'MEDIUM' : 'LOW';
  const pill = (t, c) => `<span class="ix-pill" style="color:${c};border-color:${c}">${esc(t)}</span>`;
  const S = { tab: 'bridge', c: {}, zone: 0, hz: 600, gt: '', gsel: null, tw: '', wy: '', rw: '', built: false };
  const get = async p => S.c[p] || (S.c[p] = await j(p));
  const evBtn = (id, label) => `<button class="ix-btn" onclick="IX.ev('${id}')">${label || 'View evidence'}</button>`;
  const TABS = [['bridge', '🌉 Historical-to-Future Bridge', 1], ['horizon', '🔭 Risk Horizon'], ['graph', '🕸 Institutional Memory Graph'],
    ['twin', '🧬 Historical Twin Well'], ['why', '🕵 Why This Well?'], ['replay', '⏪ Replay the Well'], ['next', '🧭 Next Best Investigation']];

  /* ---------------------------------------------------------------- 1. Historical-to-Future Bridge */
  function bridgeSvg(d, z) {
    const wells = [...new Set(z.past.map(p => p.well_id))].slice(0, 6), Wd = 900, L = 96, Rr = 24;
    const ds = z.past.map(p => p.depth).concat([d.active.depth, z.future.lo, z.future.hi]);
    const x0 = Math.min(...ds) - 30, x1 = Math.max(...ds) + 30, sx = v => L + (v - x0) / (x1 - x0) * (Wd - L - Rr);
    const top = 64, rh = 36, H = top + wells.length * rh + 46, rowY = i => top + i * rh + rh / 2;
    const zx0 = sx(z.future.lo), zx1 = Math.max(sx(z.future.hi), zx0 + 18), zc = (zx0 + zx1) / 2, F = 'font-family="Segoe UI,system-ui,sans-serif"';
    let s = `<svg class="ix-svg" viewBox="0 0 ${Wd} ${H}" style="min-width:680px" role="img" aria-label="Bridge from historical events to the upcoming interval">`;
    s += `<rect x="${zx0}" y="30" width="${zx1 - zx0}" height="${H - 30 - 36}" fill="#ff5968" opacity=".14" stroke="#ff5968" stroke-dasharray="4 3"/>`;
    s += `<text x="${zc}" y="20" text-anchor="middle" fill="#ff6b6b" font-size="11" font-weight="700" ${F}>FUTURE · ${z.future.lo}–${z.future.hi} m</text>`;
    wells.forEach((w, i) => {
      const y = rowY(i), p = z.past.find(x => x.well_id === w);
      s += `<line x1="${L}" x2="${Wd - Rr}" y1="${y}" y2="${y}" stroke="#36302a"/><text x="8" y="${y + 4}" fill="#f3f1ee" font-size="12" font-weight="600" ${F}>${w}</text><text x="52" y="${y + 4}" fill="#9a938d" font-size="10" ${F}>${p.similarity}%</text>`;
    });
    z.past.filter(p => wells.includes(p.well_id)).forEach(p => {
      const x = sx(p.depth), y = rowY(wells.indexOf(p.well_id)), c = LV[p.severity] || '#aaa';
      s += `<path d="M${x} ${y - 7} C${x} ${y - 46},${zc} ${y - 30},${zc} 44" fill="none" stroke="${c}" stroke-width="1.4" opacity=".55" stroke-dasharray="5 4"/>`;
    });
    z.past.filter(p => wells.includes(p.well_id)).forEach(p => {
      const x = sx(p.depth), y = rowY(wells.indexOf(p.well_id)), c = LV[p.severity] || '#aaa';
      s += `<g class="ix-node" onclick="IX.ev('${p.event_id}')"><title>${esc(p.well_id)} · ${esc(N(p.event_type))} @ ${p.depth} m · ${esc(p.outcome)}</title><circle cx="${x}" cy="${y}" r="7" fill="${c}" stroke="#fff" stroke-width="1.5"/></g><text x="${x}" y="${y + 20}" text-anchor="middle" fill="#9a938d" font-size="10" ${F}>${p.depth} m</text>`;
    });
    const cx = sx(d.active.depth);
    s += `<line x1="${cx}" x2="${cx}" y1="30" y2="${H - 36}" stroke="#e88c46" stroke-width="2" stroke-dasharray="6 4"/><circle cx="${cx}" cy="${H - 36}" r="5" fill="#fff" stroke="#4da5ff" stroke-width="3"/>`;
    const lx = Math.min(Math.max(cx, 80), Wd - 80);
    s += `<text x="${lx}" y="${H - 14}" text-anchor="middle" fill="#e88c46" font-size="11" font-weight="700" ${F}>W-125 NOW · ${d.active.depth} m</text>`;
    s += `<text x="8" y="${H - 14}" fill="#9a938d" font-size="10" ${F}>PAST →</text><text x="${Wd - Rr}" y="${H - 14}" text-anchor="end" fill="#9a938d" font-size="10" ${F}>deeper →</text></svg>`;
    return s;
  }
  async function pBridge(el) {
    const d = await get('bridge'), z = d.zones[Math.min(S.zone, d.zones.length - 1)], f = z.future;
    const eta = f.in_zone ? 'Inside zone' : `~${f.eta_lo_h}–${f.eta_hi_h} h`;
    el.innerHTML = `<div class="ix-h"><div><h3>Historical-to-Future Bridge</h3><small>What happened in offset wells → what W-125 looks like today → the interval it is about to enter.</small></div></div>
    <div class="ix-kpis"><div><span>Bridge strength</span><b style="color:${z.strength >= 75 ? '#4cda8a' : z.strength >= 55 ? '#ffc65b' : '#9a938d'}">${z.strength}</b> <small class="ix-sub">${z.strength_label} evidence</small></div>
      <div><span>Risk score</span><b style="color:${LV[z.level]}">${z.score}/100</b> <small class="ix-sub">${z.level}</small></div>
      <div><span>Distance to zone</span><b>${f.in_zone ? '0' : f.distance} m</b></div><div><span>Time to reach*</span><b>${eta}</b></div>
      <div><span>Offset wells</span><b>${new Set(z.past.map(p => p.well_id)).size}</b> <small class="ix-sub">${z.past.length} events</small></div></div>
    <div class="ix-chips">${d.zones.map((x, i) => `<span class="chip ${i === S.zone ? 'on' : ''}" onclick="IX.zone(${i})">${N(x.event_type)} · ${x.score}</span>`).join('')}</div>
    <div class="box" style="padding:6px"><div class="ix-scroll">${bridgeSvg(d, z)}</div><small class="ix-sub">Each dot is a historical ${N(z.event_type).toLowerCase()} event in an offset well (colour = severity); dashed arcs carry that experience into the upcoming zone. Click a dot for the source record.</small></div>
    <div class="ix-cols">
     <div class="ix-card past"><h4>Past · what the offsets recorded</h4>${z.past.map(p => `<div class="ix-ev"><div class="row"><b>${p.well_id}</b><span>similarity ${p.similarity}%</span></div><small>${p.depth} m · ${p.date} · ${p.severity} · ${p.offset_m >= 0 ? '+' : ''}${p.offset_m} m from W-125</small><br>Cause: ${esc(p.cause)}<br>Recorded action: ${esc(p.action_taken)}<br>Outcome: ${esc(p.outcome)}<br>${evBtn(p.event_id)}<button class="ix-btn" onclick="IX.go('replay',{well:'${p.well_id}'})">Replay ${p.well_id}</button></div>`).join('')}</div>
     <div class="ix-card now"><h4>Present · conditions today</h4><table class="ix-mt"><tr><th></th><th>W-125</th><th>Offsets</th></tr>${z.present.matches.map(m => `<tr><td>${m.label}</td><td><b>${esc(m.now)}</b></td><td><small class="ix-sub">${esc(m.past)}</small></td></tr>`).join('')}</table></div>
     <div class="ix-card fut"><h4>Future · what lies ahead</h4><p style="margin:0 0 6px"><b>${N(z.event_type)}</b> zone at <b>${f.lo}–${f.hi} m</b> ${pill(z.level, LV[z.level])}</p><small class="ix-sub">${f.in_zone ? 'W-125 is inside the historical interval.' : `${f.distance} m below current depth (${eta} at ${d.rop} m/hr).`}</small>
      <h4 style="margin-top:12px">Worth reviewing (information only)</h4><ul style="margin:0;padding-left:16px">${z.review.map(r => `<li>${esc(r)}</li>`).join('')}</ul></div></div>
    <p class="ix-sub" style="margin-top:8px">* ${esc(d.note)}</p>`;
  }

  /* ---------------------------------------------------------------- 2. Risk Horizon */
  async function pHorizon(el) {
    const d = await get('horizon?ahead=' + S.hz), Wd = 900, H = 290, ml = 46, mr = 14, mt = 16, mb = 62, F = 'font-family="Segoe UI,system-ui,sans-serif"';
    const sx = v => ml + (v - d.depth) / d.ahead * (Wd - ml - mr), sy = v => mt + (100 - v) / 100 * (H - mt - mb);
    const pts = d.bins.map(b => `${sx(b.depth).toFixed(1)},${sy(b.index).toFixed(1)}`), last = d.bins[d.bins.length - 1];
    let s = `<svg class="ix-svg" viewBox="0 0 ${Wd} ${H}" style="min-width:680px" role="img" aria-label="Historical exposure index along the next ${d.ahead} metres">
     <defs><linearGradient id="ixg" gradientUnits="userSpaceOnUse" x1="0" x2="0" y1="${sy(100)}" y2="${sy(0)}"><stop offset="0" stop-color="#ff5968"/><stop offset=".25" stop-color="#ff5968"/><stop offset=".5" stop-color="#ffc65b"/><stop offset=".75" stop-color="#4cda8a"/><stop offset="1" stop-color="#e88c46"/></linearGradient></defs>`;
    [0, 25, 50, 75, 100].forEach(v => s += `<line x1="${ml}" x2="${Wd - mr}" y1="${sy(v)}" y2="${sy(v)}" stroke="${v === 50 || v === 75 ? '#ffc65b66' : '#292420'}" ${v === 50 || v === 75 ? 'stroke-dasharray="4 4"' : ''}/><text x="${ml - 6}" y="${sy(v) + 4}" text-anchor="end" fill="#9a938d" font-size="10" ${F}>${v}</text>`);
    s += `<path d="M${pts.join('L')}L${sx(last.depth)},${sy(0)}L${sx(d.depth)},${sy(0)}Z" fill="url(#ixg)" opacity=".28"/><path d="M${pts.join('L')}" fill="none" stroke="url(#ixg)" stroke-width="2.5"/>`;
    d.bins.forEach((b, i) => { const w = (Wd - ml - mr) / d.ahead * 25; s += `<rect x="${sx(b.depth) - w / 2}" y="${mt}" width="${w}" height="${H - mt - mb}" fill="transparent"><title>${b.depth} m · exposure ${b.index} (${b.level})${b.dominant ? ' · mostly ' + N(b.dominant) : ''} · ~${b.eta_h} h away</title></rect>`; });
    for (let m = Math.ceil(d.depth / 100) * 100; m <= d.depth + d.ahead; m += 100) s += `<line x1="${sx(m)}" x2="${sx(m)}" y1="${sy(0)}" y2="${sy(0) + 5}" stroke="#9a938d"/><text x="${sx(m)}" y="${sy(0) + 18}" text-anchor="middle" fill="#beb9b4" font-size="10" ${F}>${m} m</text><text x="${sx(m)}" y="${sy(0) + 31}" text-anchor="middle" fill="#9a938d" font-size="9" ${F}>+${((m - d.depth) / d.rop).toFixed(1)} h</text>`;
    d.markers.forEach(m => { const x = sx(m.depth), y = sy(0) - 9; s += `<g class="ix-node" onclick="IX.ev('${m.event_id}')"><title>${m.well_id} · ${N(m.event_type)} @ ${m.depth} m (${m.severity})</title><path d="M${x} ${y - 7} L${x + 6} ${y + 5} L${x - 6} ${y + 5}Z" fill="${TC[m.event_type]}" stroke="#0d0b0a"/></g>`; });
    s += `<line x1="${ml}" x2="${ml}" y1="${mt}" y2="${sy(0)}" stroke="#e88c46" stroke-width="2"/><text x="${ml + 6}" y="${mt + 10}" fill="#e88c46" font-size="11" font-weight="700" ${F}>NOW ${d.depth} m</text></svg>`;
    const types = [...new Set(d.markers.map(m => m.event_type))];
    el.innerHTML = `<div class="ix-h"><div><h3>Risk Horizon</h3><small>Don't wait for the problem: see the exposure building over the next ${d.ahead} m and how long it takes to get there.</small></div>
     <div class="ix-chips" style="margin:0">${[300, 600, 900].map(v => `<span class="chip ${v === S.hz ? 'on' : ''}" onclick="IX.hz(${v})">${v} m</span>`).join('')}</div></div>
     <div class="ix-kpis">${d.windows.map(w => `<div><span>${w.label}</span><b style="color:${LV[w.level]}">${w.peak}</b> ${pill(w.level, LV[w.level])}<br><small class="ix-sub">peak at ${w.peak_depth} m${w.dominant ? ' · ' + N(w.dominant) : ''} · ~${w.eta_h} h</small></div>`).join('')}</div>
     <div class="box" style="padding:6px"><div class="ix-scroll">${s}</div>
     <div class="lgd" style="margin-top:4px">${types.map(t => `<span><i style="background:${TC[t]};border-radius:2px"></i>${N(t)}</span>`).join('')}<span>▲ = historical event · hours = distance ÷ current ROP (${d.rop} m/hr)</span></div></div>
     <p class="ix-sub" style="margin-top:8px">${esc(d.note)} Headline Risk Score for the nearest zone: <b>${d.official_score}</b>.</p>`;
  }

  /* ---------------------------------------------------------------- 3. Institutional Memory Graph */
  const CX = [10, 195, 380, 565, 750, 935], NW = 150, RH = 30, HEAD = ['ACTIVE WELL', 'OFFSET WELLS', 'EVENTS', 'CAUSES', 'RECORDED ACTIONS', 'OUTCOMES'];
  const KC = { active: '#4da5ff', well: '#a78bfa', cause: '#7a7b66', action: '#a4622f', outcome: '#4cda8a' };
  function trace(id, edges) {
    const set = new Set([id]);
    [1, 0].forEach(dir => { const st = [id]; while (st.length) { const c = st.pop(); edges.forEach(e => { const [a, b] = dir ? [e.source, e.target] : [e.target, e.source]; if (a === c && !set.has(b)) { set.add(b); st.push(b); } }); } });
    return set;
  }
  async function pGraph(el) {
    const d = await get('graph' + (S.gt ? '?type=' + S.gt : '')), by = {}, cols = [[], [], [], [], [], []];
    d.nodes.forEach(n => { by[n.id] = n; cols[n.col].push(n); });
    const mx = Math.max(...cols.map(c => c.length)), place = c => cols[c].forEach((n, i) => n.y = 46 + i * RH + (mx - cols[c].length) * RH / 2);
    place(0); place(1);
    const src = n => (d.edges.find(e => e.target === n.id) || {}).source;
    cols[2].sort((a, b) => cols[1].indexOf(by[src(a)]) - cols[1].indexOf(by[src(b)])); place(2);
    for (let c = 3; c <= 5; c++) { const avg = n => { const ys = d.edges.filter(e => e.target === n.id).map(e => by[e.source].y); return ys.reduce((a, b) => a + b, 0) / (ys.length || 1); }; cols[c].sort((a, b) => avg(a) - avg(b)); place(c); }
    const lit = S.gsel && by[S.gsel] ? trace(S.gsel, d.edges) : null, H = 46 + mx * RH + 12, F = 'font-family="Segoe UI,system-ui,sans-serif"';
    let s = `<svg class="ix-svg" viewBox="0 0 1100 ${H}" style="min-width:900px" role="img" aria-label="Institutional memory graph">`;
    HEAD.forEach((h, i) => s += `<text x="${CX[i]}" y="16" fill="#9a938d" font-size="10" letter-spacing="1" ${F}>${h}</text>`);
    d.edges.forEach(e => { const a = by[e.source], b = by[e.target], x1 = CX[a.col] + NW, x2 = CX[b.col], on = !lit || (lit.has(a.id) && lit.has(b.id));
      s += `<path d="M${x1} ${a.y} C${x1 + 24} ${a.y},${x2 - 24} ${b.y},${x2} ${b.y}" fill="none" stroke="${on && lit ? '#e88c46' : '#534d47'}" stroke-width="${e.weight ? 1 + e.weight / 40 : 1.2}" opacity="${on ? (lit ? .95 : .55) : .12}"/>`; });
    d.nodes.forEach(n => { const x = CX[n.col], on = !lit || lit.has(n.id), c = n.kind === 'event' ? TC[n.etype] : KC[n.kind], sel = n.id === S.gsel;
      s += `<g class="ix-node" opacity="${on ? 1 : .22}" onclick="IX.pick('${n.id.replace(/'/g, "\\'")}')"><title>${esc(n.label)}${n.sub ? ' · ' + esc(n.sub) : ''}</title><rect x="${x}" y="${n.y - 12}" width="${NW}" height="24" rx="5" fill="${c}" fill-opacity=".22" stroke="${sel ? '#fff' : c}" stroke-width="${sel || n.pattern ? 2 : 1}"/><text x="${x + 8}" y="${n.y + 4}" fill="#f1efed" font-size="11" ${F}>${esc(trunc(n.label, 23))}</text></g>`; });
    s += '</svg>';
    el.innerHTML = `<div class="ix-h"><div><h3>Institutional Memory Graph</h3><small>Wells → events → causes → recorded actions → outcomes, stitched together from the ingested DDR / WCR / MLR records. Click any node to trace its lineage.</small></div></div>
     <div class="ix-kpis"><div><span>Nodes</span><b>${d.meta.nodes}</b></div><div><span>Links</span><b>${d.meta.edges}</b></div><div><span>Offset wells</span><b>${d.meta.wells}</b></div><div><span>Source documents</span><b>${d.meta.documents}</b></div></div>
     <div class="ix-chips"><span class="chip ${S.gt ? '' : 'on'}" onclick="IX.gt('')">All events</span>${d.types.map(t => `<span class="chip ${S.gt === t ? 'on' : ''}" onclick="IX.gt('${t}')">${N(t)}</span>`).join('')}</div>
     <div class="box" style="padding:6px"><div class="ix-scroll">${s}</div><small class="ix-sub">Thick outline = same pattern as the active alert (${N(d.top_type)}). Line weight from W-125 = similarity.</small></div><div class="ix-gd" id="ixgd"></div>`;
    graphDetail(d, by);
  }
  function graphDetail(d, by) {
    const box = q('#ixgd'), n = by[S.gsel];
    if (!n) { box.innerHTML = '<span class="ix-sub">Select a node to see its record and lineage.</span>'; return; }
    if (n.kind === 'event') { const e = d.events[n.event_id]; box.innerHTML = `<b>${e.well_id} · ${N(e.event_type)} @ ${e.depth} m</b> ${pill(e.severity, LV[e.severity])}<br>Cause: ${esc(e.cause)}<br>Recorded action: ${esc(e.action_taken)}<br>Outcome: ${esc(e.outcome)}<br><small class="ix-sub">${e.source_document} · ${e.document_type} · ${e.date}</small><br>${evBtn(e.event_id)}<button class="ix-btn" onclick="IX.go('replay',{well:'${e.well_id}'})">Replay ${e.well_id}</button>`; }
    else if (n.kind === 'well' || n.kind === 'active') box.innerHTML = `<b>${n.label}</b> <span class="ix-sub">${esc(n.sub || '')}</span><br>` + (n.kind === 'well' ? `<button class="ix-btn" onclick="IX.go('why',{well:'${n.label}'})">Why this well?</button><button class="ix-btn" onclick="IX.go('twin',{well:'${n.label}'})">Compare as twin</button><button class="ix-btn" onclick="typeof showWell==='function'&&showWell('${n.label}')">Open history</button>` : 'Everything to the right is what the institution already knows from offset wells.');
    else box.innerHTML = `<b>${esc(n.label)}</b> <span class="ix-sub">(${n.kind}) seen in ${n.event_ids.length} event(s)</span><br>${n.event_ids.map(id => evBtn(id, d.events[id].well_id + ' · ' + d.events[id].depth + ' m')).join('')}`;
  }

  /* ---------------------------------------------------------------- 4. Historical Twin Well */
  async function pTwin(el) {
    const d = await get('twin' + (S.tw ? '?well=' + S.tw : ''));
    el.innerHTML = `<div class="ix-h"><div><h3>Historical Twin Well · ${d.twin}</h3><small>The offset well that looks most like W-125 today, side by side, with its own history laid against W-125's depth.</small></div></div>
     <div class="ix-chips">${d.candidates.map(c => `<span class="chip ${c.well_id === d.twin ? 'on' : ''}" onclick="IX.twin('${c.well_id}')">${c.well_id} · ${c.similarity}%</span>`).join('')}</div>
     <div class="ix-kpis"><div><span>Similarity</span><b style="color:var(--a)">${d.similarity}%</b></div><div><span>Distance</span><b>${d.distance_km} km</b></div><div><span>Recorded events</span><b>${d.events.length}</b></div></div>
     <div class="ix-cols two"><div class="ix-card"><h4>W-125 vs ${d.twin}</h4><table class="ix-mt"><tr><th></th><th>W-125</th><th>${d.twin}</th><th>Closeness</th></tr>${d.metrics.map(m => `<tr><td>${m.label}</td><td>${esc(m.active)}</td><td>${esc(m.twin)}</td><td>${m.closeness == null ? '<small class="ix-sub">n/a</small>' : `<div class="ix-bar"><i style="width:${m.closeness}%"></i></div>`}</td></tr>`).join('')}</table>
       <p style="margin:8px 0 0">${d.reasons.map(r => `<span class="chip" style="cursor:default">${esc(r)}</span>`).join('')}</p>
       <button class="ix-btn pri" onclick="IX.go('why',{well:'${d.twin}'})">Why this well?</button><button class="ix-btn" onclick="IX.go('replay',{well:'${d.twin}'})">Replay ${d.twin}</button></div>
      <div class="ix-card"><h4>${d.twin} history vs W-125 depth (${d.active_depth} m)</h4>${d.events.map(e => `<div class="ix-ev"><div class="row"><b style="color:${TC[e.event_type]}">${N(e.event_type)}</b><span>${e.depth} m <span class="ix-off">${e.offset_m >= 0 ? '+' + e.offset_m + ' m ahead of W-125' : Math.abs(e.offset_m) + ' m above W-125'}</span></span></div><small>${e.date} · ${e.severity}</small><br>Cause: ${esc(e.cause)}<br>Outcome: ${esc(e.outcome)}<br>${evBtn(e.event_id)}</div>`).join('') || '<span class="ix-sub">No recorded events.</span>'}</div></div>`;
  }

  /* ---------------------------------------------------------------- 5. Why This Well? */
  async function pWhy(el) {
    const rk = await get('ranking'), id = S.wy || rk[0].well_id, d = await get('why/' + id);
    const vc = { Strong: '#4cda8a', Partial: '#ffc65b', Weak: '#ff5968' };
    el.innerHTML = `<div class="ix-h"><div><h3>Why This Well?</h3><small>Not just “Similarity = ${d.similarity}%” - the full reasoning trail, one auditable step at a time.</small></div>
      <select style="width:auto" onchange="IX.why(this.value)">${rk.map(w => `<option value="${w.well_id}" ${w.well_id === id ? 'selected' : ''}>${w.well_id} · ${w.similarity}%</option>`).join('')}</select></div>
     <div class="ix-cols two"><div class="ix-trail">${d.steps.map((s, i) => `<div class="ix-step"><span class="n">${i + 1}</span><div><b>${s.title}</b> ${pill(s.verdict, vc[s.verdict])}<small>${esc(s.finding)}</small><div class="ix-bar" style="margin-top:5px"><i style="width:${s.ratio * 100}%"></i></div></div><div class="pts">${s.value.toFixed(1)}<small> / ${s.weight}</small></div></div>`).join('')}
       <div class="ix-total"><div><b>${id}</b> is similar to W-125<br><small class="ix-sub">Rank ${d.rank} of ${d.of} wells · confidence <b>${d.confidence}</b></small></div><div class="big">${d.computed_total}%</div></div></div>
      <div><div class="ix-card"><h4>Matched history (${N(d.top_type)})</h4>${d.matched_events.map(e => `<div class="ix-ev"><b>${e.depth} m</b> · ${e.date}<br>Cause: ${esc(e.cause)}<br>Outcome: ${esc(e.outcome)}<br>${evBtn(e.event_id)}</div>`).join('') || '<span class="ix-sub">This well has no recorded event of the alert’s type.</span>'}</div>
       <div class="ix-card" style="margin-top:10px"><h4>What would lower confidence</h4><ul style="margin:0;padding-left:16px">${d.lowers_confidence.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>
       <p class="ix-sub">${esc(d.note)}</p></div></div>`;
  }

  /* ---------------------------------------------------------------- 6. Replay the Well */
  const RP = { id: null, d: null, depth: 0, playing: false, speed: 1, shown: new Set(), cur: null, step: 0, hold: 0, last: 0, H: 440 };
  const rpY = v => (v - RP.d.start) / (RP.d.end - RP.d.start) * RP.H;
  function rpReset() { RP.playing = false; RP.depth = RP.d.start; RP.shown = new Set(); RP.cur = null; RP.step = 0; RP.hold = 0; }
  async function pReplay(el) {
    if (!S.c.allev) S.c.allev = await api('/api/events');
    const rk = await get('ranking'), ids = [...new Set(S.c.allev.map(e => e.well_id))].filter(w => w !== 'W-125');
    ids.sort((a, b) => ((rk.find(x => x.well_id === b) || {}).similarity || 0) - ((rk.find(x => x.well_id === a) || {}).similarity || 0));
    const id = S.rw || rk[0].well_id, d = await get('replay/' + id);
    RP.playing = false; RP.d = d; if (RP.id !== id) { RP.id = id; } rpReset();
    let bands = '', ticks = '';
    d.layers.forEach((l, i) => { const t = Math.max(l.top, d.start), b = Math.min(i + 1 < d.layers.length ? d.layers[i + 1].top : 1e9, d.end); if (b > t) bands += `<div class="band" style="top:${rpY(t)}px;height:${rpY(b) - rpY(t)}px;background:${l.color}"></div><div class="bl" style="top:${rpY(t) + 9}px">${esc(l.name)}</div>`; });
    for (let m = Math.ceil(d.start / 100) * 100; m <= d.end; m += 100) ticks += `<div class="tk" style="top:${rpY(m)}px">${m}</div>`;
    const marks = d.events.map((e, i) => `<div class="mk" id="ixm${i}" style="top:${rpY(e.depth)}px;background:${TC[e.event_type]};opacity:.25" title="${N(e.event_type)} @ ${e.depth} m">${i + 1}</div>`).join('');
    const ay = d.active_depth >= d.start && d.active_depth <= d.end ? `<div class="now" style="top:${rpY(d.active_depth)}px">W-125 now · ${d.active_depth} m</div>` : '';
    el.innerHTML = `<div class="ix-h"><div><h3>Replay the Well · ${d.well_id}</h3><small>Watch a past well drill through the interval W-125 is approaching. Events surface as the bit reaches their depth.</small></div>
      <select style="width:auto" onchange="IX.rw(this.value)">${ids.map(w => `<option value="${w}" ${w === id ? 'selected' : ''}>${w}${(rk.find(x => x.well_id === w) || {}).similarity ? ' · ' + rk.find(x => x.well_id === w).similarity + '%' : ''}</option>`).join('')}</select></div>
     <div class="ix-rp" id="ixrp"><div class="box" style="padding:8px"><div class="ix-well" id="ixw">${bands}${ticks}<div class="path" style="height:${RP.H}px"></div><div class="fill" id="ixfill" style="height:0"></div>${ay}${marks}<div class="bit" id="ixbit" style="top:0"></div></div></div>
      <div><div class="ix-kpis"><div><span>Depth</span><b id="ixdep">-</b></div><div><span>Formation</span><b id="ixfm" style="font-size:14px">-</b></div><div><span>Events surfaced</span><b id="ixcnt">0</b> <small class="ix-sub">/ ${d.events.length}</small></div></div>
       <div class="ix-live" id="ixlive"></div>
       <div class="ix-ctl"><button class="ix-btn pri" id="ixplay" onclick="IX.play()">▶ Play</button><button class="ix-btn" onclick="IX.reset()">↺ Reset</button><button class="ix-btn" onclick="IX.sync()">Jump to W-125 depth</button>
        <select onchange="IX.speed(this.value)"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select><input type="range" id="ixsl" min="${d.start}" max="${d.end}" step="1" value="${d.start}" oninput="IX.scrub(this.value)"></div>
       <p class="ix-sub">${esc(d.note)}</p></div></div>`;
    paint();
  }
  function paint() {
    if (!q('#ixrp')) return; const d = RP.d;
    q('#ixbit').style.top = rpY(RP.depth) + 'px'; q('#ixfill').style.height = rpY(RP.depth) + 'px';
    d.events.forEach((e, i) => { const m = q('#ixm' + i); if (m) m.style.opacity = RP.shown.has(e.event_id) ? 1 : .25; });
    q('#ixdep').textContent = Math.round(RP.depth) + ' m'; q('#ixcnt').textContent = RP.shown.size; q('#ixsl').value = RP.depth;
    const lay = d.layers.filter(l => l.top <= RP.depth).pop(); q('#ixfm').textContent = lay ? lay.name : '-'; q('#ixplay').textContent = RP.playing ? '❚❚ Pause' : (RP.depth >= d.end ? '↺ Replay' : '▶ Play');
    const li = d.events.filter(e => RP.shown.has(e.event_id));
    q('#ixlive').innerHTML = li.length ? li.map(e => `<div class="lg" style="--c:${TC[e.event_type]}"><b>${N(e.event_type)}</b> · ${e.depth} m · ${e.date} ${pill(e.severity, LV[e.severity])}<br><small class="ix-sub">Cause: ${esc(e.cause)}</small>${RP.cur && RP.cur.event_id === e.event_id ? e.steps.slice(0, RP.step).map(s => `<div class="st">${esc(s)}</div>`).join('') : `<br><small>Recorded: ${esc(e.action_taken)} → ${esc(e.outcome)}</small>`}<br>${evBtn(e.event_id)}</div>`).reverse().join('')
      : `<div class="ix-card"><span class="ix-sub">Press <b>Play</b> to replay ${d.well_id} from ${d.start} m to TD (${d.end} m). ${d.active_depth >= d.start ? `W-125 is currently at ${d.active_depth} m - use “Jump to W-125 depth” to see what ${d.well_id} had already met by then.` : ''}</span></div>`;
  }
  function tick(t) {
    if (!RP.playing) return;
    if (!q('#ixrp') || q('#page-insights').classList.contains('hidden')) { RP.playing = false; return; }
    const dt = Math.min(.1, (t - (RP.last || t)) / 1000); RP.last = t; const d = RP.d;
    if (RP.hold > 0) { RP.hold -= dt; if (RP.hold <= 0) { if (RP.cur && RP.step < RP.cur.steps.length) { RP.step++; RP.hold = .9 / RP.speed; } else RP.hold = 0; } }
    else {
      const nx = RP.depth + 60 * RP.speed * dt, e = d.events.find(x => !RP.shown.has(x.event_id) && x.depth <= nx);
      if (e) { RP.depth = Math.max(RP.depth, e.depth); RP.shown.add(e.event_id); RP.cur = e; RP.step = 1; RP.hold = .9 / RP.speed; }
      else { RP.depth = Math.min(nx, d.end); if (RP.depth >= d.end) RP.playing = false; }
    }
    paint(); if (RP.playing) requestAnimationFrame(tick);
  }

  /* ---------------------------------------------------------------- 7. Next Best Investigation */
  async function pNext(el) {
    const d = await get('investigations');
    el.innerHTML = `<div class="ix-h"><div><h3>Next Best Investigation</h3><small>Where a few minutes of reading buys the most clarity - ranked by expected information value.</small></div></div>
     <div class="ix-safe">${esc(d.note)}</div>
     ${d.items.map(i => `<div class="ix-inv"><div class="rk">${i.rank}<small>rank</small></div><div><b>${esc(i.title)}</b><p>${esc(i.why)}</p>${pill(i.kind, '#e88c46')}${pill(N(i.event_type), TC[i.event_type])}${pill(i.level + ' · ' + i.priority, LV[i.level])}<span class="ix-sub">zone ${i.zone} · ~${i.eta_h} h at current ROP</span><br>${i.event_ids.slice(0, 3).map(id => evBtn(id, 'Evidence ' + id)).join('')}</div></div>`).join('')}`;
  }

  /* ---------------------------------------------------------------- shell */
  const PANELS = { bridge: pBridge, horizon: pHorizon, graph: pGraph, twin: pTwin, why: pWhy, replay: pReplay, next: pNext };
  async function render() {
    const el = q('#ixp'); if (!el) return;
    q('#ixtabs').innerHTML = TABS.map(t => `<button class="${t[0] === S.tab ? 'on' : ''} ${t[2] ? 'fav' : ''}" onclick="IX.go('${t[0]}')">${t[1]}</button>`).join('');
    RP.playing = false;
    try { await PANELS[S.tab](el); } catch (e) { console.error(e); el.innerHTML = `<div class="box">Could not load this panel (${esc(e.message)}). Is the backend running?</div>`; }
  }
  window.IX = {
    open() { S.c = {}; if (!S.built) { q('#v-insights').innerHTML = '<div class="ix-safe">🛡 Decision support only · Historical actions shown are <b>records from offset wells</b>, not drilling recommendations · Synthetic data.</div><div class="ix-tabs" id="ixtabs"></div><div class="box" id="ixp">Loading…</div>'; S.built = true; } render(); },
    go(t, o) { S.tab = t; if (o && o.well) { if (t === 'twin') S.tw = o.well; if (t === 'why') S.wy = o.well; if (t === 'replay') S.rw = o.well; } render(); },
    zone(i) { S.zone = i; render(); }, hz(v) { S.hz = v; render(); }, gt(t) { S.gt = t; S.gsel = null; render(); },
    pick(id) { S.gsel = S.gsel === id ? null : id; render(); }, twin(w) { S.tw = w; render(); }, why(w) { S.wy = w; render(); }, rw(w) { S.rw = w; render(); },
    ev(id) { if (typeof evidence === 'function') evidence(id); },
    play() { if (!RP.d) return; if (RP.playing) { RP.playing = false; paint(); return; } if (RP.depth >= RP.d.end) rpReset(); RP.playing = true; RP.last = 0; paint(); requestAnimationFrame(tick); },
    reset() { rpReset(); paint(); }, speed(v) { RP.speed = +v; },
    scrub(v) { RP.playing = false; RP.depth = +v; RP.shown = new Set(RP.d.events.filter(e => e.depth <= RP.depth).map(e => e.event_id)); RP.cur = null; paint(); },
    sync() { const v = RP.d.active_depth; IX.scrub(Math.min(Math.max(v, RP.d.start), RP.d.end)); },
  };
})();
