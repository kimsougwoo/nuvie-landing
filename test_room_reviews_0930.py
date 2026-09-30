# -*- coding: utf-8 -*-
"""룸 페이지(/a·/b) 후기 사진 배열(대표 09-30 «A,B룸 후기 사진들 배열이 이상한데요» — B룸도 대표 지시로 적용).

실측(09-30, 390·320·1440): ① PC 3열 그리드가 align-items:start 라 한 줄의 카드 높이가 121~320px 로 제각각 → 짧은 카드 밑이 비어
   줄이 들쭉날쭉 ② /b 후기 사진은 원본(최대 6224×4672·약 24MB)을 그대로 받았다(축소본 교체가 /a 에만 배선) ③ /b 는 눌러도
   새 탭에 원본이 열렸다. 사진 1장 카드의 «반쪽 칸»은 대표 08-07 결정(항상 2열 고정 — 크기 들쭉날쭉 방지)이라 그대로 둔다.
후기 글·사진·순서는 바꾸지 않는다(verbatim).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent


def _read(n):
    return (ROOT / n).read_text(encoding="utf-8")


def _reviews_section(html):
    return html[html.index('<section id="reviews">'):html.index("</section>", html.index('<section id="reviews">'))]


def test_review_cards_masonry_on_desktop_only():
    """대표 09-30 «후기 저게 맞아요?»: 줄 높이 맞춤(stretch)은 짧은 카드 아래가 크게 비었다 → PC(641px 이상)는 벽돌형(다단),
    모바일은 한 줄 그리드 그대로. 다단은 모바일에서 만들지 않는다(홈 #reviewCards 핀치줌 버그와 같은 규칙·같은 분기점)."""
    for page in ("a.html", "b.html"):
        sec = _reviews_section(_read(page))
        assert '<div class="room-reviews" data-reveal style="display:grid;' in sec, page
    css = _read("styles.css").replace(" ", "")
    m = re.search(r"@media\(min-width:641px\)\{\.room-reviews\{([^}]*)\}\.room-reviews>div\{([^}]*)\}\}", css)
    assert m and "column-width:260px" in m.group(1) and "break-inside:avoid" in m.group(2)
    assert ".room-reviews{" not in css.replace(m.group(0), ""), "다단 규칙은 데스크탑 미디어쿼리 안에만"


def test_review_thumbs_use_small_copies_at_build_time():
    m = json.loads(_read("reviews/img/map.json"))
    for page in ("a.html", "b.html"):
        sec = _reviews_section(_read(page))
        pairs = re.findall(r'<a href="([^"]+)"[^>]*><img loading="lazy" decoding="async" src="([^"]+)"', sec)
        assert pairs, page
        for href, src in pairs:
            if href in m:
                assert src == m[href]["thumb"], f"{page}: 축소본이 있으면 처음부터 축소본({src})"
            else:
                assert src == href, f"{page}: 매핑이 없으면 원본 폴백"


def test_review_lightbox_wired_for_both_rooms():
    js = _read("site.js")
    assert "if (/^[ab]$/.test(document.body.getAttribute('data-room') || '')) {" in js
