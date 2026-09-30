# -*- coding: utf-8 -*-
"""하단 예약 바 «가장 빠른 빈 시간»(대표 09-30 결정 · 9a 전달) — A룸·B룸·홈 두 버튼·룸 페이지 바.

조건(대표): ① availability.json 과 같은 데이터로 2시간 이상 연달아 비는 칸 중 가장 이른 시작 시각
② 새벽 제외 — 근거: 정본(운영정책 §0·§2, 가격정책 v6 §5)은 새벽 포함 24시간 예약이라 시간대 제한 조항이 없다.
   그래서 실제 예약 시작 분포(예약 로그 138행, 취소 제외 126건: 1~7시 시작 0건, 0~8시 시작 A 5건 중 유료 2건)와
   09-30 대표 결정(도어락 «0시~8시 59분 시작»을 새벽으로 따로 묶음)을 근거로 9시 이후 시작만 센다.
   마지막 시작은 22시(2시간이 같은 날 24시 안에 끝남 · 정시 입퇴실 가격정책 §5).
③ 지금 이후만(오늘·내일 표기) ④ 빈 칸 없음·데이터 못 읽음·표시 범위 밖이면 원래 문구(거짓 안내 금지)
⑤ 320px 두 줄·aria-label 동시 변경. 시각은 전부 고정(Date.parse)이라 날짜가 지나도 깨지지 않는다.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
JS = (ROOT / "avail-label.js").read_text(encoding="utf-8") if (ROOT / "avail-label.js").exists() else ""


def _run(expr):
    code = "var window={};var document=undefined;" + JS + "\nprocess.stdout.write(JSON.stringify(" + expr + "));"
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def first(events, now_iso, room="A"):
    return _run("window.nvFirstFree(" + json.dumps(events) + ", Date.parse(" + json.dumps(now_iso) + "), " + json.dumps(room) + ")")


def text(events, now_iso, room="A"):
    return _run("window.nvFreeText(window.nvFirstFree(" + json.dumps(events) + ", Date.parse(" + json.dumps(now_iso) + "), " + json.dumps(room) + "))")


def ev(date, s, e, room="A", kind="booking"):
    return {"date": date, "start": s, "end": e, "room": room, "kind": kind}


def test_constants_pinned_with_evidence():
    assert re.search(r"DAY_START\s*=\s*9\b", JS), "새벽 제외 = 9시 이후 시작(근거는 이 파일 머리말)"
    assert re.search(r"LAST_START\s*=\s*22\b", JS)
    assert re.search(r"MIN_H\s*=\s*2\b", JS)
    m = re.search(r"HORIZON_DAYS\s*=\s*(\d+)", JS)
    b = re.search(r"days=(\d+)\)", (ROOT / "build_availability.py").read_text(encoding="utf-8").split("horizon = today")[1])
    assert m and b and int(m.group(1)) <= int(b.group(1)), "표시 범위는 availability.json 이 받아 오는 범위 안이어야 한다"


def test_today_next_full_hour_after_now():
    # 2026-10-01(목) 13:20 KST → 오늘 14시
    assert text([], "2026-10-01T04:20:00Z") == "오늘 14시"


def test_before_day_start_shows_nine_not_dawn():
    # 03:10 KST, 빈 날 → 오늘 9시(3시가 아님)
    assert text([], "2026-09-30T18:10:00Z") == "오늘 9시"


def test_skips_gap_shorter_than_two_hours():
    now = "2026-10-01T01:00:00Z"   # 10:00 KST
    busy = [ev("2026-10-01", 11, 12), ev("2026-10-01", 13, 18)]
    # 10~11 은 1시간뿐, 12~13 도 1시간 → 18시
    assert first(busy, now)["hour"] == 18


def test_late_night_rolls_to_tomorrow():
    # 21:30 KST → 오늘은 22시 시작만 가능(22~24). 22~24 가 막혀 있으면 내일 9시
    now = "2026-10-01T12:30:00Z"
    assert text([], now) == "오늘 22시"
    assert text([ev("2026-10-01", 22, 24)], now) == "내일 9시"


def test_full_block_today_then_morning_booking_tomorrow():
    now = "2026-10-03T02:00:00Z"   # 10/3(토) 11:00 KST
    busy = [ev("2026-10-03", 0, 24, kind="block"), ev("2026-10-04", 9, 12)]
    assert text(busy, now) == "내일 12시"


def test_weekday_label_after_tomorrow_and_weekend_crossing():
    now = "2026-10-03T14:00:00Z"   # 10/3(토) 23:00 KST
    busy = [ev("2026-10-04", 0, 24, kind="block")]
    # 오늘 남은 시간 없음, 내일(일) 종일 차단 → 10/5(월) 9시
    assert text(busy, now) == "10/5(월) 9시"
    # KST 날짜가 바뀌는 순간(15:00Z) = 10/4 0시 → 그날 종일 차단이면 «내일»은 10/5
    assert text(busy, "2026-10-03T15:00:00Z") == "내일 9시"


def test_nothing_within_horizon_returns_null():
    now = "2026-10-01T01:00:00Z"
    days = [f"2026-10-{d:02d}" for d in range(1, 32)]
    busy = [ev(d, 0, 24, kind="block") for d in days]
    assert first(busy, now) is None
    assert text(busy, now) is None


def test_bad_data_returns_null():
    assert first(None, "2026-10-01T01:00:00Z") is None
    assert first([{"date": "2026-10-01", "start": "x", "end": 12, "room": "A"}], "2026-10-01T01:00:00Z") is None


def test_b_uses_only_b_events():
    now = "2026-10-01T04:20:00Z"
    busy = [ev("2026-10-01", 14, 24, room="A")]
    assert text(busy, now, "B") == "오늘 14시"
    assert text(busy, now, "A") == "내일 9시"


def test_label_and_aria_applied_and_fallback_restores_default():
    code = r"""
