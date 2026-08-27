from __future__ import annotations

GLOBAL_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&family=Playfair+Display:wght@700&display=swap');

:root {
  --night: #07110f;
  --panel: #0d1c18;
  --panel-2: #11251f;
  --gold: #dcbf73;
  --gold-soft: #f4dfab;
  --cream: #f7f1df;
  --muted: #a5b6ae;
  --line: rgba(220,191,115,.22);
  --green: #2e8b68;
  --red: #c85f5f;
}

html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 12% 0%, rgba(31,104,77,.22), transparent 32rem),
    radial-gradient(circle at 88% 12%, rgba(167,130,44,.10), transparent 28rem),
    var(--night);
  color: var(--cream);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stSidebar"] { background: #081612; border-right: 1px solid var(--line); }
.block-container { max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem; }
.block-container:has(.st-key-check_in_kiosk),
.block-container:has(.st-key-board_podium) { max-width: 1520px; }

h1, h2, h3 { color: var(--cream) !important; letter-spacing: -.02em; }
p, label, .stCaption { color: #d9e2de; }

.brand-kicker {
  color: var(--gold); font-size: .78rem; font-weight: 800; letter-spacing: .24em;
  text-transform: uppercase; margin-bottom: .55rem;
}
.hero-title {
  font-family: 'Playfair Display', 'Noto Sans KR', serif;
  color: var(--cream); font-size: clamp(2.5rem, 7vw, 5.6rem); line-height: .98;
  max-width: 920px; margin: 0; letter-spacing: -.045em;
}
.hero-subtitle { color: var(--muted); max-width: 720px; font-size: 1.05rem; margin-top: 1rem; }
.gold-rule { height: 1px; background: linear-gradient(90deg,var(--gold),transparent); margin: 1.5rem 0 2rem; }
.safe-pill {
  display: inline-flex; gap: .45rem; align-items: center; color: var(--gold-soft);
  border: 1px solid var(--line); background: rgba(220,191,115,.07);
  border-radius: 999px; padding: .42rem .72rem; font-size: .78rem; font-weight: 700;
}

.mode-card, .panel-card, .ticket-card {
  border: 1px solid var(--line); border-radius: 20px;
  background: linear-gradient(145deg, rgba(18,43,35,.94), rgba(8,24,20,.96));
  box-shadow: 0 18px 50px rgba(0,0,0,.20); padding: 1.35rem;
}
.mode-card { min-height: 158px; margin-bottom: .6rem; }
.mode-num { color: var(--gold); font-family: 'Playfair Display', serif; font-size: 1rem; }
.mode-title { color: var(--cream); font-size: 1.15rem; font-weight: 800; margin: .55rem 0 .35rem; }
.mode-copy { color: var(--muted); font-size: .88rem; line-height: 1.65; }

.ticket-card {
  background: radial-gradient(circle at 80% 0%, rgba(220,191,115,.13), transparent 45%), #0c211b;
  position: relative; overflow: hidden; padding: 2rem;
}
.ticket-card:after {
  content: ''; position: absolute; inset: 12px; border: 1px dashed rgba(220,191,115,.35);
  border-radius: 14px; pointer-events: none;
}
.ticket-code {
  color: #fff0a8; font: 700 clamp(4.5rem, 17vw, 8.5rem)/.95 'Playfair Display', serif;
  letter-spacing: .16em; margin: .7rem 0 .45rem; text-align: center;
  text-shadow: 0 0 32px rgba(220,191,115,.35);
}
.ticket-label { color: var(--muted); font-size: .78rem; letter-spacing: .16em; text-transform: uppercase; }
.ticket-memory-label {
  display: inline-block; color: #102018; background: linear-gradient(135deg,#f1dc95,#c49c3c);
  border-radius: 999px; padding: .5rem .9rem; margin-top: .8rem;
  font-size: .9rem; font-weight: 900; letter-spacing: .08em;
}
.ticket-memory-title { color: var(--cream); font-size: clamp(1.25rem,3vw,1.9rem); font-weight: 900; text-align: center; }
.ticket-memory-copy { color: #e3cf91; font-size: 1.05rem; font-weight: 700; text-align: center; margin-top: .45rem; }

.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: .8rem; margin: 1rem 0 1.6rem; }
.metric-card {
  background: rgba(14,35,29,.88); border: 1px solid var(--line); border-radius: 18px;
  padding: 1rem 1.1rem;
}
.metric-label { color: var(--muted); font-size: .78rem; font-weight: 700; }
.metric-value { color: var(--cream); font: 700 2rem/1.2 'Playfair Display', serif; margin-top: .25rem; }
.metric-accent { color: var(--gold-soft); }

.podium-shell {
  margin: 1.5rem 0 2.4rem; padding: 1.6rem 1.5rem 0;
  border: 1px solid rgba(220,191,115,.28); border-radius: 28px;
  background:
    radial-gradient(circle at 50% 8%, rgba(220,191,115,.16), transparent 34%),
    linear-gradient(155deg, rgba(16,42,34,.98), rgba(5,18,15,.98));
  box-shadow: 0 28px 80px rgba(0,0,0,.34), inset 0 1px rgba(255,255,255,.04);
  overflow: hidden; position: relative; isolation: isolate;
}
.podium-shell:before {
  content: ''; position: absolute; inset: -60% -30%; z-index: -1;
  background: linear-gradient(105deg,transparent 40%,rgba(255,235,166,.09) 48%,rgba(255,255,255,.16) 50%,rgba(255,235,166,.09) 52%,transparent 60%);
  transform: translateX(-55%); animation: podiumShine 6s ease-in-out infinite;
}
.podium-stage-glow {
  position: absolute; width: 44%; height: 190px; left: 28%; top: 8px; z-index: -1;
  border-radius: 50%; background: rgba(255,213,88,.14); filter: blur(42px);
  animation: stageGlow 2.8s ease-in-out infinite;
}
.podium-title {
  color: var(--gold); text-align: center; font-size: .8rem; font-weight: 800;
  letter-spacing: .22em; margin-bottom: 1.4rem; position: relative; z-index: 2;
}
.podium-title span { color: #fff0a8; text-shadow: 0 0 18px rgba(255,220,109,.5); }
.podium-sparkle {
  position: absolute; color: #ffe595; z-index: 3; pointer-events: none;
  text-shadow: 0 0 15px rgba(255,226,133,.9); animation: sparkle 2.4s ease-in-out infinite;
}
.sparkle-1 { left: 8%; top: 16%; font-size: 1.25rem; }
.sparkle-2 { right: 10%; top: 10%; font-size: 1.6rem; animation-delay: -.8s; }
.sparkle-3 { left: 25%; top: 35%; font-size: .95rem; animation-delay: -1.5s; }
.sparkle-4 { right: 25%; top: 32%; font-size: 1.1rem; animation-delay: -.35s; }
.podium-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 1rem;
  align-items: end; max-width: 900px; margin: 0 auto; position: relative; z-index: 2;
}
.podium-place { min-width: 0; text-align: center; animation: podiumFloat 3.4s ease-in-out infinite; }
.podium-1 { animation-delay: -.7s; }
.podium-3 { animation-delay: -1.4s; }
.podium-medal {
  font-size: clamp(2rem, 4vw, 3.2rem); filter: drop-shadow(0 8px 16px rgba(0,0,0,.28));
  animation: medalGlow 2.6s ease-in-out infinite;
}
.winner-crown {
  height: 42px; color: #ffe486; font: 700 clamp(2.4rem,5vw,4rem)/1 'Playfair Display',serif;
  text-shadow: 0 0 14px rgba(255,223,112,.85),0 0 32px rgba(255,197,56,.45);
  animation: crownHover 2s ease-in-out infinite;
}
.winner-ribbon {
  display: inline-block; color: #1a231c; background: linear-gradient(90deg,#b68a26,#ffeb99,#b68a26);
  border-radius: 999px; padding: .28rem .7rem; margin: .2rem 0 .35rem;
  font-size: .67rem; font-weight: 900; letter-spacing: .14em;
}
.podium-name {
  color: var(--cream); font-size: clamp(.95rem, 2vw, 1.35rem); font-weight: 800;
  margin-top: .4rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.podium-id { color: var(--muted); font-size: .8rem; font-weight: 800; letter-spacing: .12em; margin-top: .25rem; }
.podium-points { color: var(--gold-soft); font: 700 clamp(1.15rem, 3vw, 1.9rem)/1.2 'Playfair Display', serif; margin: .4rem 0 .85rem; }
.podium-step {
  display: flex; align-items: flex-start; justify-content: center; padding-top: 1rem;
  border: 1px solid rgba(255,255,255,.11); border-bottom: 0; border-radius: 16px 16px 0 0;
  box-shadow: inset 0 1px rgba(255,255,255,.1), 0 -10px 32px rgba(0,0,0,.14);
  position: relative; overflow: hidden;
}
.podium-step:after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(115deg,transparent 20%,rgba(255,255,255,.22) 43%,transparent 60%);
  transform: translateX(-120%); animation: stepShimmer 4.8s ease-in-out infinite;
}
.podium-step span { font: 700 clamp(2.1rem, 5vw, 4.2rem)/1 'Playfair Display', serif; }
.podium-1 .podium-step { height: 190px; background: linear-gradient(180deg,#c7a74e,#71591c); color:#fff4bf; }
.podium-2 .podium-step { height: 132px; background: linear-gradient(180deg,#aeb9bd,#596468); color:#f4f8f9; }
.podium-3 .podium-step { height: 94px; background: linear-gradient(180deg,#a96d46,#5e3625); color:#ffe0ca; }
.podium-1 .podium-name { color: #fff2b6; font-size: clamp(1.1rem, 2.3vw, 1.55rem); }
.podium-1 .podium-points { text-shadow: 0 0 24px rgba(220,191,115,.35); }

@keyframes podiumShine { 0%,28% { transform:translateX(-55%); } 70%,100% { transform:translateX(55%); } }
@keyframes stageGlow { 0%,100% { opacity:.55; transform:scale(.92); } 50% { opacity:1; transform:scale(1.08); } }
@keyframes sparkle { 0%,100% { opacity:.2; transform:scale(.65) rotate(0); } 50% { opacity:1; transform:scale(1.3) rotate(35deg); } }
@keyframes podiumFloat { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-4px); } }
@keyframes medalGlow { 0%,100% { filter:drop-shadow(0 8px 16px rgba(0,0,0,.28)); } 50% { filter:drop-shadow(0 0 18px rgba(255,224,128,.55)); } }
@keyframes crownHover { 0%,100% { transform:translateY(0) rotate(-2deg); } 50% { transform:translateY(-6px) rotate(2deg); } }
@keyframes stepShimmer { 0%,42% { transform:translateX(-120%); } 72%,100% { transform:translateX(120%); } }

.rank-row {
  display: grid; grid-template-columns: 48px minmax(0,1fr) 110px; align-items: center;
  padding: .78rem .25rem; border-bottom: 1px solid rgba(220,191,115,.12);
}
.rank-number { color: var(--gold); font: 700 1.15rem 'Playfair Display', serif; }
.rank-name { color: var(--cream); font-weight: 700; }
.rank-code { color: var(--muted); font-size: .78rem; }
.rank-points { color: var(--gold-soft); text-align: right; font-weight: 800; }
.live-dot { width: 8px; height: 8px; display: inline-block; border-radius: 50%; background: #5be39f; box-shadow: 0 0 0 5px rgba(91,227,159,.1); margin-right: .55rem; }

.person-strip {
  border: 1px solid var(--line); border-radius: 16px; padding: 1rem 1.1rem;
  background: rgba(11,30,25,.75); margin: .45rem 0 1rem;
}
.person-name { color: var(--cream); font-size: 1.15rem; font-weight: 800; }
.person-meta { color: var(--muted); font-size: .82rem; margin-top: .25rem; }
.balance { color: var(--gold-soft); font: 700 1.45rem 'Playfair Display', serif; }

[data-testid="stForm"] { background: rgba(13,32,27,.72); border: 1px solid var(--line); border-radius: 20px; padding: 1.2rem; }
[data-baseweb="input"] > div, [data-baseweb="select"] > div, [data-baseweb="textarea"] > div {
  background-color: #0e231d !important; border-color: rgba(220,191,115,.22) !important;
}
input, textarea { color: var(--cream) !important; }
[data-baseweb="popover"], [role="listbox"] { background: #10271f !important; }

.st-key-check_in_kiosk [data-testid="stForm"] {
  padding: .8rem 0 0; border: 0; border-radius: 0; background: transparent;
  box-shadow: none;
}
.st-key-kiosk_guest_card, .st-key-kiosk_access_card {
  min-height: 350px; padding: 1.7rem 2rem 1.9rem; position: relative; overflow: hidden;
  border: 1px solid rgba(220,191,115,.3); border-radius: 24px;
  background:
    radial-gradient(circle at 92% 0%, rgba(220,191,115,.12), transparent 42%),
    linear-gradient(145deg, rgba(17,42,34,.94), rgba(8,24,20,.96));
  box-shadow: 0 24px 65px rgba(0,0,0,.2), inset 0 1px rgba(255,255,255,.04);
}
.st-key-kiosk_guest_card:before, .st-key-kiosk_access_card:before {
  content: ''; position: absolute; width: 140px; height: 1px; right: 0; top: 0;
  background: linear-gradient(90deg,transparent,#f1d98f);
}
.kiosk-section-kicker {
  color: var(--gold); font-size: .7rem; font-weight: 900; letter-spacing: .2em;
  margin-bottom: .35rem;
}
.kiosk-section-title { color: var(--cream); font-size: 1.35rem; font-weight: 900; }
.kiosk-section-copy { color: var(--muted); font-size: .86rem; margin: .25rem 0 1.15rem; }
.st-key-kiosk_guest_card [data-testid="stVerticalBlock"],
.st-key-kiosk_access_card [data-testid="stVerticalBlock"] { gap: .72rem; }
.st-key-check_in_kiosk [data-baseweb="input"] > div {
  min-height: 62px; border-radius: 14px;
  background: rgba(5,20,16,.68) !important; transition: border-color .2s ease, box-shadow .2s ease;
}
.st-key-check_in_kiosk [data-baseweb="input"] > div:focus-within {
  border-color: rgba(244,223,171,.72) !important;
  box-shadow: 0 0 0 3px rgba(220,191,115,.09), 0 10px 28px rgba(0,0,0,.16);
}
.st-key-check_in_kiosk label p, .st-key-check_in_kiosk [data-testid="stWidgetLabel"] p {
  color: var(--cream) !important; font-size: 1rem !important; font-weight: 800 !important;
}
.st-key-check_in_kiosk input {
  min-height: 60px; padding: .75rem 1rem !important; font-size: 1.18rem !important; font-weight: 700;
}
.st-key-check_in_kiosk [data-testid="stNumberInput"] button { min-height: 34px; min-width: 42px; }
.st-key-check_in_kiosk [data-testid="stRadio"] { padding: .7rem 0 1rem; }
.st-key-check_in_kiosk [data-testid="stRadio"] label { font-size: 1.15rem; margin-right: 1.4rem; }
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] { margin-top: 1rem; }
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] button {
  min-height: 64px; position: relative; overflow: hidden; isolation: isolate;
  border: 1px solid rgba(220,191,115,.58) !important; border-radius: 16px;
  background:
    radial-gradient(circle at 50% -90%,rgba(244,223,171,.2),transparent 65%),
    linear-gradient(135deg,#173b31 0%,#0d2922 55%,#132f27 100%) !important;
  color: var(--cream) !important; font-size: 1.12rem; letter-spacing: .08em;
  box-shadow: 0 16px 38px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.08);
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease, color .2s ease;
}
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] button:before {
  content: ''; position: absolute; inset: 0; z-index: -1; opacity: 0;
  background: linear-gradient(110deg,transparent 18%,rgba(244,223,171,.13) 48%,transparent 78%);
  transform: translateX(-35%); transition: opacity .2s ease, transform .45s ease;
}
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] button:hover {
  transform: translateY(-2px); border-color: rgba(244,223,171,.9) !important;
  background:
    radial-gradient(circle at 50% -70%,rgba(244,223,171,.26),transparent 68%),
    linear-gradient(135deg,#1b473a 0%,#103128 55%,#17382e 100%) !important;
  color: #fff6d9 !important;
  box-shadow: 0 20px 46px rgba(0,0,0,.32), 0 0 0 3px rgba(220,191,115,.08),
    inset 0 1px rgba(255,255,255,.12);
}
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] button:hover:before {
  opacity: 1; transform: translateX(35%);
}
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] button:active {
  transform: translateY(0); box-shadow: 0 10px 24px rgba(0,0,0,.28), inset 0 2px 8px rgba(0,0,0,.18);
}
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] button:focus-visible {
  outline: 3px solid rgba(244,223,171,.28); outline-offset: 3px;
}
.st-key-check_in_kiosk [data-testid="stFormSubmitButton"] button p {
  color: inherit !important; font-weight: 900; letter-spacing: inherit;
}

.st-key-board_podium .podium-shell { margin: 1rem 0 1.2rem; }
.st-key-board_ranking { margin-top: 1rem; }
.ranking-heading {
  min-height: 88px; display: flex; flex-direction: column; justify-content: center;
  padding: 1rem 1.2rem; border: 1px solid rgba(220,191,115,.3); border-bottom: 0;
  border-radius: 22px 22px 0 0;
  background: radial-gradient(circle at 100% 0%,rgba(220,191,115,.14),transparent 48%),rgba(13,32,27,.92);
}
.ranking-heading span { color: var(--gold); font-size: .68rem; font-weight: 900; letter-spacing: .2em; }
.ranking-heading strong { color: var(--cream); font-size: 1.35rem; margin-top: .18rem; }
.st-key-board_ranking .panel-card {
  max-height: 480px; overflow-y: auto; margin: 0; padding: .35rem 1rem .55rem;
  border-radius: 0 0 22px 22px; box-shadow: 0 24px 65px rgba(0,0,0,.2);
  scrollbar-width: thin; scrollbar-color: rgba(220,191,115,.42) rgba(5,18,15,.45);
}
.st-key-board_ranking .rank-row { grid-template-columns: 42px minmax(0,1fr) 92px; padding: .72rem .15rem; }
.st-key-board_ranking .rank-number { font-size: 1rem; }
.st-key-board_ranking .rank-points { font-size: .92rem; }

.quick-guide {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  color: var(--muted); border: 1px solid var(--line); border-radius: 15px;
  background: rgba(220,191,115,.06); padding: .8rem 1rem; margin-bottom: .8rem;
}
.quick-guide strong { color: var(--cream); }
.quick-guide b { color: var(--gold-soft); font-size: 1.05rem; }
.quick-result {
  border-radius: 16px; padding: 1rem 1.15rem; margin: .75rem 0;
  font-size: 1.05rem; font-weight: 800; letter-spacing: .01em;
}
.quick-result.success { color: #baf5d5; border: 1px solid rgba(91,227,159,.35); background: rgba(42,128,91,.2); }
.quick-result.error { color: #ffd0d0; border: 1px solid rgba(200,95,95,.45); background: rgba(139,44,44,.2); }

.st-key-operator_gate {
  max-width: 580px; margin: 2.2rem auto 0; padding: 1.5rem;
  border: 1px solid rgba(220,191,115,.3); border-radius: 22px;
  background: radial-gradient(circle at 100% 0%,rgba(220,191,115,.12),transparent 48%),rgba(13,32,27,.92);
  box-shadow: 0 24px 65px rgba(0,0,0,.24), inset 0 1px rgba(255,255,255,.04);
}
.operator-gate-copy { color: var(--muted); text-align: center; margin: 0 0 1rem; }
.st-key-operator_gate [data-testid="stForm"] { padding: 0; border: 0; background: transparent; }
.st-key-operator_gate [data-baseweb="input"] > div { min-height: 58px; border-radius: 14px; }
.st-key-operator_gate input { min-height: 56px; font-size: 1.1rem !important; text-align: center; }

.checkout-hero {
  margin: 1.4rem 0 1.2rem; padding: 1.8rem 2rem; border-radius: 24px;
  border: 1px solid rgba(232,114,91,.42);
  background: radial-gradient(circle at 90% 0%,rgba(232,114,91,.18),transparent 45%),
    linear-gradient(145deg,rgba(59,29,25,.96),rgba(26,15,14,.98));
  box-shadow: 0 24px 65px rgba(0,0,0,.24), inset 0 1px rgba(255,255,255,.04);
}
.checkout-kicker { color:#ff9b83; font-size:.72rem; font-weight:900; letter-spacing:.2em; }
.checkout-title { color:#fff0eb; font-size:clamp(2.2rem,6vw,4.2rem); font-weight:900; margin:.3rem 0; }
.checkout-copy { color:#d7aaa0; font-size:1rem; }
.st-key-checkout_station {
  max-width: 720px; margin: 1.6rem auto; padding: 1.4rem;
  border: 1px solid rgba(232,114,91,.34); border-radius: 22px;
  background: rgba(47,25,22,.9); box-shadow: 0 20px 55px rgba(0,0,0,.22);
}
.st-key-checkout_station [data-baseweb="input"],
.st-key-checkout_station [data-baseweb="input"] > div,
.st-key-checkout_station [data-baseweb="base-input"] {
  min-height: 104px; border-radius: 16px; border-color: rgba(255,155,131,.48) !important;
  background: #261714 !important;
}
.st-key-checkout_station input {
  height:104px !important; min-height:104px; padding:1rem 1.25rem !important;
  box-sizing:border-box; overflow:visible; line-height:1.2 !important;
  color:#ffd4c8 !important; font-size:3rem !important; font-weight:900;
  letter-spacing:.16em; text-align:center; text-transform:uppercase;
}
.checkout-confirm-card {
  margin: 1rem 0; padding: 1.2rem; text-align:center; border-radius:18px;
  border:1px solid rgba(255,155,131,.3); background:rgba(255,155,131,.07);
}
.checkout-confirm-label { color:#d7aaa0; font-size:.76rem; font-weight:800; letter-spacing:.12em; }
.checkout-confirm-name { color:#fff0eb; font-size:1.7rem; font-weight:900; margin:.35rem 0; }
.checkout-confirm-meta { color:#ffb29f; font-weight:800; }
.st-key-checkout_station .stButton > button[kind="primary"] {
  background:linear-gradient(135deg,#ef8c72,#b34b3c); color:#fff; border:0;
}

.st-key-analytics_gate {
  max-width:580px; margin:2rem auto; padding:1.5rem; border-radius:22px;
  border:1px solid rgba(94,180,221,.34);
  background:radial-gradient(circle at 100% 0%,rgba(94,180,221,.13),transparent 48%),rgba(12,30,34,.94);
  box-shadow:0 24px 65px rgba(0,0,0,.24),inset 0 1px rgba(255,255,255,.04);
}
.analytics-gate-copy { color:#aac7d1; text-align:center; margin-bottom:1rem; }
.st-key-analytics_gate [data-testid="stForm"] { padding:0; border:0; background:transparent; }
.analytics-panel {
  border:1px solid rgba(94,180,221,.22); border-radius:20px; padding:1rem 1.1rem;
  background:linear-gradient(145deg,rgba(13,37,40,.94),rgba(8,24,27,.96));
  box-shadow:0 18px 48px rgba(0,0,0,.18);
}
.analytics-empty { color:var(--muted); padding:1.4rem; text-align:center; }
.hour-row { display:grid; grid-template-columns:58px minmax(0,1fr) 44px; gap:.75rem; align-items:center; margin:.75rem 0; }
.hour-label,.hour-count { color:#b9d2d7; font-size:.82rem; font-weight:800; }
.hour-count { text-align:right; }
.hour-track { height:13px; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; }
.hour-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#3a8baa,#83d5e2); }
.category-panel { min-height:160px; display:flex; flex-direction:column; justify-content:center; }
.category-summary,.category-percent { display:flex; justify-content:space-between; gap:1rem; color:#c8dcdf; }
.category-summary strong { color:#f2fbfc; margin-left:.25rem; }
.category-dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:.35rem; }
.general-dot,.category-general { background:#4aa8c2; }
.vip-dot,.category-vip { background:#d8b65e; }
.category-track { display:flex; height:22px; overflow:hidden; border-radius:999px; margin:1.2rem 0 .55rem; background:rgba(255,255,255,.05); }
.category-percent { color:#8fabb0; font-size:.78rem; font-weight:800; }
.visit-list { padding:.3rem 1rem; }
.visit-row {
  display:grid; grid-template-columns:minmax(150px,1.1fr) minmax(150px,1fr) 90px 72px;
  gap:1rem; align-items:center; padding:.9rem .2rem; border-bottom:1px solid rgba(94,180,221,.12);
}
.visit-row:last-child { border-bottom:0; }
.visit-name { color:var(--cream); font-weight:900; }
.visit-meta,.visit-time { color:#95afb4; font-size:.78rem; }
.visit-time { display:flex; flex-direction:column; gap:.18rem; }
.visit-duration { color:#c9e7eb; font-weight:800; text-align:right; }
.visit-status { padding:.32rem .55rem; border-radius:999px; text-align:center; font-size:.72rem; font-weight:900; }
.visit-status.active { color:#aaf0cf; background:rgba(51,151,105,.18); }
.visit-status.exited { color:#b8c5c8; background:rgba(126,143,148,.15); }

.stButton > button, .stDownloadButton > button, .stLinkButton > a {
  border-radius: 12px; min-height: 2.75rem; font-weight: 800;
  border: 1px solid rgba(220,191,115,.4); background: rgba(220,191,115,.08); color: var(--gold-soft);
}
.stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
  border-color: var(--gold); background: rgba(220,191,115,.16); color: #fff6d9;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: linear-gradient(135deg,#d9bb6b,#a88333); color: #101914; border: none;
}
[data-testid="stAlert"] { border-radius: 14px; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }

.footer-note { color: #71847b; font-size: .73rem; text-align: center; margin-top: 3rem; }
@media (max-width: 760px) {
  .block-container { padding: 1.2rem 1rem 3rem; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .hero-title { font-size: 2.65rem; }
  .podium-shell { padding: 1.2rem .6rem 0; }
  .podium-grid { gap: .35rem; }
  .podium-1 .podium-step { height: 150px; }
  .podium-2 .podium-step { height: 105px; }
  .podium-3 .podium-step { height: 75px; }
  .quick-guide { align-items: flex-start; flex-direction: column; }
  .st-key-kiosk_guest_card, .st-key-kiosk_access_card { min-height: auto; padding: 1.35rem; }
  .st-key-check_in_kiosk input { font-size: 1.15rem !important; }
  .checkout-hero { padding:1.35rem; }
  .st-key-checkout_station [data-baseweb="input"],
  .st-key-checkout_station [data-baseweb="input"] > div,
  .st-key-checkout_station [data-baseweb="base-input"] { min-height:84px; }
  .st-key-checkout_station input {
    height:84px !important; min-height:84px; font-size:2.1rem !important;
  }
  .visit-row { grid-template-columns:1fr auto; gap:.55rem; }
  .visit-time { grid-column:1/2; }
  .visit-duration { grid-column:2/3; grid-row:2; }
}
@media (max-width: 1050px) {
  [data-testid="stHorizontalBlock"]:has(.st-key-board_podium) { flex-direction: column; }
  [data-testid="stHorizontalBlock"]:has(.st-key-board_podium) > [data-testid="stColumn"] {
    width: 100% !important; flex: 1 1 100% !important;
  }
  .st-key-board_ranking .panel-card { max-height: 420px; }
}
@media (prefers-reduced-motion: reduce) {
  .podium-shell:before, .podium-stage-glow, .podium-sparkle, .podium-place,
  .podium-medal, .winner-crown, .podium-step:after { animation: none !important; }
}
</style>
"""
