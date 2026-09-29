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



def test_pc_anchor_scroll_margin_covers_top_bar():
    """PC(모든 폭) 앵커가 상단 바(70px)에 가린다 — 규칙이 640px 이하에만 있었다."""
    hit = [(p, b) for p, b in top_level_rules()
           if "scroll-margin-top" in b and "section[id]" in p]
    assert hit, "미디어쿼리 밖에 section[id] scroll-margin-top 규칙이 없다"
    px = _margin_px(hit[0][1])
    assert px is not None and 74 <= px <= 94, f"상단 바 70px 를 덮고 0~24px 여백이 되는 값이어야 한다: {px}"


def test_pc_anchor_rule_excludes_b_room():
    """/b 동결 — 새 규칙은 b 룸 페이지에 적용되면 안 된다."""
    for p, b in top_level_rules():
        if "scroll-margin-top" in b:
            assert NOT_B in p, f"/b 를 제외하지 않은 scroll-margin 규칙: {p}"


def test_allday_anchor_has_mobile_margin():
    """모바일 /#allday(<details>) 는 헤더+칩바 밑에 66~69px 가려졌다."""
    hit = [(p, b) for p, b in media_rules("max-width:640px")
           if "#allday" in p and "scroll-margin-top" in b]
    assert hit, "모바일 미디어쿼리에 #allday scroll-margin-top 이 없다"
    px = _margin_px(hit[0][1])
    assert px is not None and 130 <= px <= 160, px
    assert NOT_B in hit[0][0]


def test_allday_anchor_has_pc_margin():
    hit = [(p, b) for p, b in top_level_rules() if "#allday" in p and "scroll-margin-top" in b]
    assert hit, "PC 폭 #allday scroll-margin-top 이 없다"
    assert 90 <= _margin_px(hit[0][1]) <= 110



def test_b_html_unchanged_since_base():
    """b.html 은 이 브랜치 시작 커밋(085d3c1) 이후 바이트가 그대로여야 한다."""
    import pytest
    if subprocess.run(["git", "cat-file", "-e", "085d3c1"], cwd=ROOT, capture_output=True).returncode != 0:
        pytest.skip("기준 커밋 없음(얕은 클론)")
    r = subprocess.run(["git", "diff", "--quiet", "085d3c1", "--", "b.html"], cwd=ROOT)
    assert r.returncode == 0, "b.html 이 바뀌었다(11/11 동결)"