var made=[];
function el(txt){var e={textContent:txt,attrs:{'aria-label':'A룸 예약 — 아워플레이스로 이동'},dataset:{},children:[],cls:{},
  getAttribute:function(k){return this.attrs[k]},setAttribute:function(k,v){this.attrs[k]=v},
  appendChild:function(c){this.children.push(c);this.textContent=(this.textContent||'')+c.textContent},
  classList:{toggle:function(){}}};e.classList.toggle=function(c,on){e.cls[c]=!!on};return e;}
var document={createElement:function(){return {textContent:'',className:''};}};
var a=el('A룸 예약 →');
window.nvApplyFreeLabel(a,'A룸','A',[],Date.parse('2026-10-01T04:20:00Z'));
var r1=[a.textContent,a.attrs['aria-label'],a.cls.wk2];
window.nvApplyFreeLabel(a,'A룸','A',null,Date.parse('2026-10-01T04:20:00Z'));
var r2=[a.textContent,a.attrs['aria-label'],a.cls.wk2];
process.stdout.write(JSON.stringify([r1,r2]));
"""
    full = "var window={};" + JS.replace("var document", "var _unused_document") + code
    out = subprocess.run(["node", "-e", full], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    r1, r2 = json.loads(out.stdout)
    assert r1[0] == "A룸 예약 · 빠른 빈 시간오늘 14시 →"
    assert r1[1] == "A룸 예약, 가장 빠른 빈 시간 오늘 14시 — 아워플레이스로 이동"
    assert r1[2] is True
    assert r2 == ["A룸 예약 →", "A룸 예약 — 아워플레이스로 이동", False]


def test_wired_on_hub_and_room_pages_without_touching_hrefs():
    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    tpl = (ROOT / "room.template.html").read_text(encoding="utf-8")
    assert '<script src="/avail-label.js"' in hub and '<script src="/avail-label.js"' in tpl
    assert "nvApplyFreeLabels" in hub[hub.index("function loadAvailability"):]
    assert "['book-side','book-a','end-a','book-mobile']" in hub, "href·계측 배선 불변"
    assert "aweek-js" not in hub and "nvAFreeThisWeek" not in hub, "옛 «이번 주» 문구 함수는 은퇴"
    assert "avail-label.js" in (ROOT / "build_fonts.py").read_text(encoding="utf-8"), "새 문구 글자를 서브셋에"
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert re.search(r"\.sticky-book a\.wk2\{[^}]*flex-direction:column", css)
