"""Deterministic live telemetry simulator with controllable SIH demo scenarios."""
import time, math
SCENARIO="NORMAL"
START=time.monotonic(); BASE_DEPTH=2810.0
RATE=0.25; PAUSED=False; _D=[BASE_DEPTH,time.monotonic()]
def _advance():
    now=time.monotonic()
    if not PAUSED: _D[0]+=(now-_D[1])*RATE
    _D[1]=now
    if _D[0]>3310: _D[0]=BASE_DEPTH
    return _D[0]
def set_clock(paused=None,reset=False):
    global PAUSED,START
    _advance()
    if paused=="toggle": PAUSED=not PAUSED
    elif isinstance(paused,bool): PAUSED=paused
    if reset: _D[0]=BASE_DEPTH; START=time.monotonic()
    return {"paused":PAUSED,"depth":round(_D[0],1)}

def set_scenario(name):
    global SCENARIO, START
    SCENARIO=name; START=time.monotonic(); _D[0]=BASE_DEPTH; _D[1]=time.monotonic()

def get_scenario(): return SCENARIO

def telemetry():
    t=time.monotonic()-START; depth=_advance(); phase=t/18
    rop=25+2.4*math.sin(phase)+0.8*math.sin(phase*2.7); wob=12+0.6*math.sin(phase*0.8); rpm=110+5*math.sin(phase*1.3)
    torque=18.5+2.2*math.sin(phase*1.7)+max(0,rop-26)*.9; pressure=285+4*math.sin(phase*.6)+max(0,depth-2830)*.02; flow=540+8*math.sin(phase*.9); mud=1.20+0.008*math.sin(phase*.45)
    status="DRILLING"
    if SCENARIO=="MUD_LOSS": flow-=65; pressure-=18; mud-=.025; status="MUD LOSS SIMULATION"
    elif SCENARIO=="STUCK_PIPE": torque+=11; rop=max(4,rop-16); wob+=2; status="STUCK PIPE SIMULATION"
    elif SCENARIO=="OVERPRESSURE": pressure+=48; mud+=.045; status="OVERPRESSURE SIMULATION"
    elif SCENARIO=="TORQUE_SPIKE": torque+=15; rpm-=12; status="TORQUE SPIKE SIMULATION"
    return {"timestamp":time.time(),"depth":round(depth,1),"rop":round(rop,2),"wob":round(wob,2),"rpm":round(rpm,1),"torque":round(torque,2),"pressure":round(pressure,1),"flow_rate":round(flow,1),"mud_weight":round(mud,3),"status":status,"paused":PAUSED,"connection_state":"LIVE SIMULATION","source":"synthetic telemetry"}
