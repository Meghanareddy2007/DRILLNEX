/* ertmac.js - features merged in from eRTMAC-NWIS: Leaflet map, risk gauge, 3D subsurface, evidence + well-history modals */
const Q=s=>document.querySelector(s);const nice=t=>String(t).replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
let shown='W-107';
const tl=s=>'<div class="tl">'+(s||[]).map(x=>`<div class="st">${esc(x)}</div>`).join('')+'</div>';
function dxModal(h){Q('#dxBody').innerHTML=h;Q('#dxModal').classList.remove('hidden')}
async function evidence(id){try{const e=await api('/api/evidence/'+id);dxModal(`<h3>Evidence · ${esc(e.event_id)}</h3><table><tr><td>Source</td><td><b>${esc(e.source_document)}</b> (${esc(e.document_type)})</td></tr><tr><td>Depth</td><td>${e.depth} m</td></tr><tr><td>Event</td><td>${nice(e.event_type)} · ${e.severity}</td></tr><tr><td>Date</td><td>${e.date}</td></tr><tr><td>Cause</td><td>${esc(e.cause)}</td></tr><tr><td>Historical action</td><td>${esc(e.action_taken)}</td></tr><tr><td>Outcome</td><td>${esc(e.outcome)}</td></tr></table><h4>What happened next?</h4>${tl(e.steps)}<small class="muted">${esc(e.verification||'')}</small>`)}catch(err){toast(err.message)}}
async function showWell(id){try{const [w,ev]=await Promise.all([api('/api/wells/'+id),api('/api/wells/'+id+'/events')]);dxModal(`<h3>${id}${id===CURRENT?' — ACTIVE':''}</h3><p>${esc(w.formation)} · TD ${w.total_depth} m · ${w.reservoir_type} · ${ev.length} historical events</p><div class="actions" style="margin-bottom:8px"><button class="btn primary" onclick="setWell('${id}');Q('#dxModal').classList.add('hidden')">Make active well</button></div>`+(ev.map(e=>`<div class="reason"><b>${nice(e.event_type)}</b> · ${e.depth} m · ${e.date}<br>${esc(e.cause)}<h4 style="margin:6px 0">What happened next</h4>${tl(e.steps)}<button class="btn" onclick="evidence('${e.event_id}')">View evidence</button></div>`).join('')||'<div class="empty">No recorded historical events for this well.</div>'))}catch(err){toast(err.message)}}
let LMAP,LG,LFB=false;const HI=['MUD_LOSS','KICK','OVERPRESSURE','STUCK_PIPE'];
const MAPC={act:'#4da5ff',high:'#ff5968',med:'#ffc65b',low:'#4cda8a',other:'#a78bfa'};
async function loadMap(rad){
 document.querySelectorAll('.rbtn').forEach(b=>b.classList.toggle('primary',+b.dataset.r===rad));
 const ws=await api('/api/wells/nearby?radius='+rad);if(!window.L||!ws.length)return;const c=ws.find(w=>w.active)||ws[0];
 if(!LMAP){LMAP=L.map('map',{zoomControl:false}).setView([c.latitude,c.longitude],12);
  const sat=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'Tiles © Esri',className:'sat',maxZoom:18}).addTo(LMAP);
  sat.on('tileerror',()=>{if(LFB)return;LFB=true;L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',className:'osmdark',maxZoom:18}).addTo(LMAP)});
  L.control.zoom({position:'topright'}).addTo(LMAP);if(window.ResizeObserver)new ResizeObserver(()=>LMAP&&LMAP.invalidateSize()).observe(Q('#map'));L.control.scale({metric:true,imperial:false,position:'bottomleft'}).addTo(LMAP);
  const cp=L.control({position:'topleft'});cp.onAdd=()=>{const d=L.DomUtil.create('div','compass');d.textContent='N';return d};cp.addTo(LMAP)}
 LMAP.setView([c.latitude,c.longitude],12);LG&&LG.remove();LG=L.layerGroup().addTo(LMAP);let outer;
 [.25,.5,.75,1].forEach(f=>{const r=L.circle([c.latitude,c.longitude],{radius:rad*1000*f,color:'#5ab0ff',weight:f==1?1.6:1,opacity:.75,fill:false,dashArray:f==1?null:'4 7'}).addTo(LG);if(f==1)outer=r});
 ws.forEach(w=>{const col=w.active?MAPC.act:w.risk_types.some(t=>HI.includes(t))?MAPC.high:w.event_count?MAPC.med:MAPC.other,g=w.active?'◉':w.event_count?'!':'•';
  L.marker([w.latitude,w.longitude],{icon:L.divIcon({html:`<div class="pin ${w.active?'act':''}" style="--c:${col}"><b></b><span>${g}</span><em>${w.well_id}${w.active?'':`<small>${w.distance_km} km</small>`}</em></div>`,className:'',iconSize:[30,30],iconAnchor:[15,29],popupAnchor:[0,-28]})}).addTo(LG)
  .bindPopup(`<b>${w.well_id}</b>${w.active?' · ACTIVE':''}<br>Distance: ${w.distance_km} km<br>Formation: ${esc(w.formation)}<br>TD: ${w.total_depth} m<br>Events: ${w.event_count}${w.risk_types.length?' ('+w.risk_types.map(nice).join(', ')+')':''}<br><button class="btn" style="margin-top:6px" onclick="showWell('${w.well_id}')">Open history</button>`)
  .on('click',()=>LMAP.flyTo([w.latitude,w.longitude],Math.max(LMAP.getZoom(),13),{duration:.6}))});
 LMAP.fitBounds(outer.getBounds(),{padding:[10,10]});setTimeout(()=>LMAP.invalidateSize(),80)}
