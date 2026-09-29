# -*- coding: utf-8 -*-
"""360px 상단 바 가로 넘침 잠금(2026-09-29 UX 실측, baseline_report §2 horizontal_overflow 2건 · S244/S280).

재현: 360px 폭에서 상단 바 내용 폭 = 로고 94.6 + 예약 2버튼 183.6 + 테마 44 + 간격 20 = 342px 인데
사용 가능한 폭은 324px(좌우 패딩 18) — 정상 상태에서도 테마 버튼이 우측 패딩 18px 를 먹고 붙어 있다(themeRight=360.2).
웹폰트(Pretendard 동적 서브셋)가 뒤늦게 바뀌어 글자 폭이 늘면 그만큼 화면 밖으로 밀린다
(느린 4G 실측: scrollWidth 376~380 > 360). ⇒ 좁은 폭에서 간격·패딩을 줄여 슬랙을 확보한다.
🧊 /b 는 11/11 동결 — 홈·/a 로만 한정(body:not([data-room="b"])).
"""
import re
from pathlib import Path

CSS = (Path(__file__).parent / "styles.css").read_text(encoding="utf-8")
NOT_B = 'body:not([data-room="b"])'


def _media_380_body():
    m = re.search(r"@media\(max-width:38\dpx\)\{", CSS.replace(" ", ""))
    assert m, "max-width:38Xpx 미디어쿼리가 없다"
    # 공백을 지운 사본에서 균형 잡힌 중괄호 블록을 잘라낸다
    flat = CSS.replace(" ", "")
    depth, i = 0, m.end() - 1
    start = i
    while i < len(flat):
        if flat[i] == "{":
            depth += 1
        elif flat[i] == "}":
            depth -= 1
            if depth == 0:
                return flat[start + 1:i]
        i += 1
    raise AssertionError("닫는 중괄호 없음")


def test_narrow_header_gives_slack_for_font_swap():
    body = _media_380_body()
    side = re.search(r'body:not\(\[data-room="b"\]\)\.side\{([^}]*)\}', body)
    assert side, "홈·/a 한정 .side 규칙이 없다"
    pads = re.findall(r"padding(?:-left|-right)?:(\d+)px", side.group(1))
    assert pads and all(int(x) <= 14 for x in pads), f".side 좌우 패딩을 줄여야 한다: {pads}"
    gap = re.search(r"gap:(\d+)px", side.group(1))
    assert gap and int(gap.group(1)) <= 6


def test_narrow_header_book_buttons_are_tighter():
    body = _media_380_body()
    m = re.search(r'body:not\(\[data-room="b"\]\)\.booka\{([^}]*)\}', body)
    assert m, "홈·/a 한정 .book a 규칙이 없다"
    pad = re.search(r"padding:\d+px(\d+)px", m.group(1))
    assert pad and int(pad.group(1)) <= 11, "예약 버튼 좌우 패딩을 줄여야 한다"


def test_narrow_header_rules_exclude_b():
    """미디어쿼리 안 모든 선택자는 b 룸을 제외해야 한다."""
    body = _media_380_body()
    for sel in re.findall(r"([^{}]+)\{[^}]*\}", body):
        for part in sel.split(","):
            assert NOT_B.replace(" ", "") in part, f"/b 를 제외하지 않은 선택자: {part}"
