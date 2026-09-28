# -*- coding: utf-8 -*-
"""09-28 push 묶음 나머지 — 검수에서 «한 번에 push» 규칙(대표 결정 15)에 맞춰 같은 브랜치에 얹은 것들.

1) 오시는 길 «아워플레이스 메시지»가 제목이라 눌러도 무반응 → FAQ 아래와 같은 문의 링크(계측 포함).
2) PC 룸 섹션 A 가격 옆 «A룸 예약 →» 링크(계측 포함). B 는 무변경 창(10/12까지)이라 건드리지 않는다.
3) «1~4인 단독 대관 / 기본인원은 4인» → «기준 4인, 초과 시 인원요금, 단체는 문의». 히어로 «무인 단독 대관»도.
   b.html·rooms.json B 항목은 B 무변경 창이라 이 테스트 범위 밖이다.
4) privacy.html — 관심 접수 양식은 08-09 에 랜딩에서 내렸다. 지금은 받지 않는다는 사실을 적는다.
5) 모바일 하단 바 A 버튼 — A룸에 이번 주(한국 시간, 일요일까지) 2시간 이상 빈 칸이 실제로 있을 때만
   «A룸 이번 주 남은 시간 보기 →». 데이터가 없거나 빈 칸이 없으면 원래 문구. href 는 그대로(계측 불변).
"""
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
NEW_PAX = "기준 4인, 초과 시 인원요금, 단체는 문의"


def _read(name):
    return open(os.path.join(HERE, name), encoding="utf-8").read()


# ── 1) 오시는 길 문의 링크 ─────────────────────────────────────
def test_directions_inquiry_is_a_tracked_link():
    html = _read("index.html")
    start = html.index('id="location"') if 'id="location"' in html else html.index("까치산역 도보 10분</h3>")
    block = html[start:start + 4000]
    m = re.search(r'<a\b[^>]*data-hp="a\|directions_inquiry"[^>]*>(.*?)</a>', block, re.S)
    assert m, "오시는 길 문의 칸에 계측된 아워플레이스 링크가 없다"
    assert 'href="https://www.hourplace.co.kr/place/61823"' in m.group(0)
    assert "아워플레이스 메시지" in m.group(1)


# ── 2) A 가격 옆 예약 링크 ─────────────────────────────────────
def _booking_info(html, room):
    start = html.index(f'id="roomInfoTitle{room}"')
    return html[start:html.index(f'id="roomInfoBook{room}"', start)]


def test_room_a_price_has_tracked_booking_link():
    info = _booking_info(_read("index.html"), "A")
    m = re.search(r'<a\b[^>]*data-hp="a\|price_link"[^>]*>(.*?)</a>', info, re.S)
    assert m, "A룸 가격 옆 예약 링크가 없다"
    assert 'href="https://www.hourplace.co.kr/place/61823"' in m.group(0)
    assert "A룸 예약" in m.group(1)


def test_room_b_booking_info_untouched():
    info = _booking_info(_read("index.html"), "B")
    assert "hourplace.co.kr" not in info and "data-hp" not in info


# ── 3) 인원 문구 ───────────────────────────────────────────────
def test_pax_wording_replaced_in_hub_and_llms():
    html = _read("index.html")
    llms = _read("llms.txt")
    for old in ("1~4인 단독 대관", "기본인원은 4인", "무인 단독 대관"):
        assert old not in html, f"index.html 에 옛 문구가 남아 있다: {old}"
    assert "1~4인" not in llms, "llms.txt 에 «1~4인»이 남아 있다"
    assert html.count(NEW_PAX) >= 3, "FAQ(JSON-LD·본문)·룸 섹션에 새 문구가 모두 들어가야 한다"
    assert NEW_PAX in llms


# ── 4) 처리방침 ────────────────────────────────────────────────
def test_privacy_says_interest_form_is_not_offered_now():
    p = _read("privacy.html")
    assert "현재 웹사이트에서는 관심 접수 양식을 운영하지 않습니다" in p
    assert "자사몰에서는 선택적으로 관심·예약 알림을 접수합니다" not in p


# ── 5) 모바일 하단 바 A 문구 ───────────────────────────────────
def _week_js():
    html = _read("index.html")
    m = re.search(r'<script id="aweek-js">(.*?)</script>', html, re.S)
    assert m, "모바일 하단 바 A 문구 스크립트(#aweek-js)가 없다"
    return m.group(1)


def _free(events, now_iso):
    """node 로 nvAFreeThisWeek(events, nowMs) 를 실제로 돌린다."""
    js = _week_js() + (
        "\nprocess.stdout.write(JSON.stringify(window.nvAFreeThisWeek("
        + json.dumps(events) + ", Date.parse(" + json.dumps(now_iso) + "))));"
    )
    out = subprocess.run(["node", "-e", "var window={};var document=undefined;" + js],
                         capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_week_label_true_when_a_has_free_window():
    # 2026-10-01(목) 12:00 KST. 이번 주 = 10/1~10/4(일).
    assert _free([], "2026-10-01T03:00:00Z") is True


def test_week_label_false_when_rest_of_week_full():
    now = "2026-10-03T13:00:00Z"   # 10/3(토) 22:00 KST → 오늘 남은 2시간, 일요일 하루
    full = [
        {"date": "2026-10-03", "start": 22.0, "end": 24.0, "room": "A", "kind": "booking"},
        {"date": "2026-10-04", "start": 0, "end": 24, "room": "A", "kind": "block"},
    ]
    assert _free(full, now) is False
    # B 가 차 있어도 A 판정에는 영향 없음
    assert _free([dict(e, room="B") for e in full], now) is True


def test_week_label_needs_two_hours_and_ignores_past_hours():
    now = "2026-10-04T12:00:00Z"   # 10/4(일) 21:00 KST — 남은 3시간 중 22~24 예약 → 1시간뿐
    ev = [{"date": "2026-10-04", "start": 22.0, "end": 24.0, "room": "A", "kind": "booking"}]
    assert _free(ev, now) is False
    # 월요일 0시 KST 에는 새 주가 시작된다
    assert _free(ev, "2026-10-04T15:00:00Z") is True


def test_week_label_false_on_bad_data():
    assert _free(None, "2026-10-01T03:00:00Z") is False


def test_mobile_bar_default_label_and_href_wiring_unchanged():
    html = _read("index.html")
    m = re.search(r'<a\b[^>]*id="book-mobile"[^>]*>(.*?)</a>', html, re.S)
    assert m and m.group(1).strip() == "A룸 예약 →", "기본 문구는 원래 문구여야 한다(JS 없거나 데이터 없을 때)"
    assert "['book-side','book-a','end-a','book-mobile']" in html, "A_URL·trackBook 배선이 그대로여야 한다"
    b = re.search(r'<a\b[^>]*id="book-mobile-b"[^>]*>(.*?)</a>', html, re.S)
    assert b and b.group(1).strip() == "B룸 예약 →"
    assert "nvApplyWeekLabel" in html[html.index("function loadAvailability"):], "예약현황 로드 뒤 문구를 갱신해야 한다"
