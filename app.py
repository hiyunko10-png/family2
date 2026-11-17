"""우리집 — 가족의 하루를 함께 챙기는 작은 공간.

실행: python -m streamlit run app.py
GitHub에는 app.py와 requirements.txt를 올리고 Streamlit Community Cloud에서
저장소와 app.py를 지정하세요. GitHub 자체는 Streamlit 실행 서비스가 아닙니다.

선택 설정 (Streamlit 앱 설정 > Secrets; 코드에 비밀번호를 쓰지 마세요):
    APP_PASSWORD = "가족끼리만 공유할 비밀번호"
    DATA_DIR = "/영구저장소가/있는/경우에만/지정"

기본 저장은 app.py 옆 SQLite 파일입니다. Community Cloud의 로컬 파일은
재배포·휴면 복구 등으로 사라질 수 있습니다. 설정에서 정기적으로 백업하세요.
GitHub에는 기록이 자동으로 올라가지 않습니다. 가족 선택은 로그인이 아니며,
같은 비밀번호를 아는 가족은 다른 가족으로 전환할 수 있습니다.
"""
from __future__ import annotations

import calendar
import copy
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="우리집 | 함께 챙기는 하루", page_icon="🌿", layout="wide")
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).date()
MEALS = ["아직 몰라요", "먹어요", "안 먹어요"]
STATUSES = {"open": "함께할 가족을 찾아요", "claimed": "하고 있어요", "submitted": "확인 기다려요", "approved": "완료했어요"}
WEEKDAYS = "월화수목금토일"
PALETTE = ["#e7eee4", "#faead9", "#e6edf5", "#f1e5eb", "#ede9d9"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap');
:root {color-scheme:light;--forest:#254c3b;--paper:#f7f8f3;--ink:#263c32;}
html,body,.stApp {font-family:Pretendard,-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;color:var(--ink);background:var(--paper);}
[data-testid="stAppViewContainer"],[data-testid="stHeader"] {background:var(--paper);}
[data-testid="stHeader"] {display:none;}
.block-container {max-width:1200px;padding:2.2rem 2.5rem 3rem;}
[data-testid="stMainBlockContainer"] {padding-top:2.2rem;}
h1,h2,h3,p,label {word-break:keep-all;letter-spacing:-.025em;}
p {line-height:1.75;}
h1 {font-family:'Gowun Batang',serif!important;font-size:2.55rem!important;font-weight:700!important;line-height:1.4!important;padding:0!important;color:var(--ink)!important;}
h2 {font-size:1.2rem!important;font-weight:700!important;padding:.35rem 0!important;color:var(--ink)!important;}
h3 {font-size:1.05rem!important;color:var(--ink)!important;}
[data-testid="stCaptionContainer"] p {color:#617268!important;}
[data-testid="stVerticalBlock"] {gap:.8rem;}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button {border-radius:10px;min-height:43px;font-weight:600;border-color:#d5dfd4;background:#fff;color:#294d3b;box-shadow:none;}
[data-testid="stButton"] button:hover {border-color:#315c43;background:#edf2e9;color:#254c3b;}
button[kind="primary"],button[kind="primaryFormSubmit"] {background:#2e5943!important;border-color:#2e5943!important;color:white!important;}
button:focus-visible,input:focus-visible,textarea:focus-visible {outline:3px solid #ba742d!important;outline-offset:3px;}
[data-testid="stForm"] {border:1px solid #dce4d9;border-radius:15px;background:#fff;padding:1.15rem;}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"] {background:#fafbf8!important;border-radius:9px!important;}
input,textarea {color:#263c32!important;}
[data-testid="stTextInput"] label p,[data-testid="stSelectbox"] label p,[data-testid="stRadio"] label p {color:#344f3f;}
[data-testid="stExpander"] {background:#fff;border-color:#dce4d9;border-radius:12px;}
.masthead {display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #dce3d8;padding-bottom:19px;margin-bottom:13px;}
.brand {display:flex;align-items:center;gap:11px;font-size:24px;font-weight:800;letter-spacing:-1.1px;}
.brand-mark {width:36px;height:36px;background:#2e5943;border-radius:12px;display:grid;place-items:center;color:#fff;font-size:21px;}
.brand-note {font-size:12px;color:#66776a;letter-spacing:0;font-weight:400;margin-left:9px;}
.dateline {font-size:13px;color:#617268;}
.st-key-navigation {border-bottom:1px solid #dce3d8;padding-bottom:14px;margin-bottom:14px;}
.st-key-navigation [data-testid="stHorizontalBlock"] {gap:9px;}
.st-key-navigation button {border:0!important;background:transparent!important;}
.st-key-navigation button[kind="primary"] {background:#e4ecdf!important;color:#264d38!important;}
.greeting {margin:13px 0 4px;}
.intro {color:#617268;font-size:14px;margin:10px 0 20px;}
.hero {position:relative;overflow:hidden;border-radius:21px;background:#e6eedf;min-height:224px;padding:28px 31px;margin-bottom:7px;}
.hero-label {font-size:13px;font-weight:600;color:#506547;}
.hero-title {font-family:'Gowun Batang',serif;font-size:29px;font-weight:700;line-height:1.55;margin:12px 0 8px;max-width:65%;color:#244733;}
.hero-note {font-size:12px;color:#4c6348;max-width:65%;}
.hero svg {position:absolute;width:210px;right:13px;bottom:2px;}
.sectionline {display:flex;align-items:center;justify-content:space-between;margin:20px 0 11px;}
.sectionline strong {font-size:17px;letter-spacing:-.5px;}
.sectionline span {font-size:12px;color:#68786c;}
.person {display:flex;gap:13px;align-items:center;border-bottom:1px solid #e7ece3;padding:14px 3px;}
.avatar {display:grid;place-items:center;width:41px;height:41px;border-radius:50%;font-size:15px;font-weight:700;flex-shrink:0;}
.person-main {flex:1;min-width:0;overflow-wrap:anywhere;font-size:14px;font-weight:600;}
.person-main small {display:block;font-size:12px;font-weight:400;color:#69796e;margin-top:4px;}
.pill {display:inline-block;border-radius:6px;padding:4px 8px;font-size:11px;background:#e8efdf;color:#3c5c30;white-space:nowrap;font-weight:600;}
.pill.neutral {background:#edf0eb;color:#5a6a5e;}
.pill.amber {background:#f8ecd8;color:#795223;}
.note-card {background:#fff;border:1px solid #e0e6db;border-radius:13px;padding:18px 20px;margin-bottom:10px;}
.note-card .title {font-size:16px;font-weight:700;line-height:1.6;overflow-wrap:anywhere;}
.note-card .meta {font-size:12px;color:#647567;margin-top:7px;line-height:1.8;}
.note-card .reward {border-top:1px dashed #dbe2d4;margin-top:14px;padding-top:12px;font-size:13px;color:#73562b;}
.empty {padding:27px 20px;border:1px dashed #cedbc9;border-radius:13px;text-align:center;color:#687b69;font-size:13px;line-height:1.9;background:#f2f5ed;}
.footer {border-top:1px solid #dce3d8;margin-top:34px;padding-top:15px;color:#738071;font-size:11px;display:flex;justify-content:space-between;gap:12px;}
.st-key-calendar {padding:17px;border:1px solid #dce4d7;border-radius:15px;background:#fff;}
.st-key-calendar [data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;gap:4px!important;}
.st-key-calendar [data-testid="stColumn"] {min-width:0!important;width:0!important;flex:1 1 0!important;}
.st-key-calendar button {padding:0!important;border:0!important;min-height:44px!important;}
.st-key-calendar button:disabled {visibility:hidden;}
.weekday {text-align:center;color:#68786b;font-size:12px;padding:10px 0;}
.calendar-title {font-size:19px;font-weight:700;text-align:center;line-height:43px;}
.st-key-monthnav [data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;}
.st-key-monthnav [data-testid="stColumn"] {min-width:0!important;}
.st-key-monthnav button {padding:0 4px!important;}
.st-key-monthnav button p {font-size:12px!important;white-space:nowrap;}
button {touch-action:manipulation;}
@media(max-width:700px) {
 .block-container {padding:1.2rem 1.05rem 2rem;}[data-testid="stMainBlockContainer"] {padding-top:1.2rem;}
 .brand-note {display:none;}.dateline {font-size:11px;}.brand {font-size:22px;}
 h1 {font-size:2rem!important;}.hero {padding:23px;min-height:210px;}.hero-title {font-size:25px;max-width:67%;}.hero svg {width:155px;right:-9px;}.hero-note {max-width:62%;}
 .st-key-navigation [data-testid="stHorizontalBlock"] {flex-wrap:nowrap!important;gap:3px!important;}
 .st-key-navigation [data-testid="stColumn"] {min-width:0!important;width:0!important;flex:1 1 0!important;}
 .st-key-navigation button {padding:0 3px!important;}.st-key-navigation button p {font-size:13px;white-space:nowrap;}
 .footer {font-size:10px;}.st-key-calendar {padding:10px;}
}
@media(prefers-reduced-motion:reduce) {* {transition:none!important;animation:none!important;}}
</style>
"""

ILLUSTRATION = """<svg viewBox="0 0 240 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="함께 식사할 준비가 된 작은 집">
<circle cx="153" cy="62" r="31" fill="#f4dca2"/><path d="M15 195Q110 159 233 192" fill="none" stroke="#b7c9a8" stroke-width="2"/>
<rect x="60" y="94" width="137" height="99" rx="6" fill="#faf9e9"/><path d="M41 99L125 33L213 99Z" fill="#3e684a"/>
<path d="M40 100L125 34L212 100" fill="none" stroke="#2a4e39" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="115" y="137" width="35" height="56" rx="16" fill="#d9ac70"/><circle cx="141" cy="168" r="2" fill="#70593b"/>
<rect x="76" y="118" width="25" height="26" rx="4" fill="#e8c778"/><path d="M88 118v26m-12-13h25" stroke="#fff9e4" stroke-width="3"/>
<rect x="160" y="118" width="25" height="26" rx="4" fill="#e8c778"/><path d="M172 118v26m-12-13h25" stroke="#fff9e4" stroke-width="3"/>
<path d="M35 190v-63m0 30C5 157 7 119 31 121c-9-22 21-30 28-10 22 7 15 41-24 46" fill="#7b9b66" stroke="#567746" stroke-width="3"/>
<path d="M208 193v-28m0 10q-22-12-16-23 18-2 16 23m0 7q24-11 20-24-21-4-20 24" fill="#6b8c55" stroke="#567746" stroke-width="2"/>
<path d="M118 194l-9 21h53l-16-21" fill="#c9d6b8"/></svg>"""


def setting(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.environ.get(name, default)))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.environ.get(name, default)


def blank() -> dict:
    return {"members": [], "days": {}, "tasks": [], "events": []}


def new_id() -> str:
    return uuid.uuid4().hex


def text(value, limit=200) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError("문자열 형식 또는 길이를 확인해 주세요.")
    return value.strip()


def arrival_options() -> list[str]:
    return ["미정", "집에 있어요"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]


def clock(value: str) -> str:
    try:
        h, m = map(int, value.split(":"))
        return f"{'오전' if h < 12 else '오후'} {h % 12 or 12}:{m:02d}"
    except (ValueError, AttributeError):
        return value


def validate(raw: dict) -> dict:
    """기존 JSON 백업과 새 백업을 같은 형식으로 엄격하게 정규화합니다."""
    if not isinstance(raw, dict):
        raise ValueError("백업 내용이 올바르지 않아요.")
    if "data" in raw:
        raw = raw["data"]
    if not isinstance(raw, dict):
        raise ValueError("백업 내용이 올바르지 않아요.")
    out = blank()
    members = raw.get("members")
    if not isinstance(members, list) or len(members) > 30:
        raise ValueError("가족은 최대 30명까지 등록할 수 있어요.")
    out["members"] = [text(n, 16) for n in members]
    if any(not n for n in out["members"]) or len(set(out["members"])) != len(members):
        raise ValueError("가족 별명이 비어 있거나 중복돼요.")
    days = raw.get("days", {})
    if not isinstance(days, dict) or len(days) > 20000:
        raise ValueError("하루 기록 형식이 올바르지 않아요.")
    for day, entries in days.items():
        date.fromisoformat(day)
        if not isinstance(entries, dict) or len(entries) > 30:
            raise ValueError("가족별 하루 기록을 확인해 주세요.")
        out["days"][day] = {}
        for member, entry in entries.items():
            if member not in members or not isinstance(entry, dict):
                raise ValueError("하루 기록의 가족 정보를 확인해 주세요.")
            meal = entry.get("meal", "아직 몰라요")
            arrival = text(entry.get("arrival", "미정"), 20)
            if meal not in MEALS or arrival not in arrival_options():
                raise ValueError("식사 또는 귀가 시간을 확인해 주세요.")
            out["days"][day][member] = {"meal": meal, "arrival": arrival}
    for collection in ("tasks", "events"):
        records = raw.get(collection, [])
        if not isinstance(records, list) or len(records) > 10000:
            raise ValueError("부탁 또는 일정이 너무 많거나 형식이 올바르지 않아요.")
        ids = set()
        for item in records:
            if not isinstance(item, dict):
                raise ValueError("기록 형식을 확인해 주세요.")
            rid = text(item.get("id", ""), 100)
            title = text(item.get("title", ""), 100)
            if not rid or rid in ids or not title:
                raise ValueError("중복된 기록 또는 제목이 없는 기록이 있어요.")
            ids.add(rid)
            if collection == "tasks":
                status = item.get("status")
                if status is None:
                    status = "approved" if item.get("done") else "claimed" if item.get("owner") else "open"
                if status == "done":
                    status = "approved"
                owner, creator = text(item.get("owner", ""), 16), text(item.get("created", ""), 16)
                if status not in STATUSES or creator not in members or (owner and owner not in members):
                    raise ValueError("부탁의 담당 가족 또는 상태가 올바르지 않아요.")
                if status != "open" and not owner:
                    raise ValueError("진행 중인 부탁에 담당 가족이 없어요.")
                reward = item.get("reward", 0)
                if type(reward) is not int or not 0 <= reward <= 1000000 or type(item.get("paid", False)) is not bool:
                    raise ValueError("보상 형식을 확인해 주세요.")
                out[collection].append({"id": rid, "title": title, "created": creator, "owner": owner,
                    "status": status, "reward": reward, "prize": text(item.get("prize", ""), 100),
                    "paid": item.get("paid", False), "done": status == "approved"})
            else:
                day = text(item.get("date", ""), 10)
                date.fromisoformat(day)
                who = text(item.get("who", "가족 모두"), 16)
                if who not in members + ["가족 모두"]:
                    raise ValueError("일정의 가족 정보를 확인해 주세요.")
                items = item.get("items", [])
                if not isinstance(items, list) or len(items) > 50:
                    raise ValueError("준비물은 최대 50개예요.")
                prep = []
                for v in items:
                    if not isinstance(v, dict) or type(v.get("done")) is not bool:
                        raise ValueError("준비물 형식을 확인해 주세요.")
                    label = text(v.get("text", ""), 100)
                    if not label:
                        raise ValueError("준비물 이름이 비어 있어요.")
                    prep.append({"text": label, "done": v["done"]})
                out[collection].append({"id": rid, "title": title, "date": day, "who": who,
                    "time": text(item.get("time", ""), 100), "items": prep})
    return out


def connect() -> sqlite3.Connection:
    folder = Path(setting("DATA_DIR", str(Path(__file__).resolve().parent)))
    folder.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(folder / "woorijip.sqlite3", timeout=10)
    con.execute("PRAGMA busy_timeout=10000")
    con.execute("CREATE TABLE IF NOT EXISTS household (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)")
    if not con.execute("SELECT 1 FROM household WHERE id=1").fetchone():
        initial = blank()
        old = folder / "home_today.json"
        if old.exists():
            initial = validate(json.loads(old.read_text(encoding="utf-8")))
        con.execute("INSERT OR IGNORE INTO household VALUES(1,0,?)", (json.dumps(initial, ensure_ascii=False),))
    con.commit()
    return con


def load() -> tuple[dict, int]:
    if st.session_state.get("demo"):
        return copy.deepcopy(st.session_state.demo_data), st.session_state.demo_revision
    con = connect()
    try:
        revision, payload = con.execute("SELECT revision,payload FROM household WHERE id=1").fetchone()
        return validate(json.loads(payload)), revision
    finally:
        con.close()


def persist(data: dict, revision: int) -> bool:
    data = validate(data)
    if st.session_state.get("demo"):
        st.session_state.demo_data = copy.deepcopy(data)
        st.session_state.demo_revision += 1
        return True
    con = connect()
    try:
        with con:
            result = con.execute("UPDATE household SET payload=?,revision=revision+1 WHERE id=1 AND revision=?",
                (json.dumps(data, ensure_ascii=False), revision))
            return result.rowcount == 1
    finally:
        con.close()


def save(message="저장했어요."):
    try:
        if not persist(DATA, REVISION):
            st.error("다른 가족이 먼저 수정했어요. 화면을 새로고침한 뒤 다시 입력해 주세요.")
            st.stop()
    except (sqlite3.Error, OSError, ValueError) as exc:
        st.error("저장하지 못했어요. 입력 내용과 저장 공간을 확인한 뒤 다시 시도해 주세요.")
        st.caption(str(exc) if isinstance(exc, ValueError) else "저장 공간 접근에 문제가 있어요. 기존 기록은 덮어쓰지 않았어요.")
        st.stop()
    st.session_state.flash = message
    st.rerun()


def demo_data() -> dict:
    d = blank()
    d["members"] = ["엄마", "아빠", "지우", "하준"]
    d["days"][TODAY.isoformat()] = {"엄마": {"meal": "먹어요", "arrival": "집에 있어요"},
        "아빠": {"meal": "먹어요", "arrival": "18:30"}, "지우": {"meal": "먹어요", "arrival": "19:00"}}
    d["tasks"] = [{"id": new_id(), "title": "오는 길에 우유 한 팩 부탁해요", "created": "엄마", "owner": "",
        "status": "open", "prize": "따뜻한 커피 한 잔", "reward": 0, "paid": False, "done": False},
        {"id": new_id(), "title": "거실 화분에 물 주기", "created": "아빠", "owner": "지우",
        "status": "claimed", "prize": "주말 영화 고르기", "reward": 0, "paid": False, "done": False}]
    d["events"] = [{"id": new_id(), "title": "다 같이 저녁 먹는 날", "date": TODAY.isoformat(), "who": "가족 모두", "time": "오후 7시 · 우리집", "items": []},
        {"id": new_id(), "title": "가볍게, 주말 피크닉", "date": (TODAY + timedelta(days=3)).isoformat(), "who": "가족 모두", "time": "오전 11시 · 동네 공원", "items": [{"text": "돗자리", "done": False}, {"text": "도시락", "done": False}]}]
    return d


def html(value: str):
    st.markdown(value, unsafe_allow_html=True)


def section(title: str, note: str = ""):
    html(f'<div class="sectionline"><strong>{escape(title)}</strong><span>{escape(note)}</span></div>')


def empty(message: str):
    html(f'<div class="empty">{escape(message)}</div>')


def card(title: str, meta: str, badge="", reward=""):
    html('<div class="note-card">' + (f'<div class="pill" style="margin-bottom:10px">{escape(badge)}</div>' if badge else "")
         + f'<div class="title">{escape(title)}</div><div class="meta">{escape(meta)}</div>'
         + (f'<div class="reward">작은 보상　{escape(reward)}</div>' if reward else "") + '</div>')


def go(page: str):
    st.session_state.page = page
    st.session_state.pop("editor", None)
    st.rerun()


def today_page(actor: str):
    html(f'<div class="greeting"><h1>오늘도, 함께라서 좋아요.</h1></div><div class="intro">{escape(actor)}님, 우리 가족의 하루를 가볍게 챙겨보세요.</div>')
    entries = DATA["days"].get(TODAY.isoformat(), {})
    count = sum(entries.get(n, {}).get("meal") == "먹어요" for n in DATA["members"])
    pending = sum(entries.get(n, {}).get("meal", "아직 몰라요") == "아직 몰라요" for n in DATA["members"])
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        note = f'{pending}명의 저녁 소식을 기다리고 있어요.' if pending else '모두의 저녁 소식이 도착했어요.'
        html(f'<div class="hero"><div class="hero-label">오늘 저녁, 우리집 식탁</div><div class="hero-title">{count}명이 함께<br>저녁을 먹어요.</div><div class="hero-note">{note}</div>' + ILLUSTRATION + '</div>')
        section("가족들의 오늘", f"함께하는 {len(DATA['members'])}명")
        for i, n in enumerate(DATA["members"]):
            e = entries.get(n, {})
            meal = e.get("meal", "아직 몰라요")
            state, style = ("함께 먹어요", "") if meal == "먹어요" else (("밖에서 먹어요", "neutral") if meal == "안 먹어요" else ("아직 미정", "amber"))
            me = '<span style="font-size:10px;color:#69796e">나</span>' if n == actor else ""
            html(f'<div class="person"><div class="avatar" style="background:{PALETTE[i % len(PALETTE)]}">{escape(n[:1])}</div><div class="person-main">{escape(n)} {me}<small>귀가　{escape(clock(e.get("arrival", "미정")))}</small></div><span class="pill {style}">{state}</span></div>')
        section("내 저녁 소식")
        current = entries.get(actor, {})
        with st.form(f"meal_{actor}_{TODAY}"):
            meal = st.radio("오늘 저녁은요?", MEALS, index=MEALS.index(current.get("meal", MEALS[0])), horizontal=True)
            options = arrival_options()
            arrival = st.selectbox("언제 집에 오나요?", options, index=options.index(current.get("arrival", "미정")), format_func=clock)
            if st.form_submit_button("내 소식 저장", type="primary", use_container_width=True):
                DATA["days"].setdefault(TODAY.isoformat(), {})[actor] = {"meal": meal, "arrival": arrival}
                save("가족에게 내 저녁 소식을 전했어요.")
    with right:
        section("다가오는 가족 일정", "오늘부터")
        events = sorted([e for e in DATA["events"] if e["date"] >= TODAY.isoformat()], key=lambda e: (e["date"], e["time"]))
        for e in events[:3]:
            when = date.fromisoformat(e["date"])
            card(e["title"], f'{e["who"]} · {e["time"] or "시간·장소 미정"}', "오늘" if when == TODAY else f"{when.month}월 {when.day}일 ({WEEKDAYS[when.weekday()]})")
        if not events:
            empty("함께할 다음 일정을 등록해 보세요.")
        if st.button("가족 캘린더 보기", use_container_width=True):
            go("일정")
        active = [t for t in DATA["tasks"] if t["status"] != "approved"]
        section("가족의 작은 부탁", f"진행 중 {len(active)}개")
        for t in list(reversed(active))[:2]:
            card(t["title"], f'{t["created"]}의 부탁 · {t["owner"] or "아직 담당이 없어요"}', reward=t["prize"] or (f'{t["reward"]:,}원' if t["reward"] else ""))
        if not active:
            empty("부탁이 없어요. 작은 일도 함께 나눠요.")
        if st.button("부탁 나누러 가기", use_container_width=True):
            go("부탁")


def task_editor(actor: str, original=None):
    old_prize = (original.get("prize", "") or (f'{original["reward"]:,}원' if original["reward"] else "")) if original else ""
    with st.form("task_editor"):
        title = st.text_input("어떤 부탁인가요? *", value=original["title"] if original else "", max_chars=70, placeholder="예: 오는 길에 우유 한 팩 사다 주기")
        prize = st.text_input("작은 보상 (선택)", value=old_prize, max_chars=100, placeholder="예: 아이스크림 / 3,000원 / 주말 영화 고르기")
        if st.form_submit_button("부탁 수정" if original else "부탁 등록", type="primary", use_container_width=True):
            if not title.strip():
                st.error("부탁 내용을 적어 주세요.")
            else:
                if original:
                    original.update(title=title.strip(), prize=prize.strip(), reward=0)
                else:
                    DATA["tasks"].append({"id": new_id(), "title": title.strip(), "prize": prize.strip(), "created": actor, "owner": "", "reward": 0, "status": "open", "done": False, "paid": False})
                st.session_state.pop("editor", None)
                save("부탁을 저장했어요.")
    if st.button("목록으로 돌아가기"):
        st.session_state.pop("editor", None)
        st.rerun()


def tasks_page(actor: str):
    st.title("작은 부탁, 같이 해요.")
    st.caption("혼자 하기 번거로운 일도 함께 나누면 가벼워져요.")
    editor = st.session_state.get("editor", "")
    original = next((t for t in DATA["tasks"] if t["id"] == editor and t["created"] == actor and t["status"] == "open"), None)
    if editor == "new_task" or original:
        task_editor(actor, original)
        return
    if st.button("＋ 새로운 부탁", type="primary"):
        st.session_state.editor = "new_task"
        st.rerun()
    category = st.radio("부탁 목록", ["진행 중", "확인 대기", "완료"], horizontal=True)
    only_mine = st.checkbox("내가 부탁하거나 맡은 일만 보기")
    tasks = [t for t in reversed(DATA["tasks"]) if (t["status"] in ("open", "claimed") if category == "진행 중" else t["status"] == "submitted" if category == "확인 대기" else t["status"] == "approved") and (not only_mine or actor in (t["owner"], t["created"]))]
    if not tasks:
        empty("여기는 아직 조용해요. 새로운 부탁을 남겨보세요.")
    if len(tasks) > 12:
        pages = (len(tasks) + 11) // 12
        page_no = st.selectbox("목록 페이지", list(range(1, pages + 1)), format_func=lambda n: f"{n} / {pages}쪽", key=f"task_page_{category}_{actor}_{only_mine}")
        tasks = tasks[(page_no - 1) * 12:page_no * 12]
    for t in tasks:
        with st.container(border=True):
            prize = t["prize"] or (f'{t["reward"]:,}원' if t["reward"] else "")
            card(t["title"], f'{t["created"]}의 부탁 · 담당: {t["owner"] or "아직 없어요"}', STATUSES[t["status"]], prize)
            if t["status"] == "open":
                if t["created"] != actor:
                    if st.button("내가 할게요", key="claim_" + t["id"], type="primary"):
                        t.update(owner=actor, status="claimed")
                        save("부탁을 맡았어요. 고마워요!")
                else:
                    a, b = st.columns(2)
                    if a.button("내용 수정", key="edit_" + t["id"]):
                        st.session_state.editor = t["id"]
                        st.rerun()
                    if b.button("부탁 삭제", key="delete_" + t["id"]):
                        st.session_state.confirm_task = t["id"]
                    if st.session_state.get("confirm_task") == t["id"]:
                        agree = st.checkbox("이 부탁을 삭제할게요", key="agree_" + t["id"])
                        if st.button("삭제하기", key="delete_yes_" + t["id"], disabled=not agree):
                            DATA["tasks"] = [v for v in DATA["tasks"] if v["id"] != t["id"]]
                            st.session_state.pop("confirm_task", None)
                            save("부탁을 삭제했어요.")
            elif t["status"] == "claimed" and t["owner"] == actor:
                a, b = st.columns(2)
                if a.button("완료했어요", key="submit_" + t["id"], type="primary"):
                    t["status"] = "submitted"
                    save("완료 소식을 보냈어요. 부탁한 가족의 확인을 기다려 주세요.")
                if b.button("맡기 취소", key="unclaim_" + t["id"]):
                    t.update(owner="", status="open")
                    save("다른 가족이 맡을 수 있게 했어요.")
            elif t["status"] == "submitted" and t["created"] == actor:
                a, b = st.columns(2)
                if a.button("고마워요, 완료 승인", key="approve_" + t["id"], type="primary"):
                    t.update(status="approved", done=True)
                    save("부탁이 완료됐어요.")
                if b.button("다시 부탁하기", key="return_" + t["id"]):
                    t["status"] = "claimed"
                    save("담당 가족에게 다시 부탁했어요.")
            elif t["status"] == "approved" and prize:
                if t["paid"]:
                    st.caption("✓ 보상까지 전달했어요.")
                elif t["created"] == actor and st.button("보상 전달했어요", key="pay_" + t["id"]):
                    t["paid"] = True
                    save("보상 전달을 기록했어요.")


def event_editor(chosen: date, original=None):
    with st.form("event_editor"):
        title = st.text_input("일정 이름 *", value=original["title"] if original else "", max_chars=70, placeholder="예: 함께하는 주말 피크닉")
        when = st.date_input("날짜", value=date.fromisoformat(original["date"]) if original else chosen)
        people = ["가족 모두"] + DATA["members"]
        who = st.selectbox("함께하는 가족", people, index=people.index(original["who"]) if original else 0)
        place = st.text_input("시간 · 장소", value=original["time"] if original else "", max_chars=100, placeholder="예: 오전 11시 · 동네 공원")
        prep = st.text_area("준비물 (한 줄에 하나씩)", value="\n".join(i["text"] for i in original["items"]) if original else "", max_chars=2000, placeholder="예: 돗자리\n도시락")
        if st.form_submit_button("일정 수정" if original else "일정 등록", type="primary", use_container_width=True):
            labels = [s.strip() for s in prep.splitlines() if s.strip()]
            if not title.strip():
                st.error("일정 이름을 적어 주세요.")
            elif len(labels) > 50 or any(len(s) > 100 for s in labels):
                st.error("준비물은 50개까지, 각각 100자 이내로 적어 주세요.")
            else:
                old_checks = {i["text"]: i["done"] for i in original["items"]} if original else {}
                values = {"title": title.strip(), "date": when.isoformat(), "who": who, "time": place.strip(),
                    "items": [{"text": s, "done": old_checks.get(s, False)} for s in dict.fromkeys(labels)]}
                if original:
                    original.update(values)
                else:
                    DATA["events"].append({"id": new_id(), **values})
                st.session_state.update(selected_day=when.isoformat(), month=when.replace(day=1).isoformat())
                st.session_state.pop("editor", None)
                save("가족 일정을 저장했어요.")
    if st.button("캘린더로 돌아가기"):
        st.session_state.pop("editor", None)
        st.rerun()


def calendar_page():
    st.title("함께할 날을 기록해요.")
    st.caption("평범한 약속부터 특별한 날까지, 우리 가족의 캘린더예요.")
    st.session_state.setdefault("month", TODAY.replace(day=1).isoformat())
    st.session_state.setdefault("selected_day", TODAY.isoformat())
    cursor = date.fromisoformat(st.session_state.month)
    chosen = date.fromisoformat(st.session_state.selected_day)
    editor = st.session_state.get("editor")
    original = next((e for e in DATA["events"] if e["id"] == editor), None)
    if editor == "new_event" or original:
        event_editor(chosen, original)
        return
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        with st.container(key="monthnav"):
            a, b, c = st.columns([1.1, 3, 1.1])
            previous = a.button("이전 달", use_container_width=True, disabled=cursor.year <= 1900 and cursor.month == 1)
            b.markdown(f'<div class="calendar-title">{cursor.year}년 {cursor.month}월</div>', unsafe_allow_html=True)
            following = c.button("다음 달", use_container_width=True, disabled=cursor.year >= 2200 and cursor.month == 12)
        if previous or following:
            n = cursor.year * 12 + cursor.month - 1 + (1 if following else -1)
            target = date(n // 12, n % 12 + 1, 1)
            st.session_state.update(month=target.isoformat(), selected_day=target.isoformat())
            st.rerun()
        event_days = {e["date"] for e in DATA["events"]}
        with st.container(key="calendar"):
            for col, day in zip(st.columns(7), "일월화수목금토"):
                col.markdown(f'<div class="weekday">{day}</div>', unsafe_allow_html=True)
            for wi, week in enumerate(calendar.Calendar(6).monthdayscalendar(cursor.year, cursor.month)):
                for ci, (col, num) in enumerate(zip(st.columns(7), week)):
                    if not num:
                        col.button("빈 날짜", key=f"blank_{wi}_{ci}", disabled=True, use_container_width=True)
                        continue
                    day = cursor.replace(day=num)
                    label = f"{num}" + (" ·" if day.isoformat() in event_days else "")
                    if col.button(label, key="day_" + day.isoformat(), type="primary" if day == chosen else "secondary", use_container_width=True, help=f'{day.isoformat()}{" (오늘)" if day == TODAY else ""}{" · 일정 있음" if day.isoformat() in event_days else ""}'):
                        st.session_state.selected_day = day.isoformat()
                        st.rerun()
        st.caption("· 표시가 있는 날에는 가족 일정이 있어요.")
        if st.button("오늘로 이동"):
            st.session_state.update(month=TODAY.replace(day=1).isoformat(), selected_day=TODAY.isoformat())
            st.rerun()
    with right:
        section(f"{chosen.month}월 {chosen.day}일 ({WEEKDAYS[chosen.weekday()]})")
        if st.button("＋ 이 날의 일정 추가", type="primary", use_container_width=True):
            st.session_state.editor = "new_event"
            st.rerun()
        events = [e for e in DATA["events"] if e["date"] == chosen.isoformat()]
        if not events:
            empty("아직 일정이 없어요. 함께할 약속을 남겨보세요.")
        for e in events:
            card(e["title"], f'{e["who"]} · {e["time"] or "시간·장소 미정"}')
            for i, item in enumerate(e["items"]):
                done = st.checkbox(item["text"], value=item["done"], key=f'prep_{e["id"]}_{i}_{item["done"]}')
                if done != item["done"]:
                    item["done"] = done
                    save("준비물 상태를 저장했어요.")
            a, b = st.columns(2)
            if a.button("일정 수정", key="event_edit_" + e["id"]):
                st.session_state.editor = e["id"]
                st.rerun()
            if b.button("일정 삭제", key="event_delete_" + e["id"]):
                st.session_state.confirm_event = e["id"]
            if st.session_state.get("confirm_event") == e["id"]:
                agree = st.checkbox("이 일정과 준비물을 삭제할게요", key="event_agree_" + e["id"])
                if st.button("일정 삭제하기", key="event_yes_" + e["id"], disabled=not agree):
                    DATA["events"] = [v for v in DATA["events"] if v["id"] != e["id"]]
                    st.session_state.pop("confirm_event", None)
                    save("일정을 삭제했어요.")


def settings_page():
    st.title("우리집을 가꿔요.")
    st.caption("함께할 가족을 등록하고, 소중한 기록을 안전하게 챙기세요.")
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        section("함께하는 가족", f"{len(DATA['members'])} / 30명")
        for i, n in enumerate(DATA["members"]):
            html(f'<div class="person"><div class="avatar" style="background:{PALETTE[i % 5]}">{escape(n[:1])}</div><div class="person-main">{escape(n)}</div><span class="pill neutral">우리 가족</span></div>')
        with st.form("add_member", clear_on_submit=True):
            n = st.text_input("가족 별명 *", max_chars=16, placeholder="예: 엄마, 아빠, 지우")
            if st.form_submit_button("가족 추가", type="primary", use_container_width=True):
                n = n.strip()
                if not n:
                    st.error("가족이 사용할 별명을 적어 주세요.")
                elif n in DATA["members"]:
                    st.error("같은 별명이 있어요. 다른 별명을 적어 주세요.")
                elif len(DATA["members"]) >= 30:
                    st.error("가족은 최대 30명까지 등록할 수 있어요.")
                else:
                    DATA["members"].append(n)
                    save("새로운 가족을 맞이했어요.")
        st.caption("기록을 보호하기 위해 가족 삭제는 제공하지 않아요.")
    with right:
        section("기록 백업")
        st.write("가족의 기록을 파일로 보관해 두세요. 다른 곳에서 다시 시작할 때도 가져올 수 있어요.")
        payload = {"format": "woorijip", "version": 2, "exported_at": datetime.now(KST).isoformat(), "data": DATA}
        st.download_button("전체 기록 다운로드", json.dumps(payload, ensure_ascii=False, indent=2), file_name=f"우리집_백업_{TODAY.isoformat()}.json", mime="application/json", use_container_width=True)
        st.warning("Streamlit Community Cloud에서는 앱 재시작·재배포 시 기록이 사라질 수 있어요. 중요한 기록은 정기적으로 다운로드해 주세요.")
        with st.expander("기존 백업 가져오기"):
            st.caption("이전 버전의 JSON 백업도 지원해요. 가져오면 현재 기록 전체가 바뀌어요.")
            uploaded = st.file_uploader("백업 파일", type=["json"], key="restore_upload")
            candidate = None
            if uploaded is not None:
                if uploaded.size > 5 * 1024 * 1024:
                    st.error("5MB 이하의 백업 파일을 선택해 주세요.")
                else:
                    try:
                        candidate = validate(json.loads(uploaded.getvalue().decode("utf-8-sig")))
                        st.caption(f'가족 {len(candidate["members"])}명 / 부탁 {len(candidate["tasks"])}개 / 일정 {len(candidate["events"])}개')
                    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                        st.error("올바른 우리집 백업 파일이 아니에요. 원본 파일을 다시 선택해 주세요.")
            signature = hashlib.sha256(uploaded.getvalue()).hexdigest() if uploaded is not None else "none"
            agree = st.checkbox("현재 기록이 모두 교체되는 것에 동의해요", key="restore_agree_" + signature)
            if st.button("백업으로 교체", disabled=candidate is None or not agree):
                DATA.clear()
                DATA.update(candidate)
                for key in ("actor", "editor", "confirm_task", "confirm_event"):
                    st.session_state.pop(key, None)
                save("백업을 가져왔어요.")
        section("가족끼리 사용하는 공간")
        st.caption("가족 선택은 로그인 기능이 아니에요. 선택한 별명으로 부탁을 맡고 완료를 확인해요. 주소만으로 접근하지 못하게 하려면 Streamlit 앱의 Secrets에 APP_PASSWORD를 설정해 주세요.")
        st.caption("최신 소식을 보려면 아래 버튼을 눌러 주세요.")
        if st.button("최신 기록 불러오기", use_container_width=True):
            st.rerun()


def gate():
    password = setting("APP_PASSWORD")
    if not password:
        return
    digest = hashlib.sha256(password.encode()).hexdigest()
    if st.session_state.get("access_digest") == digest:
        return
    st.title("우리집에 오신 걸 환영해요.")
    st.caption("가족끼리 공유한 비밀번호로 들어와 주세요.")
    with st.form("access"):
        entered = st.text_input("가족 비밀번호", type="password")
        if st.form_submit_button("우리집 들어가기", type="primary"):
            if hmac.compare_digest(entered.encode(), password.encode()):
                st.session_state.access_digest = digest
                st.rerun()
            else:
                st.error("비밀번호가 달라요. 가족에게 확인해 주세요.")
    st.stop()


def main():
    global DATA, REVISION
    html(CSS)
    gate()
    try:
        DATA, REVISION = load()
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError):
        st.error("우리집 기록을 읽지 못했어요. 원본 저장 파일을 보관한 뒤 저장 공간과 백업 형식을 확인해 주세요. 기록은 자동으로 초기화하지 않았어요.")
        st.stop()
    html(f'<div class="masthead"><div class="brand"><span class="brand-mark">⌂</span>우리집<span class="brand-note">함께 챙기는 하루</span></div><div class="dateline">{TODAY.year}년 {TODAY.month}월 {TODAY.day}일 {WEEKDAYS[TODAY.weekday()]}요일</div></div>')
    if st.session_state.get("flash"):
        st.toast(st.session_state.pop("flash"), icon="✅")
    if st.session_state.get("demo"):
        st.caption("예시 체험 중 · 이름과 기록은 모두 예시이며 실제 기록과 분리돼요.")
        if st.button("체험 종료 · 내 가족 등록"):
            for k in list(st.session_state):
                if k != "access_digest":
                    del st.session_state[k]
            st.rerun()
    st.session_state.setdefault("page", "오늘")
    with st.container(key="navigation"):
        for col, page in zip(st.columns(4), ["오늘", "부탁", "일정", "설정"]):
            label = {"오늘": "⌂ 오늘", "부탁": "♡ 부탁", "일정": "▦ 일정", "설정": "⚙ 설정"}[page]
            if col.button(label, type="primary" if st.session_state.page == page else "secondary", use_container_width=True):
                go(page)
    if not DATA["members"]:
        html('<div class="hero"><div class="hero-label">우리 가족만의 작은 공간</div><div class="hero-title">함께 챙기면<br>더 다정한 하루.</div><div class="hero-note">저녁 소식, 작은 부탁, 가족 일정을 한곳에 모아요.</div>' + ILLUSTRATION + '</div>')
        if st.button("예시로 먼저 둘러보기"):
            st.session_state.update(demo=True, demo_data=demo_data(), demo_revision=0, page="오늘")
            st.rerun()
        settings_page()
    else:
        a, b = st.columns([3, 1])
        a.caption("우리 가족의 일상 노트" + (" · 예시 체험" if st.session_state.get("demo") else ""))
        if st.session_state.get("actor") not in DATA["members"]:
            st.session_state.actor = DATA["members"][0]
        actor = b.selectbox("지금 사용하는 가족", DATA["members"], key="actor", on_change=lambda: st.session_state.pop("editor", None))
        page = st.session_state.page
        if page == "오늘":
            today_page(actor)
        elif page == "부탁":
            tasks_page(actor)
        elif page == "일정":
            calendar_page()
        else:
            settings_page()
    html('<div class="footer"><span>작은 소식을 나누는 곳, 우리집</span><span>기록은 설정에서 백업할 수 있어요.</span></div>')


if __name__ == "__main__":
    main()
