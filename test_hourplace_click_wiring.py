# -*- coding: utf-8 -*-
"""🔴 재현→수정 (2026-08-18 광고 추적 점검): 아워 이동 측정에 구멍 4개가 있었다.

점검에서 «브라우저 라이브 실측»으로 확인한 것
  ① 예약현황 달력 CTA(availBookA/B·dayDetailBookA/B)를 클릭하면 GA4 는 두 건이 나가는데
     **Meta 는 한 건도 안 나간다.** 달력은 방문자가 예약 의사를 굳히는 자리인데
     메타 학습 신호에서 통째로 빠져 있었다.
  ② 아워로 나가는 버튼이 세 갈래(book_click / avail_click / booking_intent)로 흩어져
     **「아워로 나간 총량」을 한 지표로 셀 수 없었다.**
  ③ `attribution.js` 가 UTM 을 localStorage 에 저장은 하는데 **이벤트에 실어 보내지 않아**,
     「훅 A 와 B 중 어느 쪽이 더 클릭시켰나」를 이벤트 단위로 못 갈랐다.
  ④ 가격·시설 조회 이벤트가 아예 없어 **「가격까지 본 사람」 리타겟팅 모수**를 못 만들었다.

⛔ **`book_click` 은 이름도 파라미터도 건드리지 않는다.**
   광고 파일럿 사전등록 판독 지표라, 이름을 바꾸면 7월 파일럿과 9월 데이터를 비교할 수 없다.
   ⇒ 통일 이벤트 `HourplaceClick` 을 **나란히 추가**한다(교체가 아니라 병행).
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
HUB = (ROOT / "index.html").read_text(encoding="utf-8")
ATTR = (ROOT / "attribution.js").read_text(encoding="utf-8")
TPL = (ROOT / "room.template.html").read_text(encoding="utf-8")


# ── ① 달력 CTA 가 Meta 로 Lead 를 보낸다 ────────────────────────────────
def test_calendar_cta_now_fires_meta_lead():
    """🔴 실사고 재현 — 이 문장이 없으면 달력 클릭이 메타에 안 잡힌다."""
    block = HUB[HUB.index("function trackAvail"):HUB.index("function trackAvail") + 700]
    assert "fbq" in block and "Lead" in block, (
        "달력 CTA(trackAvail)에서 Meta Lead 가 발화하지 않는다 — "
        "리타겟팅 모수와 메타 학습 신호가 그만큼 샌다"
    )


def test_book_click_definition_is_untouched():
    """⛔ 광고 파일럿 판독 지표는 불변 — 이름·파라미터를 그대로 유지한다."""
    assert "gtag('event','book_click',{room:room,transport_type:'beacon',page:'hub'})" in HUB
    assert "fbq('track','Lead',{room:room})" in HUB


# ── ② HourplaceClick 통일 이벤트 ────────────────────────────────────────
def test_hourplace_click_event_exists():
    assert "HourplaceClick" in HUB, "아워 이동 통일 이벤트가 없다"


@pytest.mark.parametrize("param", [
    "destination_url", "button_location",
    "utm_source", "utm_medium", "utm_campaign", "utm_content",
])
def test_hourplace_click_carries_required_params(param):
    """점검 보고서가 요구한 6개 파라미터가 전부 실려야 한다."""
    block = HUB[HUB.index("function hourplaceClick"):]
    block = block[:block.index("\n  }") + 4]
    assert param in block, f"HourplaceClick 에 {param} 이 빠졌다"


def test_hourplace_click_is_added_not_replacing():
    """book_click 을 지우고 갈아끼운 게 아니라 «나란히» 있어야 한다."""
    assert "book_click" in HUB and "HourplaceClick" in HUB


def test_every_hourplace_bound_button_is_covered():
    """아워로 실제로 나가는 버튼이 전부 통일 이벤트를 탄다."""
    for btn in ["book-side", "end-a", "book-mobile", "book-b", "end-b", "book-mobile-b",
                "availBookA", "availBookB", "dayDetailBookA", "dayDetailBookB"]:
        assert btn in HUB, f"{btn} 버튼이 사라졌다"
    # 두 배선 함수 모두 통일 이벤트를 호출해야 한다
    for fn in ["function trackBook", "function trackAvail"]:
        block = HUB[HUB.index(fn):HUB.index(fn) + 700]
        assert "hourplaceClick" in block, f"{fn} 이 통일 이벤트를 안 부른다"


# ── ③ UTM 을 이벤트 파라미터로 ──────────────────────────────────────────
def test_attribution_exposes_utm_for_events():
    """저장만 하고 안 쓰던 UTM 을 이벤트가 읽을 수 있게 노출한다."""
    assert "utmParams" in ATTR, "attribution.js 가 UTM 을 이벤트용으로 안 내놓는다"
    assert "NUVIE_ATTRIBUTION" in ATTR


def test_landing_view_now_carries_campaign_and_content():
    """훅 A/B 를 가르려면 utm_content 가 이벤트에 있어야 한다."""
    block = ATTR[ATTR.index("event('landing_view'"):]
    block = block[:block.index("});") + 3]
    assert "utm_content" in block or "utmParams" in block, (
        "landing_view 가 utm_source 만 보내고 campaign·content 를 안 보낸다"
    )


# ── ④ ViewContent (가격·시설 조회) ──────────────────────────────────────
def test_view_content_event_exists():
    assert "ViewContent" in HUB, "가격·시설 조회 이벤트가 없다 — 리타겟팅 모수를 못 만든다"


def test_view_content_uses_intersection_observer_not_scroll_spam():
    """스크롤 이벤트 연발이 아니라 «한 번만» 발화해야 한다."""
    block = HUB[HUB.index("ViewContent") - 1200:HUB.index("ViewContent") + 900]
    assert "IntersectionObserver" in block
    assert "unobserve" in block or "disconnect" in block or "fired" in block, (
        "한 번만 쏘는 가드가 없다 — 스크롤할 때마다 중복 발화한다"
    )


# ── 회귀 가드 ────────────────────────────────────────────────────────────
def test_internal_traffic_gate_still_first():
    """계측 게이트가 여전히 태그보다 먼저 온다(자체 트래픽 오염 차단)."""
    assert HUB.index("__nvInternal") < HUB.index("googletagmanager.com/gtag")


def test_hub_and_room_template_gate_stay_identical():
    """허브·룸템플릿 게이트 동기화 — 기존 규약을 깨지 않았는지."""
    def gate(src):
        s = src.index("var internal = false;")
        return re.sub(r"\s+", " ", src[s:src.index("})();", s)])
    assert gate(HUB) == gate(TPL)


def test_no_pii_in_event_params():
    """이벤트에 이메일·전화·예약번호를 싣지 않는다."""
    block = HUB[HUB.index("function hourplaceClick"):]
    block = block[:block.index("\n  }") + 4]
    for bad in ["email", "phone", "tel:", "booking_id", "reservation"]:
        assert bad not in block.lower(), f"이벤트 파라미터에 {bad} 가 들어갔다"
