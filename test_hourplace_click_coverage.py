# -*- coding: utf-8 -*-
"""🔴 재현→수정 (2026-08-18, 2차): `HourplaceClick` 이 «모든» 아워 이동 문을 덮지 못했다.

1차 작업(`test_hourplace_click_wiring.py`)은 허브의 주 CTA·달력 CTA 만 덮었다.
외부 점검 의견을 코드와 대조하다가 **아직 안 덮인 문 두 종류**를 찾았다.

  ① **룸 상세페이지(/a·/b) 예약 버튼** — `site.js:trackBook` 이 `book_click` + Meta `Lead` 만 쏘고
     `HourplaceClick` 이 없었다. 룸 페이지를 거쳐 나간 손님이 **총량에서 통째로 빠진다.**
     🔴 왜 치명적인가: 광고 소재 A/B 에서 «소재마다 룸 페이지 경유 비율이 다르면»
        경유가 많은 소재가 실제보다 나쁘게 나온다. 측정 누락이 판정을 뒤집는다.

  ② **폴백·문의 링크 3종** — 평소엔 숨어 있다가 오류 때 나타나는 링크들.
     특히 `calFetchWarn` 안의 「A룸 예약 · B룸 예약」은 **달력이 안 뜰 때 나오는 진짜 예약 버튼**이다.
     달력 로드 실패는 실제로 있었던 일(`test_build_availability_fetchfail_repro.py`)이라
     이 경로가 0 으로 잡히면 그날 광고 성과가 통째로 왜곡된다.

⛔ **`book_click` 은 여전히 불변**이다(광고 파일럿 사전등록 판독 지표) — 이번에도 «추가»만 했다.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HUB = (ROOT / "index.html").read_text(encoding="utf-8")
SITE = (ROOT / "site.js").read_text(encoding="utf-8")

_PARAMS = (
    "room",
    "destination_url",
    "button_location",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
)


# ── ① 룸 상세페이지 ────────────────────────────────────────────────
def test_room_page_fires_hourplace_click():
    """🔴 실사고 재현 — 이 호출이 없으면 /a·/b 를 거친 클릭이 총량에서 빠진다."""
    assert "hourplaceClick(" in SITE, (
        "site.js 에 HourplaceClick 호출이 없다 — 룸 상세페이지에서 나간 예약 클릭이 "
        "광고 A/B 판정의 분자에 안 잡힌다"
    )
    start = SITE.index("function trackBook")
    block = SITE[start:start + 1200]
    assert "hourplaceClick(" in block and "room_page" in block, (
        "trackBook 안에서 HourplaceClick 이 button_location='room_page' 로 발화하지 않는다"
    )


def test_room_page_hourplace_click_carries_all_params():
    """허브와 «같은» 파라미터여야 두 표면을 한 지표로 합산할 수 있다."""
    start = SITE.index("function hourplaceClick")
    block = SITE[start:start + 1400]
    missing = [p for p in _PARAMS if p not in block]
    assert not missing, f"site.js hourplaceClick 에 빠진 파라미터: {missing}"


def test_room_page_hourplace_click_is_gated_on_external_booking():
    """🔜 자사몰(FF.mode='own') 전환 후엔 아워 이동이 아니므로 발화하면 안 된다."""
    start = SITE.index("function trackBook")
    block = SITE[start:start + 1200]
    assert "isExternalBooking()" in block, (
        "자사몰 전환 후에도 HourplaceClick 이 계속 발화하면 «아워로 나간 수»가 거짓이 된다"
    )


def test_site_js_book_click_still_frozen():
    """⛔ 광고 파일럿 사전등록 지표 — 이름·파라미터 불변(추가만 허용)."""
    assert "gtag('event', 'book_click', { room: room, transport_type: 'beacon', page: PAGE_ORIGIN })" in SITE, (
        "site.js 의 book_click 정의가 바뀌었다 — 7월 파일럿과의 비교선이 끊긴다"
    )
    assert "fbq('track', 'Lead', { room: room })" in SITE, "site.js 의 Meta Lead 가 사라졌다"


# ── ② 폴백·문의 링크 ──────────────────────────────────────────────
def test_all_fallback_hourplace_links_are_marked():
    """숨어 있다 나타나는 링크 3종이 전부 계측 표시를 달고 있어야 한다."""
    for marker in (
        'data-hp="a|reviews_fallback"',
        'data-hp="a|calendar_fallback"',
        'data-hp="b|calendar_fallback"',
        'data-hp="a|inquiry_link"',
    ):
        assert marker in HUB, f"폴백 링크 계측 표시 누락: {marker}"


def test_calendar_fallback_is_treated_as_a_real_booking_button():
    """🔴 달력이 안 뜰 때 나오는 A·B룸 링크는 «진짜 예약 버튼»이다 — 반드시 계측된다."""
    start = HUB.index('id="calFetchWarn"')
    block = HUB[start:start + 900]
    assert block.count("data-hp=") == 2, (
        "calFetchWarn 안의 A룸·B룸 예약 링크 둘 다 계측돼야 한다 — "
        "달력 로드 실패는 실제로 있었던 일이고, 그날 성과가 통째로 왜곡된다"
    )


def test_delegated_listener_exists_for_late_inserted_links():
    """후기 폴백 링크는 innerHTML 로 나중에 삽입된다 → 위임이 아니면 절대 안 잡힌다."""
    assert "data-hp" in HUB and "addEventListener('click'" in HUB
    start = HUB.index("function hourplaceClick")
    block = HUB[start:start + 2600]
    assert "getAttribute('data-hp')" in block, (
        "data-hp 위임 리스너가 없다 — 로드 시점에 DOM 에 없는 폴백 링크는 영원히 0 건이 된다"
    )


def test_delegation_does_not_double_fire_on_existing_ctas():
    """이미 계측된 CTA 에 data-hp 를 달면 한 클릭이 두 번 세어진다."""
    for cta_id in ("availBookA", "availBookB", "dayDetailBookA", "dayDetailBookB"):
        start = HUB.index(f'id="{cta_id}"')
        tag = HUB[start:HUB.index(">", start)]
        assert "data-hp" not in tag, (
            f"{cta_id} 는 이미 trackAvail 로 계측된다 — data-hp 를 달면 이중 계상된다"
        )


# ── ③ 전수 검사: 남은 미계측 문이 없는가 ──────────────────────────
def test_no_uninstrumented_hourplace_anchor_remains():
    """새 아워 링크를 «계측 없이» 추가하면 여기서 걸린다.

    앵커(<a>)만 본다 — JSON-LD 의 Offers URL 과 JS 상수(A_URL/B_URL)는 클릭 대상이 아니다.
    """
    import re

    uninstrumented = []
    for m in re.finditer(r"<a\b[^>]*hourplace\.co\.kr/place[^>]*>", HUB):
        tag = m.group(0)
        if "data-hp=" in tag:
            continue
        # id 로 개별 배선된 CTA 는 허용 목록
        if any(f'id="{k}"' in tag for k in ("availBookA", "availBookB", "dayDetailBookA", "dayDetailBookB")):
            continue
        uninstrumented.append(tag[:120])
    assert not uninstrumented, (
        "계측되지 않은 아워플레이스 링크가 남아 있다 — "
        "data-hp=\"<room>|<위치>\" 를 달거나 개별 배선할 것:\n" + "\n".join(uninstrumented)
    )
