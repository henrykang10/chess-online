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
        try:
            cred = credentials.Certificate("firebase_key.json")
        except:
            st.error("Firebase credentials not found. Please check your Secrets or local JSON file.")
            st.stop()
    firebase_admin.initialize_app(cred)

# Get project_id for REST URL
try:
    PROJECT_ID = st.secrets["firebase"]["project_id"]
except Exception:
    try:
        with open("firebase_key.json") as f:
            PROJECT_ID = json.load(f)["project_id"]
    except:
        PROJECT_ID = "your-project-id"

db = firestore.client()
doc_ref = db.collection("games").document("match_1")

# The REST URL used by the Javascript component to pull updates
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
/* Hide scrollbars on mobile to keep it clean */
iframe { border-radius: 8px; overflow: hidden; }
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
st.markdown("<h1 style='text-align:center;color:#e0e0e0;'>♟ Henry's Chessboard</h1>", unsafe_allow_html=True)

# ── 5. Full game component ────────────────────────────────────────────────────
component_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #1a1a2e; color: #e0e0e0;
  font-family: 'Segoe UI', sans-serif;
  display: flex; flex-direction: column; align-items: center;
  padding: 5px 0 20px;
  overflow-x: hidden;
}}
.player-bar {{
  width: 95vw; max-width: 480px;
  display: flex; align-items: center; justify-content: space-between;
  background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
  padding: 6px 12px; margin: 4px 0;
}}
.player-name {{ font-size: 14px; font-weight: 600; color: #e0e0e0; }}
.player-name span {{ font-size: 18px; margin-right: 4px; }}
.clock {{
  font-size: 18px; font-weight: 700; font-family: 'Courier New', monospace;
  color: #e0e0e0; background: #0f3460; padding: 3px 10px;
  border-radius: 6px; min-width: 70px; text-align: center;
}}
.clock.active {{ background: #e94560; color: white; }}
.clock.low    {{ background: #ff0000; animation: pulse 1s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.6}} }}

table {{
  border-collapse: collapse; border: 2px solid #4a3728;
  box-shadow: 0 4px 20px rgba(0,0,0,0.6);
  width: 95vw; max-width: 480px; height: 95vw; max-height: 480px;
}}
td {{
  width: 11.875vw; height: 11.875vw;
  max-width: 60px; max-height: 60px;
  text-align: center; vertical-align: middle;
  font-size: 32px; cursor: pointer; user-select: none;
  position: relative;
}}
@media (min-width: 500px) {{ td {{ font-size: 42px; }} }}

.rank-label, .file-label {{
  position: absolute; font-size: 9px; font-weight: 700; opacity: 0.5; pointer-events: none;
}}
.rank-label {{ top: 2px; left: 3px; }}
.file-label {{ bottom: 1px; right: 3px; }}

#status-bar {{
  width: 95vw; max-width: 480px; text-align: center; padding: 6px; margin: 4px 0;
  background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
  font-size: 14px; font-weight: 600; color: #e0e0e0; min-height: 32px;
}}
#history-wrap {{
  width: 95vw; max-width: 480px; background: #16213e; border: 1px solid #0f3460;
  border-radius: 8px; padding: 8px 12px; margin-top: 4px;
}}
#history-title {{ font-size: 11px; font-weight: 700; color: #e94560; text-transform: uppercase; margin-bottom: 4px; }}
#history-grid {{
  display: grid; grid-template-columns: 25px 1fr 1fr;
  gap: 2px 6px; max-height: 80px; overflow-y: auto; font-size: 12px; font-family: 'Courier New', monospace;
}}
</style>
</head>
<body>

<div class="player-bar">
  <div class="player-name"><span>⬛</span> Opponent</div>
  <div class="clock" id="clock-black">--:--</div>
</div>

<table id="board"></table>

<div class="player-bar">
  <div class="player-name"><span>⬜</span> You</div>
  <div class="clock" id="clock-white">--:--</div>
</div>

<div id="status-bar">Loading…</div>

<div id="history-wrap">
  <div id="history-title">📋 History</div>
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

let chess = new Chess(), sel = null, legalT = new Set(), lastMove = null;
let moveList = [], wTime = INIT_SECONDS, bTime = INIT_SECONDS;
let timerInt = null, lastFen = chess.fen();

