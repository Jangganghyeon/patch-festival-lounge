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
.ticket-code { color: var(--gold-soft); font: 700 clamp(2rem, 8vw, 4.4rem)/1 'Playfair Display', serif; letter-spacing: .13em; }
.ticket-label { color: var(--muted); font-size: .78rem; letter-spacing: .16em; text-transform: uppercase; }

.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: .8rem; margin: 1rem 0 1.6rem; }
.metric-card {
  background: rgba(14,35,29,.88); border: 1px solid var(--line); border-radius: 18px;
  padding: 1rem 1.1rem;
}
.metric-label { color: var(--muted); font-size: .78rem; font-weight: 700; }
.metric-value { color: var(--cream); font: 700 2rem/1.2 'Playfair Display', serif; margin-top: .25rem; }
.metric-accent { color: var(--gold-soft); }

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
}
</style>
"""
