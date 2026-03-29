import streamlit as st
import streamlit.components.v1 as components
import chess
import firebase_admin
from firebase_admin import credentials, firestore
import json

# ── 1. SETUP ──────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Henry's Chess Board", layout="centered")

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

with open("firebase_key.json") as f:
    svc = json.load(f)
PROJECT_ID = svc["project_id"]

db = firestore.client()
doc_ref = db.collection("games").document("match_1")

FIREBASE_REST = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/games/match_1"

# ── 2. Dark mode CSS for Streamlit shell ──────────────────────────────────────
st.markdown("""
<style>
/* Dark background for entire app */
[data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #1a1a2e !important;
}
[data-testid="stSidebar"] {
    background-color: #16213e !important;
}
[data-testid="stSidebar"] * {
    color: #e0e0e0 !important;
}
h1, h2, h3, p, label { color: #e0e0e0 !important; }
.stRadio label { color: #ccc !important; }
.stButton > button {
    background: #0f3460 !important;
    color: #e0e0e0 !important;
    border: 1px solid #e94560 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background: #e94560 !important;
    color: white !important;
}
[data-testid="stInfo"] {
    background: #0f3460 !important;
    border: 1px solid #e94560 !important;
    color: #ccc !important;
}
</style>
""", unsafe_allow_html=True)

# ── 3. Sidebar ────────────────────────────────────────────────────────────────
st.sidebar.markdown("## ♟ Play Chess with Henry")
st.sidebar.markdown("---")
role = st.sidebar.radio("**Playing as**", ["White", "Black", "Spectator"])
st.sidebar.markdown("---")

# Timer duration
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
st.sidebar.info("Select black if you're not Henry.")

# ── 4. Main area ──────────────────────────────────────────────────────────────
st.markdown(f"<h1 style='text-align:center;color:#e0e0e0;'>Henry's Chessboard</h1>", unsafe_allow_html=True)

# ── 5. The full game component ────────────────────────────────────────────────
component_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/chess.js/0.10.3/chess.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #1a1a2e;
  color: #e0e0e0;
  font-family: 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0 20px;
}}

/* ── Player bars ── */
.player-bar {{
  width: 496px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 8px 14px;
  margin: 6px 0;
}}
.player-name {{
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
}}
.player-name span {{ font-size: 20px; margin-right: 6px; }}
.clock {{
  font-size: 22px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #e0e0e0;
  background: #0f3460;
  padding: 4px 12px;
  border-radius: 6px;
  min-width: 80px;
  text-align: center;
  transition: background 0.3s;
}}
.clock.active {{ background: #e94560; color: white; }}
.clock.low    {{ background: #ff0000; color: white; animation: pulse 1s infinite; }}
@keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.6}} }}

/* ── Board ── */
#board-wrap {{
  position: relative;
  margin: 4px 0;
}}
table {{
  border-collapse: collapse;
  border: 3px solid #4a3728;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  border-radius: 2px;
}}
td {{
  width: 62px; height: 62px;
  text-align: center; vertical-align: middle;
  font-size: 42px; line-height: 62px;
  cursor: pointer; user-select: none;
  transition: filter 0.08s;
  position: relative;
}}
td:hover {{ filter: brightness(0.82); }}
.rank-label {{
  position: absolute;
  top: 2px; left: 3px;
  font-size: 10px;
  font-weight: 700;
  opacity: 0.6;
  pointer-events: none;
}}
.file-label {{
  position: absolute;
  bottom: 1px; right: 3px;
  font-size: 10px;
  font-weight: 700;
  opacity: 0.6;
  pointer-events: none;
}}

/* ── Status bar ── */
#status-bar {{
  width: 496px;
  text-align: center;
  padding: 8px;
  margin: 6px 0;
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
  min-height: 38px;
}}

