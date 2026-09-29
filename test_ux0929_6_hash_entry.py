# -*- coding: utf-8 -*-
"""랜딩 UX 실측 3차 수정(2026-09-29) 회귀 잠금 — 해시 링크로 첫 진입 시 목표에 도착하지 못하던 결함.

근거: nuvie_ux_lab after_v1 S041(1920x1080·wifi·/#allday). html{scroll-behavior:smooth} 로 스크롤이 도는 동안
후기 카드·빈 시간 달력이 늦게 채워져 문서가 7,404→8,956px 로 길어지고, 스크롤은 옛 목표 위치에서 멈춘다.
PC 에서 /#allday·/#faq·/#location 진입이 목표보다 1,530~1,590px 위에서 멈췄다(실측: nuvie_ux_lab/check_hash_entry.py).
실제 화면 판정은 check_hash_entry.py 가 하고, 여기서는 소스 계약으로 잠근다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


def _realign_script():
    for m in re.finditer(r"<script>(.*?)</script>", INDEX, flags=re.S):
        if "ResizeObserver" in m.group(1) and "location.hash" in m.group(1):
            return m.group(1)
    return None


def test_index_realigns_hash_target_when_layout_grows():
    s = _realign_script()
    assert s, "해시 진입 뒤 문서 높이 변화를 보고 목표로 다시 맞추는 스크립트가 없다"
    assert "scrollIntoView" in s


def test_realign_is_instant_not_smooth():
    """다시 맞출 때도 smooth 면 같은 경주가 반복된다."""
    s = _realign_script() or ""
    assert re.search(r"behavior\s*:\s*['\"]instant['\"]", s), "behavior:'instant' 로 맞춰야 한다"


def test_realign_stops_on_user_input_and_hashchange_and_timeout():
    """손님이 직접 스크롤·탭하거나 메뉴를 누른 뒤에는 절대 끌어당기지 않는다."""
    s = _realign_script() or ""
    for ev in ("wheel", "touchstart", "keydown", "pointerdown", "hashchange"):
        assert ev in s, f"{ev} 에서 멈추지 않는다"
    assert re.search(r"\d{4}", s), "시간 상한(ms)이 없다"


def test_realign_ignores_invalid_hash():
    """querySelector 에 못 쓰는 해시(#utm=... 등)에서 스크립트가 죽으면 안 된다."""
    s = _realign_script() or ""
    assert "try" in s and "catch" in s
