# -*- coding: utf-8 -*-
"""랜딩 UX 실측 2차 수정(2026-09-29) 회귀 잠금 — 근거: NUVIE_랜딩UX실측_2026-09-29 의 baseline_report·ux_blockers.

브라우저 없이 소스 계약으로 잠근다(실제 화면 실측은 별도 Playwright 스크립트로 한다).
🧊 /b 는 11/11 까지 동결이다 — 아래 테스트는 «홈·/a 만 바뀌고 b.html 은 안 바뀐다» 를 함께 지킨다.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
CSS = (ROOT / "styles.css").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
SITEJS = (ROOT / "site.js").read_text(encoding="utf-8")

NOT_B = ':not([data-room="b"])'


def _blocks(css):
    """(prelude, body) 최상위 블록 목록. @media 는 body 안에 중첩 규칙이 그대로 들어 있다."""
    out, depth, start, pre = [], 0, 0, ""
    i = 0
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    while i < len(css):
        c = css[i]
        if c == "{":
            if depth == 0:
                pre = css[start:i].strip()
                bstart = i + 1
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                out.append((pre, css[bstart:i]))
                start = i + 1
        i += 1
    return out


def top_level_rules():
    return [(p, b) for p, b in _blocks(CSS) if not p.startswith("@")]


def media_rules(needle):
    rules = []
    for p, b in _blocks(CSS):
        if p.startswith("@media") and needle in p.replace(" ", ""):
            rules += _blocks(b)
    return rules


def _margin_px(body, prop="scroll-margin-top"):
    m = re.search(prop + r":\s*(\d+)px", body)
    return int(m.group(1)) if m else None



def test_a_chipbar_not_hidden_behind_header():
    """칩바가 top:0 인데 헤더 z-index(50) > 칩바(40) 라 스크롤 뒤 칩이 헤더 밑에 숨었다(오눌림 9건)."""
    assert re.search(r"data-room[^\n]{0,40}['\"]a['\"]", SITEJS), "site.js 에 /a 전용 칩바 top 배선이 없다"
    assert "nv-chipbar" in SITEJS
    assert "getBoundingClientRect" in SITEJS[SITEJS.index("nv-chipbar"):]
    assert re.search(r'body\[data-room="a"\]\s+\.nv-chipbar\s*\{[^}]*top:\s*\d+px', CSS), \
        "JS 실행 전에도 칩바가 헤더 아래에 붙는 CSS 대비값이 없다"


def test_booking_anchor_margin_mobile_a_only():
    """/a «요금·예약» 칩 → #booking 도착 때 가격 줄이 상단 바에 가렸다(-85px)."""
    hit = [(p, b) for p, b in media_rules("max-width:640px")
           if "#booking" in p and "scroll-margin-top" in b]
    assert hit, "모바일 #booking scroll-margin-top 없음"
    assert 130 <= _margin_px(hit[0][1]) <= 160
    assert NOT_B in hit[0][0]
