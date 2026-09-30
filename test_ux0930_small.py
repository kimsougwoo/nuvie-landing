# -*- coding: utf-8 -*-
"""09-29 UX 막힘 목록 중 «문구 변경 없는» 소묶음 (2026-09-30).

U-13 히어로 «★ 5.0 · 후기 N건» 칩이 후기 대신 룸 소개(#rooms)로 갔다 → #reviews.
U-10 룸 페이지 히어로 «A룸 예약하기»(실제 아워 이동)가 라이트 테마에서 검은 채움이라 어두운 히어로 사진 위에서
     사라졌다(대비 1.03:1). 허브 규칙 «흰 채움은 실제 아워 이동에만»(index.html 2026-07-29 주석)대로 두 테마 모두 흰 채움.
     🧊 /b 는 11/11 동결 — body:not([data-room="b"]) 로 막는다(b.html 바이트는 test_ux0929_1_anchor 가 지킨다).
U-11 이번 달의 지난 날이 흐리지 않아 «비어 있는(예약 가능한) 날»처럼 읽혔다 → 지난 날은 흐리게.
     ⚠️ «월말엔 다음 달을 기본으로»는 08-21 결정(진행 중 예약을 숨긴다)과 충돌해 하지 않는다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent


def _read(n):
    return (ROOT / n).read_text(encoding="utf-8")


def test_hero_review_badge_goes_to_reviews():
    m = re.search(r'<a href="([^"]+)" id="heroReviewBadge"', _read("index.html"))
    assert m and m.group(1) == "#reviews", m and m.group(1)
    assert 'id="reviews"' in _read("index.html")


def test_room_hero_booking_button_is_white_fill_except_frozen_b():
    css = _read("styles.css").replace(" ", "")
    rule = re.search(r'body:not\(\[data-room="b"\]\)\.herocta\.btn\[data-book\]\{([^}]*)\}', css)
    assert rule, "룸 히어로 예약 버튼 흰 채움 규칙이 없다(/b 제외)"
    body = rule.group(1).lower()
    assert "background:#f5f5f6" in body and "color:#0b0b0c" in body


def test_room_hero_booking_button_markup_unchanged():
    # 라벨·href·data-book 은 그대로(색만 CSS 로)
    assert '<a class="btn" data-book="{{SLUG}}" href="{{BOOKING_HREF}}" style="padding:15px 32px;font-size:15px">{{LABEL}} 예약하기</a>' in _read("room.template.html")


def test_calendar_dims_past_days_but_keeps_current_month_default():
    src = _read("index.html")
    assert re.search(r"isPast\s*=\s*inMonth\s*&&\s*key\s*<\s*todayKey", src), "지난 날 판정이 없다"
    assert "monthOffset=0" in src.replace(" ", ""), "08-21 결정: 첫 화면은 항상 이번 달"
