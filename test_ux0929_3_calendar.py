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



def test_calendar_selected_outline_survives_cssText():
    """선택일 outline 이 바로 뒤 cssText 대입에 지워졌다(index.html renderCal)."""
    i = INDEX.index("cell.style.cssText='min-height:96px")
    j = INDEX.index("style.outline", INDEX.index("function renderCal"))
    assert j > i, "outline 대입이 cssText 대입보다 앞이라 지워진다"


def test_calendar_day_detail_scrolls_into_view_above_bottom_bar():
    body = INDEX[INDEX.index("function showDay"):INDEX.index("var calGridEl")]
    assert "scrollIntoView" in body, "날짜를 눌러도 상세 패널로 스크롤하지 않는다"
    assert re.search(r"#dayDetail\s*\{[^}]*scroll-margin-bottom:\s*\d+px", CSS), \
        "고정 하단 바(54px)에 안 가리는 scroll-margin-bottom 이 없다"
