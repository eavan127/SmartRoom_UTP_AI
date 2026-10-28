"""SmartRoom UTP - IRC smart locker kiosk (Streamlit prototype).

Run: streamlit run app/kiosk.py
Layout (every screen):  top bar  |  step tracker  |  main task (left, 2/3) + booking panel (right, 1/3)  |  action bar
"""
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import card_log  # noqa: E402
from src.matcher import CONFIG, Verification  # noqa: E402

st.set_page_config(page_title="SmartRoom UTP | IRC Kiosk", page_icon="🔑", layout="wide",
                   initial_sidebar_state="collapsed")

BOOKINGS = json.loads((ROOT / "mock" / "bookings.json").read_text())["bookings"]
STEPS = ["Choose booking", "Face scan", "Locker", "Done"]
PAGE_STEP = {"select": 0, "scan": 1, "result": 2, "done": 3}

# ---------------------------------------------------------------- styling
# Colours taken from ulibrary.utp.edu.my: navy logo/menu, deep navy footer,
# gold ChatBot tab, sage-green pill buttons, cream panels, light-grey page.
CSS = """
<style>
:root{
  --navy:#324773; --navy-deep:#061E2F; --gold:#C48D0C; --gold-soft:#EDCF89;
  --sage:#749082; --sage-dark:#4F6B5D; --cream:#EBE3C7; --cream-soft:#F6F2E4;
  --bg:#F3F3F3; --ink:#212529; --muted:#5E5E5E; --danger:#A8322D; --danger-soft:#F7E3E1;
  --radius:14px;
}
html, body, [data-testid="stAppViewContainer"]{background:var(--bg); color:var(--ink);
  font-family:"Segoe UI", Segoe, Tahoma, Helvetica, Arial, sans-serif;}
[data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu,
[data-testid="stSidebarCollapsedControl"]{display:none !important;}
.block-container{padding:0 2rem 7.5rem 2rem !important; max-width:none !important;}

/* ---- top bar ---- */
.stApp, .stMarkdown, .stButton p, input, textarea{font-family:"Segoe UI", Segoe, Tahoma, Helvetica, Arial, sans-serif !important;}
/* full-bleed bar: cancel the page's 2rem side padding so it lines up at any width */
.st-key-topbar{background:#fff; margin:0 -2rem !important; width:calc(100% + 4rem) !important;
  max-width:none !important; padding:.75rem 2rem 0 2rem; gap:.75rem !important;
  box-shadow:0 2px 8px rgba(0,0,0,.06);}
.st-key-topbar [data-testid="stHorizontalBlock"]{align-items:center; gap:.75rem;}
.st-key-topbar .stButton > button{min-height:2.75rem; font-size:.95rem; padding:0 1rem; white-space:nowrap;}
.st-key-home_btn button{border-color:var(--navy); color:var(--navy);}
.st-key-home_btn button:disabled{border-color:#ddd; color:#aaa; background:#fafafa;}
.st-key-staff_btn button{border-color:#c9c9c9; color:var(--muted);}
.st-key-exit_staff_btn button{background:var(--gold); border-color:var(--gold); color:#fff;}
.st-key-exit_staff_btn button:hover{background:#a87806; border-color:#a87806; color:#fff;}
.brand{display:flex; align-items:center; gap:14px;}
.brand .mark{font-family:Georgia,"Times New Roman",serif; font-size:2.4rem; color:var(--navy);
  line-height:1; letter-spacing:1px; padding-left:12px; border-left:6px solid var(--gold);}
.brand .txt b{display:block; color:var(--navy); font-size:1.05rem; letter-spacing:.5px;}
.brand .txt span{color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:1px;}
.clock{text-align:right; color:var(--navy); line-height:1.25; white-space:nowrap;}
.clock b{font-size:1.45rem;} .clock span{font-size:.8rem; color:var(--muted);}

/* ---- step tracker ---- */
.steps{display:flex; gap:0; margin:1.1rem 0 1rem 0; background:#fff; border-radius:var(--radius);
  overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.06);}
.step{flex:1; padding:.7rem 1rem; text-align:center; color:var(--muted); font-weight:600;
  font-size:.95rem; border-right:1px solid #e6e6e6;}
.step:last-child{border-right:none;}
.step .n{display:inline-flex; width:26px; height:26px; border-radius:50%; align-items:center;
  justify-content:center; margin-right:8px; background:#e3e3e3; color:#555; font-size:.85rem;}
.step.done{color:var(--sage-dark);} .step.done .n{background:var(--sage); color:#fff;}
.step.now{background:var(--navy); color:#fff;} .step.now .n{background:var(--gold); color:#fff;}

/* ---- cards ---- */
.card{background:#fff; border-radius:var(--radius); padding:1.2rem 1.4rem; margin-bottom:1rem;
  box-shadow:0 1px 4px rgba(0,0,0,.07);}
.card h3{margin:0 0 .4rem 0; color:var(--navy); font-size:1.2rem;}
.card .sub{color:var(--muted); font-size:.92rem;}
.panel-title{background:var(--cream); color:var(--navy-deep); font-weight:700; letter-spacing:.5px;
  text-transform:uppercase; font-size:.8rem; padding:.55rem 1rem; border-radius:10px 10px 0 0;
  margin:-1.2rem -1.4rem 1rem -1.4rem;}
.title{color:var(--navy); font-size:1.9rem; font-weight:700; margin:.2rem 0 .1rem 0;}
.lead{color:var(--muted); font-size:1.05rem; margin-bottom:1rem;}
.badge{display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:700;}
.b-now{background:var(--sage); color:#fff;} .b-next{background:var(--gold-soft); color:#5a4100;}
.b-out{background:var(--navy); color:#fff;} .b-end{background:#ddd; color:#555;}
.member{display:flex; justify-content:space-between; align-items:center; padding:.55rem .2rem;
  border-bottom:1px dashed #e3e3e3; font-size:1rem;}
.member:last-child{border-bottom:none;}
.member .who{display:flex; align-items:center; gap:10px;}
.av{width:30px; height:30px; border-radius:50%; background:var(--navy); color:#fff; font-weight:700;
  display:inline-flex; align-items:center; justify-content:center; font-size:.85rem;}
.av.ok{background:var(--sage);}
.chip{padding:3px 12px; border-radius:999px; font-size:.8rem; font-weight:700;}
.c-ok{background:#E3EDE7; color:var(--sage-dark);} .c-wait{background:#EEE; color:#666;}
.progress{height:10px; border-radius:6px; background:#e6e6e6; overflow:hidden; margin:.4rem 0 .2rem;}
.progress > div{height:100%; background:var(--sage);}
.msg{border-radius:12px; padding:.9rem 1.1rem; font-size:1.05rem; margin:.6rem 0; font-weight:600;}
.m-ok{background:#E3EDE7; color:var(--sage-dark); border-left:6px solid var(--sage);}
.m-bad{background:var(--danger-soft); color:var(--danger); border-left:6px solid var(--danger);}
.m-info{background:var(--cream-soft); color:#5a4100; border-left:6px solid var(--gold);}
.hero{background:linear-gradient(120deg,var(--navy-deep) 0%,var(--navy) 100%); color:#fff;
  border-radius:var(--radius); padding:2rem 2.2rem; margin-bottom:1.2rem;}
.hero h1{margin:0; font-size:2.2rem; color:#fff;} .hero p{margin:.4rem 0 0 0; color:#dfe6f3; font-size:1.1rem;}
/* mode strip: bottom edge of the top bar (gold = simulation, navy = staff mode) */
.mode{color:#fff; text-align:center; font-weight:700; font-size:.78rem; letter-spacing:1px;
  padding:4px; margin:0 -2rem; text-transform:uppercase; background:var(--gold);}
.mode.staff{background:var(--navy);} .mode.plain{padding:0; height:4px;}
.howto{counter-reset:s; list-style:none; padding:0; margin:0;}
.howto li{counter-increment:s; display:flex; gap:12px; margin:.55rem 0; align-items:flex-start;}
.howto li:before{content:counter(s); flex:0 0 28px; height:28px; border-radius:50%; background:var(--navy);
  color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700;}
.camframe{height:44vh; min-height:280px; background:radial-gradient(circle at 50% 45%,#2c3e5c 0%,#0b1a2a 75%);
  border-radius:var(--radius); display:flex; align-items:center; justify-content:center; position:relative;}
.camframe .lbl{position:absolute; bottom:14px; color:#cfd8e6; font-size:.95rem;}

/* ---- buttons ---- */
.stButton > button{border-radius:999px; font-weight:700; font-size:1.05rem; min-height:3.1rem;
  border:2px solid var(--navy); color:var(--navy); background:#fff;}
.stButton > button:hover{border-color:var(--gold); color:var(--navy-deep);}
.stButton > button[kind="primary"]{background:var(--sage); border-color:var(--sage); color:#fff;}
.stButton > button[kind="primary"]:hover{background:var(--sage-dark); border-color:var(--sage-dark); color:#fff;}

/* home tiles */
.st-key-tile_collect button, .st-key-tile_return button{min-height:13rem; border-radius:var(--radius);
  font-size:1.6rem; flex-direction:column; gap:.4rem; box-shadow:0 4px 14px rgba(0,0,0,.08);}
.st-key-tile_collect button{background:var(--navy); border-color:var(--navy); color:#fff;}
.st-key-tile_collect button:hover{background:var(--navy-deep); color:#fff;}
.st-key-tile_return button{background:#fff; border:3px solid var(--sage); color:var(--sage-dark);}
.st-key-tile_collect button p, .st-key-tile_return button p{font-size:1.6rem;}
.st-key-tile_collect button > div > span, .st-key-tile_return button > div > span{display:flex;
  flex-direction:column; align-items:center; gap:.8rem;}
[data-testid="stHeaderActionElements"]{display:none !important;}
.st-key-tile_collect [data-testid="stIconMaterial"], .st-key-tile_return [data-testid="stIconMaterial"]{font-size:3rem;}

/* booking list select buttons */
[class*="st-key-pick_"] button{min-height:2.6rem;}

/* fixed action bar: Back always bottom-left, main action always bottom-right */
.st-key-actionbar{position:fixed; left:0; right:0; bottom:0; z-index:999; background:#fff;
  border-top:1px solid #ddd; padding:.8rem 2rem; box-shadow:0 -2px 10px rgba(0,0,0,.06);}
.st-key-actionbar .hint{text-align:center; color:var(--muted); padding-top:.75rem; font-size:.95rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------- state
cfg = json.loads(CONFIG.read_text())
ss = st.session_state
ss.setdefault("page", "home")
ss.setdefault("mode", "collect")


def now():
    """Wall clock, or a fixed demo time (SMARTROOM_DEMO_TIME=HH:MM) for screenshots."""
    demo = os.environ.get("SMARTROOM_DEMO_TIME")
    if demo:
        return datetime.combine(datetime.today(), datetime.strptime(demo, "%H:%M").time())
    return datetime.now()


def go(page, **kw):
    ss.page = page
    for k, v in kw.items():
        ss[k] = v


def enter_staff():
    ss.prev_page = ss.page
    go("staff")


def exit_staff():
    """Back to the student screen staff came from (e.g. a denied verification), else Home."""
    ss.staff_ok = False
    prev = ss.pop("prev_page", "home")
    if prev in ("scan", "result") and ss.get("verif"):
        go("result" if ss.verif.approved or ss.get("override") else prev)
    else:
        reset()


def reset():
    for k in ("booking", "verif", "fails", "msg", "t0", "override", "staff_ok"):
        ss.pop(k, None)
    go("home")


@st.cache_resource(show_spinner="Loading face model ...")
def load_engine():
    from src.face_model import FaceModel
    from src.matcher import load_gallery
    model = FaceModel()
    return model, load_gallery(model)


def slot_status(b):
    start, end = [datetime.strptime(t.strip(), "%H:%M").time() for t in b["slot"].split("-")]
    t = now().time()
    if b["booking_id"] in card_log.cards_out():
        return "Card out", "b-out"
    if start <= t <= end:
        return "Now", "b-now"
    return ("Upcoming", "b-next") if t < start else ("Ended", "b-end")


def locker_no(b):
    return f"{BOOKINGS.index(b) + 1:02d}"


# ---------------------------------------------------------------- shared layout pieces
def top_bar():
    with st.container(key="topbar"):
        left, right, home, staff = st.columns([5, 2, 1.1, 1.1], vertical_alignment="center")
        left.markdown(
            '<div class="brand"><div class="mark">IRC</div><div class="txt">'
            '<b>SmartRoom UTP</b><span>Discussion Room Smart Locker</span></div></div>',
            unsafe_allow_html=True)
        t = now()
        right.markdown(f'<div class="clock"><b>{t:%H:%M}</b><br><span>{t:%A, %d %b %Y}</span></div>',
                       unsafe_allow_html=True)
        # Home and Staff never move: Home is disabled (not hidden) on the home screen
        home.button("Home", icon=":material/home:", key="home_btn", width="stretch",
                    disabled=ss.page == "home", on_click=reset)
        if ss.page == "staff":
            staff.button("Exit staff", icon=":material/logout:", key="exit_staff_btn", width="stretch",
                         on_click=exit_staff)
        else:
            staff.button("Staff", icon=":material/badge:", key="staff_btn", width="stretch",
                         on_click=enter_staff)
        if ss.page == "staff":
            strip = '<div class="mode staff">Staff mode - press Exit staff to return to the student screen</div>'
        elif cfg.get("simulation_mode"):
            strip = '<div class="mode">Simulation mode - face results are simulated for demonstration</div>'
        else:
            strip = '<div class="mode plain"></div>'
        st.markdown(strip, unsafe_allow_html=True)


def step_tracker():
    cur = PAGE_STEP.get(ss.page)
    if cur is None:
        return
    label = "Collect card" if ss.mode == "collect" else "Return card"
    html = ""
    for i, name in enumerate(STEPS):
        cls = "done" if i < cur else "now" if i == cur else ""
        name = label if i == 2 else name
        html += f'<div class="step {cls}"><span class="n">{"✓" if i < cur else i + 1}</span>{name}</div>'
    st.markdown(f'<div class="steps">{html}</div>', unsafe_allow_html=True)


def action_bar(back=None, primary=None, hint=""):
    """back/primary: (label, callback, args) or None. Back = bottom-left, primary = bottom-right."""
    with st.container(key="actionbar"):
        l, m, r = st.columns([1, 2, 1], vertical_alignment="center")
        if back:
            l.button(back[0], icon=":material/arrow_back:", key="ab_back", width="stretch",
                     on_click=back[1], args=back[2] if len(back) > 2 else ())
        m.markdown(f'<div class="hint">{hint}</div>', unsafe_allow_html=True)
        if primary:
            r.button(primary[0], icon=":material/arrow_forward:", type="primary", key="ab_primary",
                     width="stretch", on_click=primary[1], args=primary[2] if len(primary) > 2 else ())


def booking_panel(b, verif=None):
    status, cls = slot_status(b)
    rows = ""
    for m in b["members"]:
        ok = verif is not None and m in verif.verified
        chip = '<span class="chip c-ok">✓ Verified</span>' if ok else (
            '<span class="chip c-wait">Waiting</span>' if verif is not None else "")
        rows += (f'<div class="member"><span class="who"><span class="av{" ok" if ok else ""}">{m.split()[-1]}</span>'
                 f'{m}{" (booker)" if m == b["booked_by"] else ""}</span>{chip}</div>')
    prog = ""
    if verif is not None:
        pct = 100 * len(verif.verified) / verif.min_required
        prog = (f'<div style="margin-top:.8rem;font-weight:700;color:var(--navy)">'
                f'{len(verif.verified)} of {verif.min_required} verified</div>'
                f'<div class="progress"><div style="width:{min(pct, 100):.0f}%"></div></div>')
    st.markdown(
        f'<div class="card"><div class="panel-title">Your booking</div>'
        f'<h3>{b["room"]} <span class="badge {cls}">{status}</span></h3>'
        f'<div class="sub">{b["level"]} · {b["slot"]} · {b["booking_id"]}<br>Locker {locker_no(b)}</div>'
        f'<div style="margin-top:.8rem">{rows}</div>{prog}</div>',
        unsafe_allow_html=True)


def help_card():
    st.markdown(
        '<div class="card"><div class="panel-title">Need help?</div>'
        '<div class="sub">Go to the IRC User Advisory Desk or press <b>Staff</b> at the top right.'
        '<br>Opening hours 09:00 - 22:00</div></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- screens
def page_home():
    st.markdown(
        '<div class="hero"><h1>Welcome to IRC Discussion Rooms</h1>'
        '<p>Collect or return your room key card with face verification. No student card needed.</p></div>',
        unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("Collect Room Card", icon=":material/key:", key="tile_collect", width="stretch"):
            go("select", mode="collect")
            st.rerun()
        st.markdown('<div class="sub" style="text-align:center">I have a booking on iBEST and want the room card</div>',
                    unsafe_allow_html=True)
    with c2:
        if st.button("Return Room Card", icon=":material/keyboard_return:", key="tile_return", width="stretch"):
            go("select", mode="return")
            st.rerun()
        st.markdown('<div class="sub" style="text-align:center">We have finished and want to return the card</div>',
                    unsafe_allow_html=True)
    st.write("")
    st.markdown(
        '<div class="card"><div class="panel-title">How it works</div><ol class="howto">'
        '<li>Choose your booking from today\'s iBEST list.</li>'
        '<li>Every booked student looks at the camera, one at a time.</li>'
        '<li>When all are verified, the locker opens with your key card and pencil case.</li></ol></div>',
        unsafe_allow_html=True)


def page_select():
    collect = ss.mode == "collect"
    out = card_log.cards_out()
    main, side = st.columns([2, 1], gap="large")
    with main:
        st.markdown(f'<div class="title">{"Choose your booking" if collect else "Which card are you returning?"}</div>'
                    f'<div class="lead">{"Today" if collect else "Cards currently out"} · tap <b>Select</b> on your room</div>',
                    unsafe_allow_html=True)
        q = st.text_input("Search", placeholder="Search room or student code, e.g. Discussion Room 3 or Student A",
                          label_visibility="collapsed")
        items = [b for b in BOOKINGS if (b["booking_id"] not in out) == collect]
        if q:
            ql = q.lower()
            items = [b for b in items if ql in b["room"].lower() or any(ql in m.lower() for m in b["members"])]
        if not items:
            st.markdown('<div class="msg m-info">No matching bookings. Check iBEST or ask IRC staff.</div>',
                        unsafe_allow_html=True)
        for b in items:
            status, cls = slot_status(b)
            with st.container(border=True):
                info, pick = st.columns([4, 1], vertical_alignment="center")
                info.markdown(
                    f'<h3 style="margin:0;color:var(--navy)">{b["room"]} <span class="badge {cls}">{status}</span></h3>'
                    f'<div class="sub">🕘 {b["slot"]} · {b["level"]} · Booked by {b["booked_by"]}<br>'
                    f'👥 {", ".join(b["members"])}</div>', unsafe_allow_html=True)
                if pick.button("Select", key=f"pick_{b['booking_id']}", type="primary", width="stretch"):
                    need = cfg["min_required_collect" if collect else "min_required_return"]
                    go("scan", booking=b, verif=Verification(b["members"], min(need, len(b["members"]))),
                       fails=0, msg=None, t0=time.time())
                    st.rerun()
    with side:
        st.markdown(
            '<div class="card"><div class="panel-title">What happens next</div><ol class="howto">'
            '<li>Face scan for each booked student</li>'
            f'<li>{"Locker opens with key card + pencil case" if collect else "Locker opens, place card + pencil case inside"}</li>'
            '<li>Close the locker door</li></ol>'
            f'<div class="msg m-info" style="font-size:.9rem">All {cfg["min_required_collect" if collect else "min_required_return"]}'
            ' booked students must be present.</div></div>', unsafe_allow_html=True)
        help_card()
    action_bar(back=("Back", reset), hint="Can't find your booking? Ask staff at the counter.")


def simulate_scan(stranger=False):
    v = ss.verif
    if stranger or not v.pending:
        v.attempts += 1
        v.rejects += 1
        return {"status": "no_match", "score": random.uniform(0.05, 0.25)}
    code = v.pending[0]
    v.attempts += 1
    v.verified[code] = random.uniform(0.55, 0.85)
    return {"status": "verified", "code": code, "score": v.verified[code]}


def handle_result(res):
    if res["status"] == "verified":
        ss.fails = 0
        ss.msg = ("ok", f'✓ {res["code"]} verified (score {res["score"]:.2f}). Next student, please.')
    elif res["status"] == "duplicate":
        ss.msg = ("info", f'{res["code"]} is already verified. Next student, please.')
    elif res["status"] == "no_face":
        ss.fails += 1
        ss.msg = ("bad", "No face found. Look straight at the camera, remove mask or cap.")
    else:
        ss.fails += 1
        ss.msg = ("bad", "Face not recognised as a student on this booking. Please try again.")
    if ss.verif.approved:
        go("result", override=False)
    elif ss.fails >= cfg["max_failed_scans"]:
        go("result", override=False)


def page_scan():
    b, v = ss.booking, ss.verif
    main, side = st.columns([2, 1], gap="large")
    with main:
        nxt = v.pending[0] if v.pending else ""
        st.markdown('<div class="title">Face scan</div>'
                    '<div class="lead">One student at a time. Look at the camera and keep still.</div>',
                    unsafe_allow_html=True)
        if ss.get("msg"):
            kind, text = ss.msg
            st.markdown(f'<div class="msg m-{kind}">{text}</div>', unsafe_allow_html=True)
        if cfg.get("simulation_mode"):
            st.markdown(
                '<div class="camframe"><svg height="78%" viewBox="0 0 220 270">'
                '<ellipse cx="110" cy="135" rx="95" ry="125" fill="none" stroke="#EDCF89" stroke-width="4" stroke-dasharray="14 10"/>'
                '<circle cx="110" cy="105" r="42" fill="#5b6f8f"/><path d="M40 245c10-55 45-80 70-80s60 25 70 80" fill="#5b6f8f"/>'
                '</svg><div class="lbl">Position your face inside the oval</div></div>', unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            if c1.button("Scan face", icon=":material/photo_camera:", type="primary", width="stretch"):
                handle_result(simulate_scan())
                st.rerun()
            if c2.button("Unknown face", help="Simulates a person who is not on this booking", width="stretch"):
                handle_result(simulate_scan(stranger=True))
                st.rerun()
        else:
            shot = st.camera_input("Camera", label_visibility="collapsed", key=f"cam_{v.attempts}")
            if shot is not None:
                from src.face_model import decode_image
                model, gallery = load_engine()
                handle_result(v.submit(model.embed(decode_image(shot.getvalue())), gallery, cfg["threshold"]))
                st.rerun()
    with side:
        booking_panel(b, v)
        st.markdown(f'<div class="card"><div class="panel-title">Tips</div><div class="sub">'
                    f'Remove mask, cap or sunglasses · Face the light · Attempts left: '
                    f'<b>{cfg["max_failed_scans"] - ss.fails}</b></div></div>', unsafe_allow_html=True)
    action_bar(back=("Cancel", reset),
               hint=f"{len(v.verified)} of {v.min_required} verified" + (f" · next: any of {len(v.pending)} remaining" if nxt else ""))


def locker_svg(open_=True, color="#749082"):
    door = ('<path d="M150 20 L215 40 L215 220 L150 240 Z" fill="#dfe6f3" stroke="#324773" stroke-width="3"/>'
            if open_ else '<rect x="40" y="20" width="110" height="220" rx="6" fill="#324773"/>')
    inside = ('<rect x="58" y="120" width="74" height="48" rx="6" fill="#C48D0C"/>'
              '<text x="95" y="150" font-size="14" fill="#fff" text-anchor="middle" font-weight="700">KEY CARD</text>'
              '<rect x="58" y="180" width="74" height="22" rx="6" fill="#749082"/>') if open_ else ""
    return (f'<svg width="240" height="260" viewBox="0 0 240 260"><rect x="40" y="20" width="110" height="220" rx="6" '
            f'fill="#061E2F"/>{inside}{door}<circle cx="{205 if open_ else 138}" cy="130" r="5" fill="{color}"/></svg>')


def page_result():
    b, v = ss.booking, ss.verif
    collect = ss.mode == "collect"
    approved = v.approved or ss.get("override")
    main, side = st.columns([2, 1], gap="large")
    with main:
        if approved:
            how = "Staff override" if ss.get("override") else "All students verified"
            what = ("Take your <b>room key card</b> and <b>pencil case</b> (2 markers, 1 duster)." if collect else
                    "Place the <b>room key card</b> and <b>pencil case</b> inside, then close the door.")
            st.markdown(
                f'<div class="card" style="border-top:8px solid var(--sage)"><div style="display:flex;gap:2rem;align-items:center">'
                f'{locker_svg(True)}<div><div class="title" style="color:var(--sage-dark)">✓ Access approved</div>'
                f'<div class="lead">{how}. <b>Locker {locker_no(b)}</b> is now open.</div>'
                f'<div class="msg m-ok">{what}</div></div></div></div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="card" style="border-top:8px solid var(--danger)"><div style="display:flex;gap:2rem;align-items:center">'
                f'{locker_svg(False, "#A8322D")}<div><div class="title" style="color:var(--danger)">✕ Access denied</div>'
                f'<div class="lead">The locker stays closed. Not verified: <b>{", ".join(v.pending)}</b>.</div>'
                f'<div class="msg m-bad">All booked students must be present and recognised.</div>'
                f'<div class="sub">Try again with better lighting, or ask staff at the counter for help.</div>'
                f'</div></div></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("Try again", icon=":material/refresh:", type="primary", width="stretch"):
                go("scan", fails=0, msg=None)
                st.rerun()
            c2.button("Call staff", icon=":material/support_agent:", width="stretch", on_click=enter_staff)
    with side:
        booking_panel(b, v)
    if approved:
        def finish():
            method = "staff override" if ss.get("override") else "face"
            card_log.append(b, ss.mode, method, list(v.verified), time.time() - ss.t0)
            go("done")
        action_bar(primary=("I have taken the card" if collect else "Card returned, door closed", finish),
                   hint="Press the button after closing the locker door")
    else:
        action_bar(back=("Start over", reset), hint="Locker remains locked")


def page_done():
    b = ss.booking
    collect = ss.mode == "collect"
    end = b["slot"].split("-")[1].strip()
    st.markdown(
        f'<div class="hero" style="text-align:center;padding:3rem"><h1>{"Enjoy your discussion!" if collect else "Thank you!"}</h1>'
        f'<p>{f"Please return the card to Locker {locker_no(b)} by <b>{end}</b>." if collect else "Your card has been returned. The room is now released."}</p></div>',
        unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="card"><div class="panel-title">Room</div><h3>{b["room"]}</h3><div class="sub">{b["level"]}</div></div>',
                unsafe_allow_html=True)
    c2.markdown(f'<div class="card"><div class="panel-title">Time slot</div><h3>{b["slot"]}</h3><div class="sub">{b["booking_id"]}</div></div>',
                unsafe_allow_html=True)
    c3.markdown(f'<div class="card"><div class="panel-title">Verification time</div><h3>{time.time() - ss.t0:.0f} s</h3>'
                f'<div class="sub">{len(ss.verif.verified)} students verified</div></div>', unsafe_allow_html=True)
    action_bar(primary=("Finish", reset), hint="Logged with student codes only")


def page_staff():
    main, side = st.columns([2, 1], gap="large")
    with main:
        st.markdown('<div class="title">Staff panel</div><div class="lead">IRC counter staff only</div>',
                    unsafe_allow_html=True)
        if not ss.get("staff_ok"):
            with st.form("pin"):
                pin = st.text_input("Staff PIN", type="password", max_chars=6)
                if st.form_submit_button("Log in", type="primary"):
                    if pin == cfg["staff_pin"]:
                        ss.staff_ok = True
                        st.rerun()
                    st.error("Wrong PIN")
        else:
            t1, t2, t3 = st.tabs(["Override", "Card log", "Settings"])
            with t1:
                if ss.get("booking") and ss.get("verif") and not ss.verif.approved:
                    b = ss.booking
                    st.markdown(f'<div class="msg m-info">Pending: {b["room"]} · not verified: '
                                f'{", ".join(ss.verif.pending)}</div>', unsafe_allow_html=True)
                    st.caption("Check the students' cards manually, then approve.")
                    if st.button("Approve and open locker", type="primary", icon=":material/lock_open:"):
                        go("result", override=True)
                        st.rerun()
                else:
                    st.info("No denied verification waiting. Overrides appear here when a student presses Call staff.")
            with t2:
                df = card_log.read()
                st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")
                out = card_log.cards_out()
                st.caption(f"Cards currently out: {', '.join(sorted(out)) or 'none'}")
            with t3:
                with st.form("settings"):
                    thr = st.slider("Match threshold (cosine)", 0.2, 0.8, float(cfg["threshold"]), 0.01)
                    mc = st.number_input("Students required to collect", 1, 4, int(cfg["min_required_collect"]))
                    mr = st.number_input("Students required to return", 1, 4, int(cfg["min_required_return"]))
                    sim = st.toggle("Simulation mode (no camera)", value=cfg.get("simulation_mode", True))
                    if st.form_submit_button("Save settings", type="primary"):
                        cfg.update(threshold=thr, min_required_collect=mc, min_required_return=mr, simulation_mode=sim)
                        CONFIG.write_text(json.dumps(cfg, indent=2))
                        st.success("Saved")
    with side:
        st.markdown('<div class="card"><div class="panel-title">Privacy</div><div class="sub">'
                    'Logs and screens show student codes only. Face images and embeddings stay on this '
                    'kiosk and are deleted at the end of the course.</div></div>', unsafe_allow_html=True)
    back = ("Back to verification", go, ("result",)) if ss.get("booking") and ss.get("verif") else ("Home", reset)
    action_bar(back=back, hint="Staff mode")


# ---------------------------------------------------------------- router
top_bar()
step_tracker()
{"home": page_home, "select": page_select, "scan": page_scan, "result": page_result,
 "done": page_done, "staff": page_staff}[ss.page]()