/* ── Move history ── */
#history-wrap {{
  width: 496px;
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 10px 14px;
  margin-top: 8px;
}}
#history-title {{
  font-size: 12px;
  font-weight: 700;
  color: #e94560;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 8px;
}}
#history-grid {{
  display: grid;
  grid-template-columns: 30px 1fr 1fr;
  gap: 2px 8px;
  max-height: 150px;
  overflow-y: auto;
  font-size: 13px;
  font-family: 'Courier New', monospace;
}}
#history-grid::-webkit-scrollbar {{ width: 4px; }}
#history-grid::-webkit-scrollbar-thumb {{ background: #0f3460; border-radius: 2px; }}
.move-num {{ color: #888; }}
.move-w   {{ color: #f0d9b5; cursor: default; }}
.move-b   {{ color: #b8860b; cursor: default; }}
.move-latest {{ background: #0f3460; border-radius: 3px; padding: 0 3px; }}
</style>
</head>
<body>

<!-- Black player bar (top) -->
<div class="player-bar">
  <div class="player-name"><span>⬛</span> Opponent (Black)</div>
  <div class="clock" id="clock-black">--:--</div>
</div>

<!-- Board -->
<div id="board-wrap"><table id="board"></table></div>

<!-- White player bar (bottom) -->
<div class="player-bar">
  <div class="player-name"><span>⬜</span> You (White)</div>
  <div class="clock" id="clock-white">--:--</div>
</div>

<!-- Status -->
<div id="status-bar">Loading…</div>

<!-- Move history -->
<div id="history-wrap">
  <div id="history-title">📋 Move History</div>
  <div id="history-grid" id="history"></div>
</div>

<script>
const ROLE         = "{role}";
const REST_URL     = "{FIREBASE_REST}";
const INIT_SECONDS = {timer_minutes} * 60;

// ── Colors ────────────────────────────────────────────────────────────────────
const LIGHT  = "#f0d9b5";
const DARK   = "#b58863";
const SELECT = "#f6f669";
const LEGAL  = "#cdd16e";
const LAST_W = "#cdd26a";   // last move highlight
const LAST_D = "#aaa23a";

const ICONS = {{
  wP:"♙",wR:"♖",wN:"♘",wB:"♗",wQ:"♕",wK:"♔",
  bP:"♟",bR:"♜",bN:"♞",bB:"♝",bQ:"♛",bK:"♚"
}};

let chess     = new Chess();
let sel       = null;
let legalT    = new Set();
let lastMove  = null;   // {{from, to}} square indices
let moveList  = [];     // SAN strings
let wTime     = INIT_SECONDS;
let bTime     = INIT_SECONDS;
let timerInt  = null;
let lastFen   = chess.fen();

// ── Sound (Web Audio API) ─────────────────────────────────────────────────────
const AC = new (window.AudioContext || window.webkitAudioContext)();

function beep(freq, dur, type="sine", vol=0.15) {{
  const o = AC.createOscillator();
  const g = AC.createGain();
  o.connect(g); g.connect(AC.destination);
  o.type = type; o.frequency.value = freq;
  g.gain.setValueAtTime(vol, AC.currentTime);
  g.gain.exponentialRampToValueAtTime(0.001, AC.currentTime + dur);
  o.start(); o.stop(AC.currentTime + dur);
}}

function playMove()    {{ beep(440, 0.08); setTimeout(()=>beep(600,0.06),80); }}
function playCapture() {{ beep(200, 0.12, "sawtooth", 0.2); }}
function playCheck()   {{ beep(880, 0.15); setTimeout(()=>beep(660,0.1),100); }}
function playEnd()     {{ [523,659,784,1047].forEach((f,i)=>setTimeout(()=>beep(f,0.2),i*120)); }}
function playIllegal() {{ beep(150, 0.1, "square", 0.1); }}

// ── Helpers ───────────────────────────────────────────────────────────────────
function sqName(file, rank) {{
  return String.fromCharCode(97+file) + (rank+1);
}}
function sqIndex(file, rank) {{ return rank * 8 + file; }}

function formatTime(s) {{
  if (s < 0) s = 0;
  const m = Math.floor(s/60);
  const sec = Math.floor(s%60);
  return String(m).padStart(2,"0") + ":" + String(sec).padStart(2,"0");
}}

function updateClocks() {{
  const wb = document.getElementById("clock-white");
  const bb = document.getElementById("clock-black");
  wb.textContent = formatTime(wTime);
  bb.textContent = formatTime(bTime);

  const isWT = chess.turn() === "w";
  wb.className = "clock" + (isWT && !chess.game_over() ? " active" : "") + (wTime<=10 && isWT?" low":"");
  bb.className = "clock" + (!isWT && !chess.game_over() ? " active" : "") + (bTime<=10 && !isWT?" low":"");
}}

function startTimer() {{
  stopTimer();
  if (chess.game_over()) return;
  timerInt = setInterval(() => {{
    if (chess.turn() === "w") wTime--; else bTime--;
    if (wTime <= 0 || bTime <= 0) {{
      stopTimer();
      playEnd();
      document.getElementById("status-bar").textContent =
        wTime <= 0 ? "⏱ White out of time — Black wins!" : "⏱ Black out of time — White wins!";
    }}
    updateClocks();
  }}, 1000);
}}

function stopTimer() {{
  if (timerInt) {{ clearInterval(timerInt); timerInt = null; }}
}}

// ── Move history ──────────────────────────────────────────────────────────────
function rebuildHistory() {{
  const grid = document.getElementById("history-grid");
  grid.innerHTML = "";
  for (let i = 0; i < moveList.length; i += 2) {{
    const num = document.createElement("div");
    num.className = "move-num";
    num.textContent = (i/2+1) + ".";
    grid.appendChild(num);

    const wm = document.createElement("div");
    wm.className = "move-w" + (i===moveList.length-1?" move-latest":"");
    wm.textContent = moveList[i];
    grid.appendChild(wm);

    const bm = document.createElement("div");
    bm.className = "move-b" + (i+1===moveList.length-1?" move-latest":"");
    bm.textContent = moveList[i+1] || "";
    grid.appendChild(bm);
  }}
  grid.scrollTop = grid.scrollHeight;
}}

// ── Render board ──────────────────────────────────────────────────────────────
function render() {{
  const table = document.getElementById("board");
  table.innerHTML = "";

  for (let rank = 7; rank >= 0; rank--) {{
    const tr = document.createElement("tr");
    for (let file = 0; file < 8; file++) {{
      const sq   = sqIndex(file, rank);
      const name = sqName(file, rank);
      const p    = chess.get(name);
      const td   = document.createElement("td");

      const isLight = (rank + file) % 2 !== 0;
      let bg = isLight ? LIGHT : DARK;

      // Last move highlight
      if (lastMove && (sq===lastMove.from || sq===lastMove.to)) {{
        bg = isLight ? LAST_W : LAST_D;
      }}
      if (sq === sel)          bg = SELECT;
      else if (legalT.has(sq)) bg = LEGAL;

      td.style.background = bg;

      // Rank label (left column only)
      if (file === 0) {{
        const rl = document.createElement("div");
        rl.className = "rank-label";
        rl.textContent = rank+1;
        rl.style.color = isLight ? DARK : LIGHT;
        td.appendChild(rl);
      }}
      // File label (bottom row only)
      if (rank === 0) {{
        const fl = document.createElement("div");
        fl.className = "file-label";
        fl.textContent = String.fromCharCode(97+file);
        fl.style.color = isLight ? DARK : LIGHT;
        td.appendChild(fl);
      }}

      if (p) {{
        const key = (p.color==="w"?"w":"b") + p.type.toUpperCase();
        td.style.color      = p.color==="w" ? "#fffaf0" : "#111";
        td.style.textShadow = p.color==="w" ? "1px 1px 3px rgba(0,0,0,0.6)" : "none";
        if (legalT.has(sq)) td.style.boxShadow = "inset 0 0 0 5px rgba(0,0,0,0.3)";
        const txt = document.createTextNode(ICONS[key]);
        td.appendChild(txt);
      }} else if (legalT.has(sq)) {{
        const dot = document.createElement("div");
        dot.style.cssText = "width:20px;height:20px;border-radius:50%;background:rgba(0,0,0,0.22);margin:auto;pointer-events:none;";
        td.appendChild(dot);
      }}

      td.dataset.sq   = sq;
      td.dataset.name = name;
      td.addEventListener("click", onSquareClick);
      tr.appendChild(td);
    }}
    table.appendChild(tr);
  }}

  // Status bar
  const sb = document.getElementById("status-bar");
  if (chess.in_checkmate()) {{
    sb.textContent = chess.turn()==="w" ? "🏆 Black wins by checkmate!" : "🏆 White wins by checkmate!";
    stopTimer(); playEnd();
  }} else if (chess.in_draw()) {{
    sb.textContent = "🤝 Draw — " + (chess.in_stalemate()?"Stalemate":chess.in_threefold_repetition()?"Threefold Repetition":"50-move rule");
    stopTimer(); playEnd();
  }} else {{
    const turn = chess.turn()==="w" ? "⬜ White to move" : "⬛ Black to move";
    sb.textContent = turn + (chess.in_check() ? " — ⚠️ Check!" : "");
  }}

  updateClocks();
  rebuildHistory();
}}

// ── Click handler ─────────────────────────────────────────────────────────────
function isMyTurn() {{
  if (ROLE==="Spectator") return false;
  return (chess.turn()==="w" && ROLE==="White") ||
         (chess.turn()==="b" && ROLE==="Black");
}}

function onSquareClick(e) {{
  if (AC.state === "suspended") AC.resume();
  if (chess.game_over()) return;
  const sq   = parseInt(this.dataset.sq);
  const name = this.dataset.name;
  const p    = chess.get(name);

  if (sel === null) {{
    if (!isMyTurn()) return;
    if (!p) return;
    const mine = (p.color==="w" && ROLE==="White") || (p.color==="b" && ROLE==="Black");
    if (!mine) return;
    sel = sq;
    legalT = new Set(
      chess.moves({{square:name, verbose:true}}).map(m => {{
        const f = m.to.charCodeAt(0)-97;
        const r = parseInt(m.to[1])-1;
        return r*8+f;
      }})
    );
  }} else {{
    if (sq === sel) {{
      sel=null; legalT=new Set(); render(); return;
    }}
    const fromName = sqName(sel%8, Math.floor(sel/8));
    let moveObj = {{from:fromName, to:name}};
    const srcP = chess.get(fromName);
    if (srcP && srcP.type==="p" && (name[1]==="8"||name[1]==="1")) moveObj.promotion="q";

    const wasCapture = !!chess.get(name);
    const result = chess.move(moveObj);

    if (result) {{
      lastMove = {{ from: sel, to: sq }};
      moveList.push(result.san);

      if (chess.in_checkmate())   playEnd();
      else if (chess.in_check())  playCheck();
      else if (wasCapture)        playCapture();
      else                        playMove();

      saveFen(chess.fen());
      startTimer();
    }} else {{
      playIllegal();
    }}
    sel=null; legalT=new Set();
  }}
  render();
}}

// ── Firebase REST ─────────────────────────────────────────────────────────────
async function saveFen(fen) {{
  await fetch(REST_URL + "?updateMask.fieldPaths=fen", {{
    method: "PATCH",
    headers: {{"Content-Type":"application/json"}},
    body: JSON.stringify({{ fields: {{ fen: {{ stringValue: fen }} }} }})
  }});
}}

async function loadFen() {{
  try {{
    const res  = await fetch(REST_URL);
    const data = await res.json();
    const fen  = data?.fields?.fen?.stringValue;
    if (fen && fen !== lastFen) {{
      lastFen = fen;
      const prevMoveCount = chess.history().length;
      chess.load(fen);
      const newMoves = chess.history();

      // Sync move list from history if opponent moved
      if (newMoves.length > moveList.length) {{
        const newSAN = newMoves.slice(moveList.length);
        newSAN.forEach(m => moveList.push(m));

        // Reconstruct lastMove from history
        const tmp = new Chess();
        newMoves.slice(0,-1).forEach(m => tmp.move(m));
        const lastResult = tmp.move(newMoves[newMoves.length-1]);
        if (lastResult) {{
          const tf = lastResult.to.charCodeAt(0)-97;
          const tr = parseInt(lastResult.to[1])-1;
          const ff = lastResult.from.charCodeAt(0)-97;
          const fr = parseInt(lastResult.from[1])-1;
          lastMove = {{ from: fr*8+ff, to: tr*8+tf }};
        }}

        if (chess.in_checkmate()) playEnd();
        else if (chess.in_check()) playCheck();
        else if (lastResult && lastResult.captured) playCapture();
        else playMove();

        sel=null; legalT=new Set();
        startTimer();
        render();
      }}
    }}
  }} catch(e) {{}}
}}

// ── Init ──────────────────────────────────────────────────────────────────────
wTime = INIT_SECONDS;
bTime = INIT_SECONDS;
loadFen().then(() => {{ render(); startTimer(); }});
setInterval(loadFen, 1500);
</script>
</body>
</html>
"""

components.html(component_html, height=780, scrolling=False)