function gauge(v){const cx=130,cy=130,r=92,D=1.1,N=72,calm=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
 const th=x=>(135+2.7*x)*Math.PI/180,pt=(x,rad)=>[(cx+rad*Math.cos(th(x))).toFixed(2),(cy+rad*Math.sin(th(x))).toFixed(2)];
 const stops=[[0,'#2fd06f'],[45,'#63e26a'],[50,'#f7b32b'],[70,'#f58a2a'],[80,'#ff5968'],[100,'#e63946']],hex=h=>[1,3,5].map(i=>parseInt(h.substr(i,2),16));
 const colAt=x=>{let k=1;while(k<stops.length-1&&x>stops[k][0])k++;const a=stops[k-1],b=stops[k],t=Math.min(1,Math.max(0,(x-a[0])/(b[0]-a[0]))),A=hex(a[1]),B=hex(b[1]);return 'rgb('+A.map((c,i)=>Math.round(c+(B[i]-c)*t)).join(',')+')'};
 const col=v>=75?'#ff5968':v>=50?'#ffc65b':'#4cda8a',lvl=v>=75?'HIGH':v>=50?'MEDIUM':'LOW',ang=(v-50)*2.7,hi=v>=75&&!calm;
 let seg='';for(let i=0;i<N;i++){const a=i*100/N,b=Math.min(100,(i+1)*100/N+.35),p=pt(a,r),q=pt(b,r);
  seg+=`<path d="M${p[0]} ${p[1]} A${r} ${r} 0 0 1 ${q[0]} ${q[1]}" fill="none" stroke="${colAt((a+b)/2)}" stroke-width="14" style="${calm?'':`opacity:0;animation:sg .05s ${(i*D/N).toFixed(2)}s forwards`}"/>`}
 let tk='';for(let i=0;i<=50;i++){const x=i*2,m=i%5===0,p=pt(x,102),q=pt(x,m?111:106);tk+=`<line x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}" stroke="#aba49e" stroke-width="${m?1.6:1}" opacity="${m?.9:.5}"/>`}
 const s0=pt(0,r),s1=pt(100,r),l0=pt(0,r+2),l1=pt(100,r+2),F='font-family="Segoe UI,system-ui,sans-serif"';
 setTimeout(()=>{const n=document.getElementById('needle');if(n)n.style.transform=`rotate(${ang}deg)`},60);
 clearInterval(window.gt);
 if(!calm){window.gt=setInterval(()=>{const n=document.getElementById('needle');if(!n){clearInterval(window.gt);return}n.style.transition='transform 1.2s ease-in-out';n.style.transform=`rotate(${ang+(Math.random()-.5)*4}deg)`},1500)}
 const t0=performance.now(),tick=t=>{const k=calm?1:Math.min(1,(t-t0)/(D*1000)),e=1-Math.pow(1-k,3),n=document.getElementById('gnum');if(n)n.textContent=Math.round(v*e);if(k<1)requestAnimationFrame(tick)};requestAnimationFrame(tick);
 return `<div class="gauge"><svg viewBox="0 0 260 260" role="img" aria-label="Risk score ${v} out of 100">
 <defs><radialGradient id="fc" cx="50%" cy="45%" r="60%"><stop offset="0" stop-color="#342e28"/><stop offset="1" stop-color="#181512"/></radialGradient>
 <linearGradient id="rm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e88c46"/><stop offset="1" stop-color="#4da5ff"/></linearGradient>
 <filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
 <circle cx="130" cy="130" r="121" fill="none" stroke="url(#rm)" stroke-width="3" filter="url(#gl)"/><circle cx="130" cy="130" r="116" fill="url(#fc)" stroke="#342e29"/>
 <circle cx="130" cy="130" r="70" fill="none" stroke="#494038" stroke-width="1" opacity=".5"/>
 <path d="M${s0[0]} ${s0[1]} A${r} ${r} 0 1 1 ${s1[0]} ${s1[1]}" fill="none" stroke="#1d1916" stroke-width="18" stroke-linecap="round"/>
 ${seg}${tk}
 <text x="${l0[0]-10}" y="222" fill="#beb9b4" font-size="12" text-anchor="middle" ${F}>0</text><text x="${+l1[0]+10}" y="222" fill="#beb9b4" font-size="12" text-anchor="middle" ${F}>100</text>
 <g stroke="#e88c46" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M122 97 L130 73 L138 97 M125 90 H135 M127 83 H133 M130 73 V69 M119 97 H141"/></g>
 <text x="130" y="113" fill="#beb9b4" font-size="10" letter-spacing="2" text-anchor="middle" ${F}>RISK SCORE</text>
 <text id="gnum" x="130" y="160" fill="${col}" font-size="56" font-weight="700" text-anchor="middle" filter="url(#gl)" ${F}>${calm?v:0}</text>
 <text x="130" y="177" fill="#9a938d" font-size="12" text-anchor="middle" ${F}>/100</text>
 <rect x="84" y="190" width="92" height="24" rx="12" fill="${col}22" stroke="${col}" ${hi?'style="animation:gp 1.8s ease-in-out infinite"':''}/><text x="130" y="206" fill="${col}" font-size="11" font-weight="700" letter-spacing="1.5" text-anchor="middle" ${F}>${lvl} RISK</text>
 <g id="needle" style="transform:rotate(-135deg);transform-origin:130px 130px;transition:transform ${D}s cubic-bezier(.2,.9,.25,1.12)" filter="url(#gl)"><polygon points="128.4,80 131.6,80 130,40" fill="#fbfaf8"/><circle cx="130" cy="41" r="2.6" fill="#fff"/></g></svg></div>`}