const AC = new (window.AudioContext || window.webkitAudioContext)();
function beep(f, d, t="sine", v=0.1) {{
  const o=AC.createOscillator(), g=AC.createGain(); o.connect(g); g.connect(AC.destination);
  o.type=t; o.frequency.value=f; g.gain.setValueAtTime(v, AC.currentTime);
  g.gain.exponentialRampToValueAtTime(0.001, AC.currentTime+d); o.start(); o.stop(AC.currentTime+d);
}}
function playMove()    {{ beep(440,0.08); }}
function playCapture() {{ beep(200,0.1,"sawtooth"); }}
function playCheck()   {{ beep(800,0.15); }}

const sqName = (f,r) => String.fromCharCode(97+f)+(r+1);
const sqIndex = (f,r) => r*8+f;
const formatTime = s => String(Math.floor(Math.max(0,s)/60)).padStart(2,"0")+":"+String(Math.floor(Math.max(0,s)%60)).padStart(2,"0");

function updateClocks() {{
  document.getElementById("clock-white").textContent = formatTime(wTime);
  document.getElementById("clock-black").textContent = formatTime(bTime);
}}

function render() {{
  const table=document.getElementById("board"); table.innerHTML="";
  for(let rank=7;rank>=0;rank--)(function(){{
    const tr=document.createElement("tr");
    for(let file=0;file<8;file++){{
      const sq=sqIndex(file,rank), name=sqName(file,rank), p=chess.get(name), td=document.createElement("td");
      const isLight=(rank+file)%2!==0;
      let bg=isLight?LIGHT:DARK;
      if(lastMove&&(sq===lastMove.from||sq===lastMove.to)) bg=isLight?LAST_W:LAST_D;
      if(sq===sel) bg=SELECT; else if(legalT.has(sq)) bg=LEGAL;
      td.style.background=bg;
      if(p){{
        td.style.color=p.color==="w"?"#fffaf0":"#111";
        td.appendChild(document.createTextNode(ICONS[(p.color==="w"?"w":"b")+p.type.toUpperCase()]));
      }} else if(legalT.has(sq)){{
        const dot=document.createElement("div"); dot.style.cssText="width:12px;height:12px;border-radius:50%;background:rgba(0,0,0,0.15);margin:auto;";
        td.appendChild(dot);
      }}
      td.onclick = () => onSquareClick(sq, name);
      tr.appendChild(td);
    }}
    table.appendChild(tr);
  }})();
  updateClocks();
}}

function isMyTurn() {{ return (chess.turn()==="w"&&ROLE==="White")||(chess.turn()==="b"&&ROLE==="Black"); }}

async function onSquareClick(sq, name) {{
  if(AC.state==="suspended") AC.resume();
  if(chess.game_over() || !isMyTurn()) return;
  const p=chess.get(name);
  if(sel===null) {{
    if(!p || p.color!==(ROLE==="White"?"w":"b")) return;
    sel=sq;
    legalT=new Set(chess.moves({{square:name,verbose:true}}).map(m=>(parseInt(m.to[1])-1)*8+(m.to.charCodeAt(0)-97)));
  }} else {{
    if(sq===sel){{ sel=null; legalT=new Set(); render(); return; }}
    const result=chess.move({{from:sqName(sel%8,Math.floor(sel/8)), to:name, promotion:"q"}});
    if(result){{
      lastMove={{from:sel,to:sq}}; moveList.push(result.san);
      saveFen(chess.fen());
      result.captured ? playCapture() : (chess.in_check() ? playCheck() : playMove());
    }}
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
  if(isMyTurn() && sel !== null) return;
  try {{
    const data=await(await fetch(REST_URL)).json();
    const fen=data?.fields?.fen?.stringValue;
    if(fen&&fen!==lastFen){{
      lastFen=fen; chess.load(fen);
      const h=chess.history({{verbose:true}});
      if(h.length>0){{
        const last=h[h.length-1];
        lastMove={{from:(parseInt(last.from[1])-1)*8+(last.from.charCodeAt(0)-97), to:(parseInt(last.to[1])-1)*8+(last.to.charCodeAt(0)-97)}};
      }}
      if(!isMyTurn()) playMove();
      render();
    }}
  }}catch(e){{}}
}}

setInterval(loadFen, 1500);
loadFen().then(render);
</script>
</body>
</html>"""

components.html(component_html, height=720, scrolling=False)
