import streamlit as st
import streamlit.components.v1 as components
import chess
import firebase_admin
from firebase_admin import credentials, firestore
import json

# ── 1. SETUP — works both locally (firebase_key.json) and on Streamlit Cloud (st.secrets) ──
st.set_page_config(page_title="♟ Henry's Chessboard", layout="centered")

if not firebase_admin._apps:
    try:
        # Streamlit Cloud: read from secrets
        key_dict = dict(st.secrets["firebase"])
        # private_key newlines are escaped in TOML — fix them
        key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(key_dict)
    except (KeyError, FileNotFoundError):
        # Local: read from file
        cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

# Get project_id for REST URL
try:
    PROJECT_ID = st.secrets["firebase"]["project_id"]
except Exception:
    with open("firebase_key.json") as f:
        PROJECT_ID = json.load(f)["project_id"]

db = firestore.client()
doc_ref = db.collection("games").document("match_1")

FIREBASE_REST = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/games/match_1"

# ── 2. Dark mode CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #1a1a2e !important;
}
[data-testid="stSidebar"] { background-color: #16213e !important; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
h1, h2, h3, p, label { color: #e0e0e0 !important; }
.stButton > button {
    background: #0f3460 !important; color: #e0e0e0 !important;
    border: 1px solid #e94560 !important; border-radius: 6px !important;
    font-weight: 600 !important;
}
.stButton > button:hover { background: #e94560 !important; color: white !important; }
[data-testid="stInfo"] {
    background: #0f3460 !important; border: 1px solid #e94560 !important; color: #ccc !important;
}
</style>
""", unsafe_allow_html=True)

# ── 3. Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.markdown("## Play Chess with Henry")
st.sidebar.markdown("---")
role = st.sidebar.radio("**Playing as**", ["White", "Black", "Spectator"])
st.sidebar.markdown("---")
timer_minutes = st.sidebar.selectbox("⏱ Clock (minutes)", [1, 3, 5, 10, 15, 30], index=2)
st.sidebar.markdown("---")
if st.sidebar.button("🔄 New Game"):
    doc_ref.set({
        "fen": chess.STARTING_FEN,
        "white_time": timer_minutes * 60,
        "black_time": timer_minutes * 60,
        "last_tick": 0
    })
    st.rerun()
st.sidebar.markdown("---")
st.sidebar.info("Share this page with your opponent. They select **Black**.")

# ── 4. Title ──────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center;color:#e0e0e0;'>♟ Play Chess with Henry</h1>", unsafe_allow_html=True)

# ── 5. Full game component ────────────────────────────────────────────────────
component_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #1a1a2e; color: #e0e0e0;
  font-family: 'Segoe UI', sans-serif;
  display: flex; flex-direction: column; align-items: center;
  padding: 10px 0 20px;
}}
.player-bar {{
  width: 496px; display: flex; align-items: center;
  justify-content: space-between; background: #16213e;
  border: 1px solid #0f3460; border-radius: 8px;
  padding: 8px 14px; margin: 6px 0;
}}
.player-name {{ font-size: 15px; font-weight: 600; color: #e0e0e0; }}
.player-name span {{ font-size: 20px; margin-right: 6px; }}
.clock {{
  font-size: 22px; font-weight: 700; font-family: 'Courier New', monospace;
  color: #e0e0e0; background: #0f3460; padding: 4px 12px;
  border-radius: 6px; min-width: 80px; text-align: center; transition: background 0.3s;
}}
.clock.active {{ background: #e94560; color: white; }}
.clock.low    {{ background: #ff0000; color: white; animation: pulse 1s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.6}} }}
table {{
  border-collapse: collapse; border: 3px solid #4a3728;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6); border-radius: 2px;
}}
td {{
  width: 62px; height: 62px; text-align: center; vertical-align: middle;
  font-size: 42px; line-height: 62px; cursor: pointer; user-select: none;
  transition: filter 0.08s; position: relative;
}}
td:hover {{ filter: brightness(0.82); }}
.rank-label {{
  position: absolute; top: 2px; left: 3px;
  font-size: 10px; font-weight: 700; opacity: 0.6; pointer-events: none;
}}
.file-label {{
  position: absolute; bottom: 1px; right: 3px;
  font-size: 10px; font-weight: 700; opacity: 0.6; pointer-events: none;
}}
#status-bar {{
  width: 496px; text-align: center; padding: 8px; margin: 6px 0;
  background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
  font-size: 15px; font-weight: 600; color: #e0e0e0; min-height: 38px;
}}
#history-wrap {{
  width: 496px; background: #16213e; border: 1px solid #0f3460;
  border-radius: 8px; padding: 10px 14px; margin-top: 8px;
}}
#history-title {{
  font-size: 12px; font-weight: 700; color: #e94560;
  letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;
}}
#history-grid {{
  display: grid; grid-template-columns: 30px 1fr 1fr;
  gap: 2px 8px; max-height: 150px; overflow-y: auto;
  font-size: 13px; font-family: 'Courier New', monospace;
}}
#history-grid::-webkit-scrollbar {{ width: 4px; }}
#history-grid::-webkit-scrollbar-thumb {{ background: #0f3460; border-radius: 2px; }}
.move-num {{ color: #888; }}
.move-w   {{ color: #f0d9b5; }}
.move-b   {{ color: #b8860b; }}
.move-latest {{ background: #0f3460; border-radius: 3px; padding: 0 3px; }}
</style>
</head>
<body>

<div class="player-bar">
  <div class="player-name"><span>⬛</span> Opponent (Black)</div>
  <div class="clock" id="clock-black">--:--</div>
</div>

<table id="board"></table>

<div class="player-bar">
  <div class="player-name"><span>⬜</span> You (White)</div>
  <div class="clock" id="clock-white">--:--</div>
</div>

<div id="status-bar">Loading…</div>

<div id="history-wrap">
  <div id="history-title">📋 Move History</div>
  <div id="history-grid"></div>
</div>

<script>
const ROLE         = "{role}";
const REST_URL     = "{FIREBASE_REST}";
const INIT_SECONDS = {timer_minutes} * 60;

const LIGHT  = "#f0d9b5", DARK = "#b58863";
const SELECT = "#f6f669", LEGAL = "#cdd16e";
const LAST_W = "#cdd26a", LAST_D = "#aaa23a";

const ICONS = {{
  wP:"♙",wR:"♖",wN:"♘",wB:"♗",wQ:"♕",wK:"♔",
  bP:"♟",bR:"♜",bN:"♞",bB:"♝",bQ:"♛",bK:"♚"
}};

let chess    = new Chess();
let sel      = null, legalT = new Set(), lastMove = null;
let moveList = [], wTime = INIT_SECONDS, bTime = INIT_SECONDS;
let timerInt = null, lastFen = chess.fen();

// ── Sound ─────────────────────────────────────────────────────────────────────
const AC = new (window.AudioContext || window.webkitAudioContext)();
function beep(freq, dur, type="sine", vol=0.15) {{
  const o = AC.createOscillator(), g = AC.createGain();
  o.connect(g); g.connect(AC.destination);
  o.type = type; o.frequency.value = freq;
  g.gain.setValueAtTime(vol, AC.currentTime);
  g.gain.exponentialRampToValueAtTime(0.001, AC.currentTime + dur);
  o.start(); o.stop(AC.currentTime + dur);
}}
function playMove()    {{ beep(440,0.08); setTimeout(()=>beep(600,0.06),80); }}
function playCapture() {{ beep(200,0.12,"sawtooth",0.2); }}
function playCheck()   {{ beep(880,0.15); setTimeout(()=>beep(660,0.1),100); }}
function playEnd()     {{ [523,659,784,1047].forEach((f,i)=>setTimeout(()=>beep(f,0.2),i*120)); }}
function playIllegal() {{ beep(150,0.1,"square",0.1); }}

// ── Helpers ───────────────────────────────────────────────────────────────────
const sqName  = (f,r) => String.fromCharCode(97+f)+(r+1);
const sqIndex = (f,r) => r*8+f;
const formatTime = s => {{
  s = Math.max(0,s);
  return String(Math.floor(s/60)).padStart(2,"0")+":"+String(Math.floor(s%60)).padStart(2,"0");
}};

function updateClocks() {{
  const wb = document.getElementById("clock-white");
  const bb = document.getElementById("clock-black");
  wb.textContent = formatTime(wTime);
  bb.textContent = formatTime(bTime);
  const isWT = chess.turn()==="w" && !chess.game_over();
  wb.className = "clock"+(isWT?" active":"")+(wTime<=10&&isWT?" low":"");
  bb.className = "clock"+(!isWT&&!chess.game_over()?" active":"")+(bTime<=10&&!isWT?" low":"");
}}

function startTimer() {{
  stopTimer();
  if (chess.game_over()) return;
  timerInt = setInterval(()=>{{
    if(chess.turn()==="w") wTime--; else bTime--;
    if(wTime<=0||bTime<=0) {{
      stopTimer(); playEnd();
      document.getElementById("status-bar").textContent =
        wTime<=0?"⏱ White out of time — Black wins!":"⏱ Black out of time — White wins!";
    }}
    updateClocks();
  }},1000);
}}
function stopTimer() {{ if(timerInt){{clearInterval(timerInt);timerInt=null;}} }}

function rebuildHistory() {{
  const grid = document.getElementById("history-grid");
  grid.innerHTML = "";
  for(let i=0;i<moveList.length;i+=2) {{
    const n=document.createElement("div"); n.className="move-num"; n.textContent=(i/2+1)+"."; grid.appendChild(n);
    const w=document.createElement("div"); w.className="move-w"+(i===moveList.length-1?" move-latest":""); w.textContent=moveList[i]; grid.appendChild(w);
    const b=document.createElement("div"); b.className="move-b"+(i+1===moveList.length-1?" move-latest":""); b.textContent=moveList[i+1]||""; grid.appendChild(b);
  }}
  grid.scrollTop=grid.scrollHeight;
}}

function render() {{
  const table=document.getElementById("board");
  table.innerHTML="";
  for(let rank=7;rank>=0;rank--){{
    const tr=document.createElement("tr");
    for(let file=0;file<8;file++){{
      const sq=sqIndex(file,rank), name=sqName(file,rank);
      const p=chess.get(name), td=document.createElement("td");
      const isLight=(rank+file)%2!==0;
      let bg=isLight?LIGHT:DARK;
      if(lastMove&&(sq===lastMove.from||sq===lastMove.to)) bg=isLight?LAST_W:LAST_D;
      if(sq===sel) bg=SELECT; else if(legalT.has(sq)) bg=LEGAL;
      td.style.background=bg;

      if(file===0){{ const rl=document.createElement("div"); rl.className="rank-label"; rl.textContent=rank+1; rl.style.color=isLight?DARK:LIGHT; td.appendChild(rl); }}
      if(rank===0){{ const fl=document.createElement("div"); fl.className="file-label"; fl.textContent=String.fromCharCode(97+file); fl.style.color=isLight?DARK:LIGHT; td.appendChild(fl); }}

      if(p){{
        const key=(p.color==="w"?"w":"b")+p.type.toUpperCase();
        td.style.color=p.color==="w"?"#fffaf0":"#111";
        td.style.textShadow=p.color==="w"?"1px 1px 3px rgba(0,0,0,0.6)":"none";
        if(legalT.has(sq)) td.style.boxShadow="inset 0 0 0 5px rgba(0,0,0,0.3)";
        td.appendChild(document.createTextNode(ICONS[key]));
      }} else if(legalT.has(sq)){{
        const dot=document.createElement("div");
        dot.style.cssText="width:20px;height:20px;border-radius:50%;background:rgba(0,0,0,0.22);margin:auto;pointer-events:none;";
        td.appendChild(dot);
      }}
      td.dataset.sq=sq; td.dataset.name=name;
      td.addEventListener("click",onSquareClick);
      tr.appendChild(td);
    }}
    table.appendChild(tr);
  }}

  const sb=document.getElementById("status-bar");
  if(chess.in_checkmate()) {{ sb.textContent=chess.turn()==="w"?"🏆 Black wins by checkmate!":"🏆 White wins by checkmate!"; stopTimer(); playEnd(); }}
  else if(chess.in_draw()) {{ sb.textContent="🤝 Draw!"; stopTimer(); playEnd(); }}
  else {{ sb.textContent=(chess.turn()==="w"?"⬜ White to move":"⬛ Black to move")+(chess.in_check()?" — ⚠️ Check!":""); }}

  updateClocks(); rebuildHistory();
}}

function isMyTurn() {{
  if(ROLE==="Spectator") return false;
  return (chess.turn()==="w"&&ROLE==="White")||(chess.turn()==="b"&&ROLE==="Black");
}}

function onSquareClick() {{
  if(AC.state==="suspended") AC.resume();
  if(chess.game_over()) return;
  const sq=parseInt(this.dataset.sq), name=this.dataset.name, p=chess.get(name);

  if(sel===null) {{
    if(!isMyTurn()||!p) return;
    const mine=(p.color==="w"&&ROLE==="White")||(p.color==="b"&&ROLE==="Black");
    if(!mine) return;
    sel=sq;
    legalT=new Set(chess.moves({{square:name,verbose:true}}).map(m=>{{
      return (parseInt(m.to[1])-1)*8+(m.to.charCodeAt(0)-97);
    }}));
  }} else {{
    if(sq===sel){{ sel=null;legalT=new Set();render();return; }}
    const fromName=sqName(sel%8,Math.floor(sel/8));
    let mv={{from:fromName,to:name}};
    const srcP=chess.get(fromName);
    if(srcP&&srcP.type==="p"&&(name[1]==="8"||name[1]==="1")) mv.promotion="q";
    const wasCapture=!!chess.get(name);
    const result=chess.move(mv);
    if(result){{
      lastMove={{from:sel,to:sq}}; moveList.push(result.san);
      if(chess.in_checkmate()) playEnd();
      else if(chess.in_check()) playCheck();
      else if(wasCapture) playCapture();
      else playMove();
      saveFen(chess.fen()); startTimer();
    }} else playIllegal();
    sel=null; legalT=new Set();
  }}
  render();
}}

async function saveFen(fen) {{
  await fetch(REST_URL+"?updateMask.fieldPaths=fen",{{
    method:"PATCH", headers:{{"Content-Type":"application/json"}},
    body:JSON.stringify({{fields:{{fen:{{stringValue:fen}}}}}})
  }});
}}

async function loadFen() {{
  try {{
    const data=await(await fetch(REST_URL)).json();
    const fen=data?.fields?.fen?.stringValue;
    if(fen&&fen!==lastFen){{
      lastFen=fen; chess.load(fen);
      const newMoves=chess.history();
      if(newMoves.length>moveList.length){{
        const tmp=new Chess();
        newMoves.slice(0,-1).forEach(m=>tmp.move(m));
        const lr=tmp.move(newMoves[newMoves.length-1]);
        if(lr){{
          lastMove={{from:(parseInt(lr.from[1])-1)*8+(lr.from.charCodeAt(0)-97),
                    to:(parseInt(lr.to[1])-1)*8+(lr.to.charCodeAt(0)-97)}};
          if(newMoves.length>moveList.length) moveList=newMoves.slice();
          if(chess.in_checkmate()) playEnd();
          else if(chess.in_check()) playCheck();
          else if(lr.captured) playCapture();
          else playMove();
        }}
        sel=null;legalT=new Set();startTimer();render();
      }}
    }}
  }}catch(e){{}}
}}

wTime=INIT_SECONDS; bTime=INIT_SECONDS;
loadFen().then(()=>{{render();startTimer();}});
setInterval(loadFen,1500);
</script>
</body>
</html>"""

components.html(component_html, height=780, scrolling=False)
