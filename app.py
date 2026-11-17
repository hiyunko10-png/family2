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

st.set_page_config(page_title="우리집 | 함께 챙기는 하루", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).date()
MEALS = ["아직 몰라요", "먹어요", "안 먹어요"]
STATUSES = {"open": "함께할 가족을 찾아요", "claimed": "하고 있어요", "submitted": "확인 기다려요", "approved": "완료했어요"}
WEEKDAYS = "월화수목금토일"
PALETTE = ["#e7eee4", "#faead9", "#e6edf5", "#f1e5eb", "#ede9d9"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&display=swap');
:root {color-scheme:light!important;--text-color:#263c32;--background-color:#f7f8f3;--secondary-background-color:#fff;--primary-color:#2e5943;}
html,body,.stApp {font-family:Pretendard,-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif!important;background:#f7f8f3!important;color:#263c32!important;}
[data-testid="stAppViewContainer"] {background:#f7f8f3!important;}
[data-testid="stHeader"],[data-testid="stToolbar"],footer {display:none!important;}
/* Only the page content is compacted; never hide overflowing form fields or the keyboard. */
.block-container,[data-testid="stMainBlockContainer"] {max-width:470px!important;padding:12px 16px calc(77px + env(safe-area-inset-bottom))!important;}
[data-testid="stVerticalBlock"] {gap:7px!important;}
[data-testid="stHorizontalBlock"] {gap:8px!important;flex-wrap:nowrap!important;}
[data-testid="stColumn"] {min-width:0!important;}
h1,h2,h3,p,label {word-break:keep-all;}
h1 {font-family:'Gowun Batang',serif!important;font-size:23px!important;line-height:1.5!important;padding:2px 0 4px!important;font-weight:700!important;color:#263c32!important;}
h2,h3 {font-size:17px!important;color:#263c32!important;padding:2px 0!important;}
p {font-size:13px;line-height:1.7;}
[data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"],label {color:#263c32!important;}
[data-testid="stWidgetLabel"] p {font-size:12px!important;color:#344f3f!important;}
[data-testid="stCaptionContainer"] p {font-size:11px!important;line-height:1.6!important;color:#586d5e!important;}
button {touch-action:manipulation;}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stFormSubmitButton"] button {border:1px solid #ccd9c9!important;border-radius:10px!important;min-height:40px!important;background:#fff!important;color:#294d3b!important;box-shadow:none!important;padding:5px 9px!important;}
button p,button span {color:inherit!important;-webkit-text-fill-color:currentColor!important;font-size:13px!important;}
button[kind="primary"],button[kind="primaryFormSubmit"] {background:#2e5943!important;border-color:#2e5943!important;color:#fff!important;}
button[kind="primary"] *,button[kind="primaryFormSubmit"] * {color:#fff!important;-webkit-text-fill-color:#fff!important;}
button:disabled {opacity:.5;}
button:focus-visible,input:focus-visible,textarea:focus-visible {outline:3px solid #b57a35!important;outline-offset:2px;}
[data-testid="stForm"] {border:1px solid #dce4d9!important;border-radius:14px!important;background:#fff!important;padding:12px!important;}
/* Override foreground AND background, including inherited WebKit text fills and portals. */
input,textarea,[contenteditable="true"] {background:#fff!important;color:#243b30!important;-webkit-text-fill-color:#243b30!important;caret-color:#243b30!important;opacity:1!important;font-size:16px!important;}
input::placeholder,textarea::placeholder {color:#6b786f!important;-webkit-text-fill-color:#6b786f!important;opacity:1!important;}
input::selection,textarea::selection {background:#d7e9cb!important;color:#183c29!important;-webkit-text-fill-color:#183c29!important;}
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div {background:#fff!important;border-color:#c7d5c5!important;color:#243b30!important;border-radius:9px!important;}
[data-baseweb="select"] div,[data-baseweb="select"] span {background:#fff!important;color:#243b30!important;-webkit-text-fill-color:#243b30!important;}
[data-baseweb="select"] svg {fill:#385641!important;color:#385641!important;}
/* Streamlit 1.67+ uses React Aria; older 1.x uses BaseWeb above. */
[data-testid="stSelectbox"] [role="group"] {background:#fff!important;color:#243b30!important;border-color:#c7d5c5!important;}
[data-testid="stSelectbox"] button {background:#fff!important;color:#385641!important;border:0!important;}
[data-testid="stSelectbox"] button svg {color:#385641!important;fill:#385641!important;}
[data-testid="stSelectbox"] [role="group"][data-focus-within] {border-color:#2e5943!important;}
[data-testid="stTextInput"] button {background:#fff!important;color:#385641!important;}
[data-testid="stDateInput"] [role="group"] {background:#fff!important;color:#243b30!important;}
[data-testid="stDateInputField"],[data-testid="stDateInputField"] *,[data-testid="stDateInputCalendarButton"] {background:#fff!important;color:#243b30!important;-webkit-text-fill-color:#243b30!important;}
[data-testid="stDateInputCalendar"],[data-testid="stDateInputCalendar"] * {background-color:#fff!important;color:#243b30!important;-webkit-text-fill-color:#243b30!important;}
[data-testid="stDateInputCalendar"] [aria-selected="true"],[data-testid="stDateInputCalendar"] [data-selected="true"], [data-testid="stDateInputCalendar"] [aria-selected="true"] * {background-color:#dcebcf!important;color:#1d402a!important;}
[role="spinbutton"]:focus-visible {outline:2px solid #2e5943!important;outline-offset:1px;}
[data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"],[role="option"],[data-baseweb="calendar"] {background:#fff!important;color:#243b30!important;color-scheme:light!important;}
[data-baseweb="popover"] *,[data-baseweb="menu"] *,[role="listbox"] *,[role="option"] * {color:#243b30!important;-webkit-text-fill-color:#243b30!important;}
[role="option"][aria-selected="true"],[role="option"]:hover,[data-baseweb="menu"] li:hover {background:#e1edda!important;color:#183c29!important;}
[data-testid="stRadio"] label p,[data-testid="stCheckbox"] label p {color:#263c32!important;-webkit-text-fill-color:#263c32!important;font-size:12px!important;}
[data-testid="stRadioOption"] > div > div:first-child {background:#fff!important;border-color:#739076!important;}
[data-testid="stRadioOption"][data-selected="true"] > div > div:first-child {background:#2e5943!important;border-color:#2e5943!important;}
[data-testid="stRadioOption"][data-selected="true"] > div > div:first-child > div {background:#fff!important;}
[data-testid="stCheckbox"] label > div:first-of-type {background:#fff!important;border:1px solid #739076!important;}
[data-testid="stCheckbox"] label:has(input:checked) > div:first-of-type {background:#2e5943!important;border-color:#2e5943!important;}
[data-testid="stCheckbox"] label:has(input:checked) svg {color:#fff!important;fill:#fff!important;}
[data-testid="stToast"] {background:#fff!important;color:#263c32!important;border:1px solid #c7d5c5!important;}
[data-testid="stToast"] * {color:#263c32!important;-webkit-text-fill-color:#263c32!important;}
[data-testid="stFileUploaderDropzone"] {background:#fff!important;color:#263c32!important;padding:10px!important;}
[data-testid="stFileUploaderDropzone"] * {color:#263c32!important;}
[data-testid="stFileChip"],[data-testid="stFileUploaderFile"] {background:#eaf1e4!important;border:1px solid #cfddc8!important;}
[data-testid="stFileChip"] *,[data-testid="stFileUploaderFile"] * {color:#263c32!important;-webkit-text-fill-color:#263c32!important;}
[data-testid="stFileUploader"] button {background:#fff!important;color:#385641!important;}
[data-testid="InputInstructions"],[data-testid="stInputInstructions"] {display:none!important;}
[data-testid="stAlert"] {padding:8px 10px!important;border-radius:10px;background:#fff2d9!important;color:#594522!important;}
[data-testid="stAlert"] * {color:#594522!important;-webkit-text-fill-color:#594522!important;}
[data-testid="stAlert"] p {font-size:12px!important;}
.masthead {display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #dce3d8;padding-bottom:9px;margin-bottom:2px;}
.brand {display:flex;align-items:center;gap:8px;font-size:21px;font-weight:800;}
.brand-mark {width:29px;height:29px;background:#2e5943;border-radius:9px;display:grid;place-items:center;color:#fff;font-size:20px;}
.dateline {font-size:11px;color:#586d5e;}
.st-key-navigation {position:fixed!important;bottom:0;left:50%;transform:translateX(-50%);width:min(100%,470px)!important;z-index:100;background:#f7f8f3!important;border-top:1px solid #d3decd;padding:9px 12px calc(9px + env(safe-area-inset-bottom));}
.st-key-navigation [data-testid="stColumn"] {width:0!important;flex:1 1 0!important;}
.st-key-navigation button {border:0!important;background:transparent!important;}
.st-key-navigation button[kind="primary"] {background:#e1ebd9!important;color:#254c36!important;}
.st-key-navigation button[kind="primary"] * {color:#254c36!important;-webkit-text-fill-color:#254c36!important;}
.st-key-profile [data-testid="stWidgetLabel"] {display:none;}
.st-key-profile [data-testid="stColumn"]:first-child {flex:1.2 1 0!important;}
.st-key-profile [data-testid="stColumn"]:last-child {flex:1 1 0!important;}
.profile-label {line-height:40px;font-size:12px;color:#586d5e;}
.hero {position:relative;overflow:hidden;border-radius:16px;background:#e6eedf;min-height:99px;padding:13px 16px;}
.hero-label {font-size:11px;color:#4c6348;}
.hero-title {font-family:'Gowun Batang',serif;font-size:23px;font-weight:700;line-height:1.5;margin:3px 0;color:#244733;max-width:75%;}
.hero-note {font-size:11px;color:#4c6348;max-width:73%;}
.hero svg {position:absolute;width:106px;right:2px;bottom:-1px;}
.sectionline {display:flex;align-items:center;justify-content:space-between;margin:4px 0;}
.sectionline strong {font-size:15px;}.sectionline span {font-size:11px;color:#586d5e;}
.person {display:flex;gap:11px;align-items:center;padding:15px;background:#fff;border:1px solid #dce4d9;border-radius:13px;}
.avatar {display:grid;place-items:center;width:38px;height:38px;border-radius:50%;font-size:15px;font-weight:700;flex-shrink:0;}
.person-main {flex:1;min-width:0;overflow-wrap:anywhere;font-size:14px;font-weight:600;}
.person-main small {display:block;font-size:12px;font-weight:400;color:#586d5e;margin-top:3px;}
.pill {display:inline-block;border-radius:6px;padding:3px 7px;font-size:11px;background:#e8efdf;color:#3c5c30;font-weight:600;}
.pill.neutral {background:#edf0eb;color:#506453;}.pill.amber {background:#f8ecd8;color:#795223;}
.note-card {background:#fff;border:1px solid #dce4d9;border-radius:14px;padding:14px 16px;}
.note-card .title {font-size:17px;font-weight:700;line-height:1.55;overflow-wrap:anywhere;}
.note-card .meta {font-size:12px;color:#586d5e;margin-top:6px;line-height:1.6;overflow-wrap:anywhere;}
.note-card .reward {border-top:1px dashed #dbe2d4;margin-top:10px;padding-top:9px;font-size:13px;color:#73562b;overflow-wrap:anywhere;}
.empty {padding:22px 15px;border:1px dashed #c5d5bf;border-radius:13px;color:#506651;text-align:center;font-size:13px;line-height:1.8;background:#f0f4e9;}
.pager-count {text-align:center;font-size:12px;color:#586d5e;line-height:40px;}
.st-key-calendar {padding:8px;border:1px solid #dce4d7;border-radius:14px;background:#fff;}
.st-key-calendar [data-testid="stVerticalBlock"] {gap:2px!important;}
.st-key-calendar [data-testid="stHorizontalBlock"] {gap:3px!important;}
.st-key-calendar [data-testid="stColumn"] {width:0!important;flex:1 1 0!important;}
.st-key-calendar button {padding:0!important;border:0!important;min-height:34px!important;height:34px!important;}
.st-key-calendar button:disabled {visibility:hidden;}
.weekday {text-align:center;color:#586d5e;font-size:11px;line-height:22px;}
.calendar-title {font-size:17px;font-weight:700;text-align:center;line-height:40px;}
.st-key-monthnav button {padding:0 4px!important;}.st-key-monthnav button p {font-size:12px!important;white-space:nowrap;}
/* Small-height phones still retain a safe scrolling fallback for keyboards / zoom. */
@media(max-height:700px) {
 .block-container,[data-testid="stMainBlockContainer"] {padding-top:8px!important;}
 [data-testid="stVerticalBlock"] {gap:5px!important;}
 h1 {font-size:21px!important;}.hero {min-height:84px;padding:10px 14px;}.hero-title {font-size:21px;}
 .hero svg {width:90px;}.st-key-calendar button {min-height:30px!important;height:30px!important;}
 [data-testid="stForm"] {padding:10px!important;}
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
    st.session_state.pop("event_draft_id", None)
    st.rerun()


def pager(items, key):
    """한 번에 하나만 보여 주므로 가족과 기록이 늘어도 화면은 길어지지 않아요."""
    if not items:
        return None
    position = min(st.session_state.get(key, 0), len(items) - 1)
    if len(items) > 1:
        a, b, c = st.columns([1, 2, 1])
        if a.button("이전", key=key + "_prev", disabled=position == 0, use_container_width=True):
            st.session_state[key] = position - 1
            st.rerun()
        b.markdown(f'<div class="pager-count">{position + 1} / {len(items)}</div>', unsafe_allow_html=True)
        if c.button("다음", key=key + "_next", disabled=position == len(items) - 1, use_container_width=True):
            st.session_state[key] = position + 1
            st.rerun()
    return items[position]


def today_page(actor: str):
    entries = DATA["days"].get(TODAY.isoformat(), {})
    count = sum(entries.get(n, {}).get("meal") == "먹어요" for n in DATA["members"])
    pending = sum(entries.get(n, {}).get("meal", "아직 몰라요") == "아직 몰라요" for n in DATA["members"])
    note = f'{pending}명은 아직 미정이에요.' if pending else '모두의 저녁 소식이 도착했어요.'
    html(f'<div class="hero"><div class="hero-label">오늘 저녁, 우리집 식탁</div><div class="hero-title">{count}명이 함께 먹어요.</div><div class="hero-note">{note}</div>' + ILLUSTRATION + '</div>')
    mode = st.radio("오늘 보기", ["내 소식", "가족 소식", "다가오는 일정"], horizontal=True, label_visibility="collapsed")
    if mode == "내 소식":
        current = entries.get(actor, {})
        with st.form(f"meal_{actor}_{TODAY}"):
            meal = st.radio("오늘 저녁은요?", MEALS, index=MEALS.index(current.get("meal", MEALS[0])), horizontal=True)
            options = arrival_options()
            arrival = st.selectbox("언제 집에 오나요?", options, index=options.index(current.get("arrival", "미정")), format_func=clock)
            if st.form_submit_button("내 소식 저장", type="primary", use_container_width=True):
                DATA["days"].setdefault(TODAY.isoformat(), {})[actor] = {"meal": meal, "arrival": arrival}
                save("가족에게 내 저녁 소식을 전했어요.")
        st.caption("가족의 소식은 ‘가족 소식’에서 넘겨 볼 수 있어요.")
    elif mode == "가족 소식":
        n = pager(DATA["members"], "today_family")
        e = entries.get(n, {})
        meal = e.get("meal", "아직 몰라요")
        i = DATA["members"].index(n)
        html(f'<div class="person"><div class="avatar" style="background:{PALETTE[i % 5]}">{escape(n[:1])}</div><div class="person-main">{escape(n)}<small>귀가　{escape(clock(e.get("arrival", "미정")))}</small></div><span class="pill">{escape(meal)}</span></div>')
        active = sum(t["status"] != "approved" for t in DATA["tasks"])
        st.caption(f"가족의 작은 부탁 {active}개가 진행 중이에요.")
        if st.button("부탁 보러 가기", use_container_width=True):
            go("부탁")
    else:
        events = sorted([e for e in DATA["events"] if e["date"] >= TODAY.isoformat()], key=lambda e: (e["date"], e["time"]))
        e = pager(events, "upcoming_event")
        if e:
            when = date.fromisoformat(e["date"])
            card(e["title"], f'{e["who"]} · {e["time"] or "시간·장소 미정"}', "오늘" if when == TODAY else f"{when.month}월 {when.day}일 ({WEEKDAYS[when.weekday()]})")
        else:
            empty("함께할 다음 일정을 등록해 보세요.")
        if st.button("가족 캘린더 보기", use_container_width=True):
            go("일정")


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
    editor = st.session_state.get("editor", "")
    original = next((t for t in DATA["tasks"] if t["id"] == editor and t["created"] == actor and t["status"] == "open"), None)
    if editor == "new_task" or original:
        task_editor(actor, original)
        return
    if st.button("＋ 새로운 부탁", type="primary"):
        st.session_state.editor = "new_task"
        st.rerun()
    category = st.radio("부탁 목록", ["진행 중", "확인 대기", "완료"], horizontal=True, label_visibility="collapsed")
    only_mine = st.checkbox("내가 부탁하거나 맡은 일만 보기")
    tasks = [t for t in reversed(DATA["tasks"]) if (t["status"] in ("open", "claimed") if category == "진행 중" else t["status"] == "submitted" if category == "확인 대기" else t["status"] == "approved") and (not only_mine or actor in (t["owner"], t["created"]))]
    if not tasks:
        empty("여기는 아직 조용해요. 새로운 부탁을 남겨보세요.")
    selected = pager(tasks, f"task_page_{category}_{actor}_{only_mine}")
    if selected:
        t = selected
        with st.container():
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
    token = st.session_state.editor
    if st.session_state.get("event_draft_id") != token:
        st.session_state.event_draft_id = token
        st.session_state.event_step = 1
        st.session_state.event_draft = {"title": original["title"] if original else "", "date": original["date"] if original else chosen.isoformat(),
            "who": original["who"] if original else "가족 모두", "time": original["time"] if original else "",
            "prep": "\n".join(i["text"] for i in original["items"]) if original else ""}
    draft = st.session_state.event_draft
    step = st.session_state.event_step
    st.caption(f"{step} / 2단계 · {'일정 정보' if step == 1 else '장소와 준비물'}")
    if step == 1:
        with st.form("event_basics"):
            title = st.text_input("일정 이름 *", value=draft["title"], max_chars=70, placeholder="예: 함께하는 주말 피크닉")
            when = st.date_input("날짜", value=date.fromisoformat(draft["date"]))
            people = ["가족 모두"] + DATA["members"]
            who = st.selectbox("함께하는 가족", people, index=people.index(draft["who"]))
            if st.form_submit_button("다음 · 장소와 준비물", type="primary", use_container_width=True):
                if not title.strip():
                    st.error("일정 이름을 적어 주세요.")
                else:
                    draft.update(title=title.strip(), date=when.isoformat(), who=who)
                    st.session_state.event_step = 2
                    st.rerun()
    else:
        with st.form("event_details"):
            place = st.text_input("시간 · 장소", value=draft["time"], max_chars=100, placeholder="예: 오전 11시 · 동네 공원")
            prep = st.text_area("준비물 (한 줄에 하나씩)", value=draft["prep"], max_chars=2000, height=100, placeholder="예: 돗자리\n도시락")
            previous = st.form_submit_button("이전 · 일정 정보", use_container_width=True)
            submit = st.form_submit_button("일정 수정" if original else "일정 등록", type="primary", use_container_width=True)
        if previous:
            draft.update(time=place.strip(), prep=prep)
            st.session_state.event_step = 1
            st.rerun()
        if submit:
            labels = [s.strip() for s in prep.splitlines() if s.strip()]
            if len(labels) > 50 or any(len(s) > 100 for s in labels):
                st.error("준비물은 50개까지, 각각 100자 이내로 적어 주세요.")
            else:
                old_checks = {i["text"]: i["done"] for i in original["items"]} if original else {}
                values = {"title": draft["title"], "date": draft["date"], "who": draft["who"], "time": place.strip(),
                    "items": [{"text": s, "done": old_checks.get(s, False)} for s in dict.fromkeys(labels)]}
                if original:
                    original.update(values)
                else:
                    DATA["events"].append({"id": new_id(), **values})
                when = date.fromisoformat(draft["date"])
                st.session_state.update(selected_day=when.isoformat(), month=when.replace(day=1).isoformat(), calendar_mode="선택일 일정")
                st.session_state.pop("editor", None)
                st.session_state.pop("event_draft_id", None)
                save("가족 일정을 저장했어요.")
    if st.button("캘린더로 돌아가기"):
        st.session_state.pop("editor", None)
        st.session_state.pop("event_draft_id", None)
        st.rerun()


def calendar_page():
    st.title("우리집 캘린더")
    st.session_state.setdefault("month", TODAY.replace(day=1).isoformat())
    st.session_state.setdefault("selected_day", TODAY.isoformat())
    cursor = date.fromisoformat(st.session_state.month)
    chosen = date.fromisoformat(st.session_state.selected_day)
    editor = st.session_state.get("editor")
    original = next((e for e in DATA["events"] if e["id"] == editor), None)
    if editor == "new_event" or original:
        event_editor(chosen, original)
        return
    if st.session_state.pop("calendar_jump", False):
        st.session_state.calendar_mode = "선택일 일정"
    mode = st.radio("일정 보기", ["달력", "선택일 일정"], horizontal=True, label_visibility="collapsed", key="calendar_mode")
    if mode == "달력":
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
                        st.session_state.calendar_jump = True
                        st.rerun()
        st.caption("날짜를 누르면 그날의 일정을 볼 수 있어요. · 일정 있음")
        if st.button("오늘로 이동"):
            st.session_state.update(month=TODAY.replace(day=1).isoformat(), selected_day=TODAY.isoformat())
            st.rerun()
    else:
        section(f"{chosen.month}월 {chosen.day}일 ({WEEKDAYS[chosen.weekday()]})")
        if st.button("＋ 이 날의 일정 추가", type="primary", use_container_width=True):
            st.session_state.editor = "new_event"
            st.rerun()
        events = [e for e in DATA["events"] if e["date"] == chosen.isoformat()]
        if not events:
            empty("아직 일정이 없어요. 함께할 약속을 남겨보세요.")
        e = pager(events, "event_page_" + chosen.isoformat())
        if e:
            card(e["title"], f'{e["who"]} · {e["time"] or "시간·장소 미정"}')
            item_index = pager(list(range(len(e["items"]))), "prep_page_" + e["id"])
            if item_index is not None:
                item = e["items"][item_index]
                done = st.checkbox("준비물 · " + item["text"], value=item["done"], key=f'prep_{e["id"]}_{item_index}_{item["done"]}')
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
    mode = st.radio("설정 메뉴", ["가족", "백업", "복원", "안내"], horizontal=True, label_visibility="collapsed")
    if mode == "가족":
        section("함께하는 가족", f"{len(DATA['members'])} / 30명")
        n = pager(DATA["members"], "settings_family")
        if n:
            i = DATA["members"].index(n)
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
    elif mode == "백업":
        section("기록 백업")
        st.write("가족의 기록을 파일로 보관해 두세요. 다른 곳에서 다시 시작할 때도 가져올 수 있어요.")
        payload = {"format": "woorijip", "version": 2, "exported_at": datetime.now(KST).isoformat(), "data": DATA}
        st.download_button("전체 기록 다운로드", json.dumps(payload, ensure_ascii=False, indent=2), file_name=f"우리집_백업_{TODAY.isoformat()}.json", mime="application/json", use_container_width=True)
        st.warning("앱 재시작·재배포 시 기록이 사라질 수 있어요. 중요한 기록은 정기적으로 백업해 주세요.")
    elif mode == "복원":
        st.caption("이전 JSON 백업도 지원해요. 현재 기록 전체가 바뀌어요.")
        uploaded = st.file_uploader("백업 파일 (5MB 이하)", type=["json"], key="restore_upload")
        candidate = None
        if uploaded is not None:
            if uploaded.size > 5 * 1024 * 1024:
                st.error("5MB 이하의 백업 파일을 선택해 주세요.")
            else:
                try:
                    candidate = validate(json.loads(uploaded.getvalue().decode("utf-8-sig")))
                    st.caption(f'가족 {len(candidate["members"])}명 / 부탁 {len(candidate["tasks"])}개 / 일정 {len(candidate["events"])}개')
                except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                    st.error("올바른 우리집 백업 파일이 아니에요.")
        signature = hashlib.sha256(uploaded.getvalue()).hexdigest() if uploaded is not None else "none"
        agree = st.checkbox("현재 기록이 모두 교체되는 것에 동의해요", key="restore_agree_" + signature)
        if st.button("백업으로 교체", disabled=candidate is None or not agree):
            DATA.clear()
            DATA.update(candidate)
            for key in ("actor", "editor", "confirm_task", "confirm_event", "event_draft_id"):
                st.session_state.pop(key, None)
            save("백업을 가져왔어요.")
    else:
        section("가족끼리 사용하는 공간")
        st.caption("가족 선택은 로그인 기능이 아니에요. 선택한 별명으로 부탁을 맡고 완료를 확인해요. 주소만으로 접근하지 못하게 하려면 Streamlit 앱의 Secrets에 APP_PASSWORD를 설정해 주세요.")
        st.caption("최신 소식을 보려면 아래 버튼을 눌러 주세요.")
        if st.button("최신 기록 불러오기", use_container_width=True):
            st.rerun()
        if st.session_state.get("demo") and st.button("체험 종료 · 내 가족 등록", use_container_width=True):
            for key in list(st.session_state):
                if key != "access_digest":
                    del st.session_state[key]
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
    date_label = f"{TODAY.month}월 {TODAY.day}일 {WEEKDAYS[TODAY.weekday()]}요일"
    if st.session_state.get("demo"):
        date_label = "예시 체험 · " + date_label
    html(f'<div class="masthead"><div class="brand"><span class="brand-mark">⌂</span>우리집</div><div class="dateline">{date_label}</div></div>')
    if st.session_state.get("flash"):
        st.toast(st.session_state.pop("flash"), icon="✅")
    st.session_state.setdefault("page", "오늘")
    with st.container(key="navigation"):
        for col, page in zip(st.columns(4), ["오늘", "부탁", "일정", "설정"]):
            label = {"오늘": "⌂ 오늘", "부탁": "♡ 부탁", "일정": "▦ 일정", "설정": "⚙ 설정"}[page]
            if col.button(label, type="primary" if st.session_state.page == page else "secondary", use_container_width=True):
                go(page)
    if not DATA["members"]:
        html('<div class="hero"><div class="hero-label">우리 가족만의 작은 공간</div><div class="hero-title">함께 챙기는 하루.</div><div class="hero-note">저녁 소식, 부탁, 가족 일정을 한곳에 모아요.</div>' + ILLUSTRATION + '</div>')
        if st.button("예시로 먼저 둘러보기"):
            st.session_state.update(demo=True, demo_data=demo_data(), demo_revision=0, page="오늘")
            st.rerun()
        settings_page()
    else:
        if st.session_state.get("actor") not in DATA["members"]:
            st.session_state.actor = DATA["members"][0]
        with st.container(key="profile"):
            a, b = st.columns([1.2, 1])
            a.markdown('<div class="profile-label">지금 사용하는 가족</div>', unsafe_allow_html=True)
            actor = b.selectbox("지금 사용하는 가족", DATA["members"], key="actor", label_visibility="collapsed", on_change=lambda: st.session_state.pop("editor", None))
        page = st.session_state.page
        if page == "오늘":
            today_page(actor)
        elif page == "부탁":
            tasks_page(actor)
        elif page == "일정":
            calendar_page()
        else:
            settings_page()


if __name__ == "__main__":
    main()
