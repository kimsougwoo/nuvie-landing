# -*- coding: utf-8 -*-
"""09-29 UX 막힘 목록 중 «문구 변경 없는» 소묶음 (2026-09-30).

U-13 히어로 «★ 5.0 · 후기 N건» 칩이 후기 대신 룸 소개(#rooms)로 갔다 → #reviews.
U-10 룸 페이지 히어로 «A룸 예약하기»(실제 아워 이동)가 라이트 테마에서 검은 채움이라 어두운 히어로 사진 위에서
     사라졌다(대비 1.03:1). 허브 규칙 «흰 채움은 실제 아워 이동에만»(index.html 2026-07-29 주석)대로 두 테마 모두 흰 채움.
     10/1 /b 1안(대표): /b 도 같게 — 동결 표지 body:not([data-frozen]) 만 제외(B룸 고유 문구·사진은 test_ux0929_1_anchor 가 지킨다).
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
    rule = re.search(r'body:not\(\[data-frozen\]\)\.herocta\.btn\[data-book\]\{([^}]*)\}', css)
    assert rule, "룸 히어로 예약 버튼 흰 채움 규칙이 없다(/b 제외)"
    body = rule.group(1).lower()
    assert "background:#f5f5f6" in body and "color:#0b0b0c" in body


def test_hero_content_is_not_scroll_revealed_except_frozen_b():
    """히어로 버튼 줄(.herocta)이 첫 화면에서 opacity 0.63~0.84 로 멈춰 있었다(2026-09-30 실측, 홈·/a·/b 모바일·PC).
    스크롤 리빌(animation-range: entry 0% cover 24%)이 첫 화면 안 요소에는 끝나지 않는다 → 히어로 안은 리빌하지 않는다."""
    css = _read("styles.css").replace(" ", "")
    rule = re.search(r'body:not\(\[data-frozen\]\)\.hero\[data-reveal\]\{([^}]*)\}', css)
    assert rule, "히어로 리빌 해제 규칙이 없다(/b 제외)"
    body = rule.group(1)
    assert "animation:none" in body and "opacity:1" in body and "transform:none" in body


def test_room_hero_booking_button_markup_unchanged():
    # 라벨·href·data-book 은 그대로(색만 CSS 로)
    assert '<a class="btn" data-book="{{SLUG}}" href="{{BOOKING_HREF}}" style="padding:15px 32px;font-size:15px">{{LABEL}} 예약하기</a>' in _read("room.template.html")


def test_calendar_cell_animation_keeps_intended_opacity():
    """nvCellIn 이 opacity:1 로 끝나며 fill both 로 붙들어, 인라인 opacity(다른 달 .3·지난 날 .45)가 한 번도 안 먹었다(09-30 캡처).
    애니메이션 끝값을 칸마다 정한 --op 로 둔다(움직임 줄이기 설정에선 애니메이션이 꺼져 인라인 opacity 가 그대로 산다)."""
    css = _read("styles.css").replace(" ", "")
    kf = re.search(r"@keyframesnvCellIn\{from\{([^}]*)\}to\{([^}]*)\}\}", css)
    assert kf and "opacity:var(--op,1)" in kf.group(2), kf and kf.group(2)
    src = _read("index.html")
    assert "--op:.45" in src and "--op:.3" in src and "--op:.65" in src   # 지난 날 · 지난 다른 달 · 다음 달 앞날(약하게)


def test_calendar_dims_past_days_but_keeps_current_month_default():
    src = _read("index.html")
    assert re.search(r"isPast\s*=\s*inMonth\s*&&\s*key\s*<\s*todayKey", src), "지난 날 판정이 없다"
    assert "monthOffset=0" in src.replace(" ", ""), "08-21 결정: 첫 화면은 항상 이번 달"