const WCOL={'W-125':'#4da5ff','W-107':'#ff5968','W-113':'#ffc65b','W-118':'#f2c94c','W-121':'#a56cf0','W-109':'#4cda8a','W-112':'#d07e40'};
const FORM=[['Top Soil',2000,2350,'#9a8a66'],['Shale',2350,2700,'#6d6f5e'],['Sandstone (XYZ)',2700,3100,'#b3a02e'],['Limestone',3100,3400,'#3b8fd9'],['Basement',3400,3700,'#b03a3a']];
// display-only gentle curvature so paths read as trajectories; events use the same transform so they stay on the line
const disp=(id,p)=>{const sg=id.charCodeAt(id.length-1)%2?1:-1,b=Math.sin((p[2]-2000)/1700*Math.PI)*350*sg;return [p[0]+b,p[1]+b*.5,p[2]]};
const at=(w,z)=>{const P=w.trajectory;let k=P.findIndex(p=>p[2]>=z);if(k<1)k=1;const a=P[k-1],b=P[k],t=(z-a[2])/((b[2]-a[2])||1);return disp(w.well_id,[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,z])};
const box=(x0,x1,y0,y1,z0,z1,c,n)=>({type:'mesh3d',x:[x0,x1,x1,x0,x0,x1,x1,x0],y:[y0,y0,y1,y1,y0,y0,y1,y1],z:[z0,z0,z0,z0,z1,z1,z1,z1],i:[0,0,4,4,0,0,3,3,0,0,1,1],j:[1,2,5,6,1,5,2,6,3,7,2,6],k:[2,3,6,7,5,4,6,7,7,4,6,5],color:c,opacity:.5,flatshading:true,name:n,hoverinfo:'name',showlegend:false});
function fs3d(){const e=Q('#b3d');document.fullscreenElement?document.exitFullscreen():e.requestFullscreen()}
document.addEventListener('fullscreenchange',()=>{Q('#plot3dSub').style.height=document.fullscreenElement?'80vh':'540px';try{Plotly.Plots.resize('plot3dSub')}catch(e){}});
async function draw3dSub(){const d=await api('/api/3d'),ws=d.wells.filter(w=>Math.hypot(w.trajectory[0][0],w.trajectory[0][1])<=6000),tr=[];
 const xs=[],ys=[];ws.forEach(w=>w.trajectory.forEach(p=>{xs.push(p[0]);ys.push(p[1])}));
 const x0=Math.min(...xs)-1200,x1=Math.max(...xs)+1200,y0=Math.min(...ys)-1200,y1=Math.max(...ys)+1200;
 FORM.forEach(l=>tr.push(box(x0,x1,y0,y1,l[1],l[2],l[3],l[0])));
 const lb={x:[],y:[],z:[],t:[],c:[]};
 ws.forEach(w=>{const P=[];for(let z=2000;z<=w.total_depth;z+=25)P.push(at(w,z));if((w.total_depth-2000)%25)P.push(at(w,w.total_depth));
  const c=WCOL[w.well_id]||'#a7a19b',sel=w.well_id===shown,X=P.map(p=>p[0]),Y=P.map(p=>p[1]),Z=P.map(p=>p[2]);
  if(w.active)tr.push({type:'scatter3d',mode:'lines',x:X,y:Y,z:Z,line:{width:16,color:c},opacity:.25,hoverinfo:'skip',showlegend:false});
  tr.push({type:'scatter3d',mode:'lines',name:w.well_id,x:X,y:Y,z:Z,line:{width:w.active?8:sel?9:5,color:c},hovertemplate:w.well_id+' · TD '+w.total_depth+' m<extra></extra>',showlegend:false});
  lb.x.push(X[0]);lb.y.push(Y[0]);lb.z.push(1950);lb.t.push(w.active?w.well_id+'<br>(Active)':w.well_id);lb.c.push(c)});
 tr.push({type:'scatter3d',mode:'text',x:lb.x,y:lb.y,z:lb.z,text:lb.t,textposition:'top center',textfont:{color:lb.c,size:13},hoverinfo:'skip',showlegend:false});
 const ev=d.events.map(e=>({e,w:ws.find(x=>x.well_id===e.well_id)})).filter(o=>o.w&&o.e.depth>=2000&&o.e.depth<=o.w.total_depth),pp=ev.map(o=>at(o.w,o.e.depth));
 tr.push({type:'scatter3d',mode:'markers',name:'Events',x:pp.map(p=>p[0]),y:pp.map(p=>p[1]),z:pp.map(p=>p[2]),text:ev.map(o=>`${o.e.well_id} · ${nice(o.e.event_type)} @ ${o.e.depth} m`),hovertemplate:'%{text}<extra></extra>',marker:{size:6,color:'#ff5968',line:{color:'#fff',width:1}},showlegend:false});
 const a=ws.find(w=>w.active);if(a){const p=at(a,window.LIVE_DEPTH||2810);tr.push({type:'scatter3d',mode:'markers',x:[p[0]],y:[p[1]],z:[p[2]],text:['W-125 current depth'],hovertemplate:'%{text}<extra></extra>',marker:{size:9,color:'#fff',line:{color:'#4da5ff',width:4}},showlegend:false})}
 Plotly.newPlot('plot3dSub',tr,{paper_bgcolor:'rgba(0,0,0,0)',font:{color:'#f3f1ee'},margin:{l:0,r:0,t:0,b:0},showlegend:false,
  scene:{bgcolor:'rgba(0,0,0,0)',xaxis:{visible:false,range:[x0,x1]},yaxis:{visible:false,range:[y0,y1]},zaxis:{range:[3700,1900],title:{text:'Depth (m)'},tickvals:[2000,2500,3000,3500],gridcolor:'#36302a',color:'#beb9b4',showbackground:false},
  aspectmode:'manual',aspectratio:{x:1.3,y:1.1,z:.7},camera:{eye:{x:1.5,y:-1.7,z:.8}}}},{responsive:true,displaylogo:false})}

function fs3d(){const e=Q('#b3d');document.fullscreenElement?document.exitFullscreen():e.requestFullscreen()}
async function initSub(){const w=await api('/api/wells');const s=Q('#sel3');s.innerHTML=w.map(x=>`<option ${x.well_id===shown?'selected':''}>${x.well_id}</option>`).join('');s.onchange=e=>{shown=e.target.value;draw3dSub()};draw3dSub()}
async function clockCtl(o){try{const r=await api('/api/demo/clock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)});toast(o.reset?'Drilling restarted at 2,810 m':r.paused?'Drilling clock paused':'Drilling clock running');refresh()}catch(e){toast(e.message)}}
