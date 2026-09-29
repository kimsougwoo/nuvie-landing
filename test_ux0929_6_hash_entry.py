# -*- coding: utf-8 -*-
"""랜딩 UX 실측 3차 수정(2026-09-29) 회귀 잠금 — 해시 링크로 첫 진입 시 목표에 도착하지 못하던 결함.

근거: nuvie_ux_lab after_v1 S041(1920x1080·wifi·/#allday). html{scroll-behavior:smooth} 로 스크롤이 도는 동안
후기 카드 23장이 JSON 으로 늦게 그려져 문서가 7,404→8,956px 로 길어지고, 스크롤은 옛 목표 위치에서 멈춘다.
PC 에서 /#allday·/#faq·/#location 진입이 목표보다 1,530~1,600px 위에서 멈췄다.
실제 화면 판정은 nuvie_ux_lab/check_hash_entry.py(실제 크롬, 도착 6조건 + 손 뗌 2조건 + 이상한 해시 4조건)가 하고,
여기서는 주석을 걷어 낸 스크립트 본문으로 계약을 잠근다(2026-09-29 새 눈 검수: 주석 속 단어만으로 통과하던 약점 보완).
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


def _strip_js_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"(^|[^:'\"])//[^\n]*", r"\1", s)


def _realign_script():
    for m in re.finditer(r"<script>(.*?)</script>", INDEX, flags=re.S):
        code = _strip_js_comments(m.group(1))
        if "ResizeObserver" in code and "location.hash" in code:
            return code
    return None


def test_index_realigns_hash_target_when_layout_grows():
    s = _realign_script()
    assert s, "해시 진입 뒤 문서 높이 변화를 보고 목표로 다시 맞추는 스크립트가 없다"
    assert re.search(r"new ResizeObserver\(", s) and re.search(r"\.observe\(document\.body\)", s)
    assert re.search(r"el\.scrollIntoView\(", s)


def test_realign_is_instant_not_smooth():
    """다시 맞출 때도 smooth 면 같은 경주가 반복된다."""
    s = _realign_script() or ""
    assert re.search(r"scrollIntoView\(\{[^}]*behavior\s*:\s*'instant'", s), "behavior:'instant' 로 맞춰야 한다"


def test_realign_stops_on_user_input_and_hashchange():
    """손님이 직접 스크롤·탭하거나 메뉴를 누른 뒤에는 끌어당기지 않는다 — 이벤트 이름이 실제 등록 배열 안에 있어야 한다."""
    s = _realign_script() or ""
    m = re.search(r"\[([^\]]*)\]\.forEach\(function\(ev\)\{\s*window\.addEventListener\(ev,\s*stop", s)
    assert m, "입력 이벤트 배열을 stop 에 등록하는 코드가 없다"
    for ev in ("wheel", "touchstart", "keydown", "pointerdown", "hashchange"):
        assert f"'{ev}'" in m.group(1), f"{ev} 에서 멈추지 않는다"


def test_realign_has_bounded_time_limit():
    s = _realign_script() or ""
    m = re.search(r"LIMIT_MS\s*=\s*(\d+)", s)
    assert m and 3000 <= int(m.group(1)) <= 10000, "시간 상한 LIMIT_MS 가 3~10초여야 한다"
    assert re.search(r"Date\.now\(\)\s*-\s*t0\s*>\s*LIMIT_MS", s) and re.search(r"setTimeout\(stop,\s*LIMIT_MS", s)


def test_realign_stops_when_position_moved_without_input_events():
    """스크롤바 드래그처럼 입력 이벤트 없이 움직인 경우: 우리가 맞춘 위치도, 거기에 늘어난 높이를 더한 위치도 아니면 멈춘다."""
    s = _realign_script() or ""
    assert re.search(r"ourY\s*=\s*window\.scrollY", s), "맞춘 뒤 위치를 기억하지 않는다"
    assert re.search(r"Math\.abs\(y-ourY\)>4\s*&&\s*Math\.abs\(y-\(ourY\+grew\)\)>4\)\{\s*stop\(\)", s)


def test_hash_is_resolved_by_id_not_selector():
    """#faq,body·#utm=… 같은 값이 선택자로 해석돼 엉뚱한 요소로 가면 안 된다. 한글 id 도 디코딩해 찾는다."""
    s = _realign_script() or ""
    assert re.search(r"getElementById\(decodeURIComponent\(h\.slice\(1\)\)\)", s)
    assert not re.search(r"querySelector\(\s*h\s*\)", s)
    assert re.search(r"try\s*\{\s*el\s*=\s*document\.getElementById", s), "decodeURIComponent 오류(#%E0 등)를 잡아야 한다"
