# -*- coding: utf-8 -*-
"""🔴 재현→수정 (2026-08-18 저녁): ViewContent 가 «배포됐는데 GA4 도달 0건»이었다.

**어떻게 잡았나 — 브라우저가 아니라 GA4 실데이터로.**
내 브라우저는 googletagmanager.com 을 차단해 전송 검증이 불가능했다(Clarity·fbevents 는 로드되는데
gtag.js 만 안 온다). 그래서 GA4 Data API 로 실제 방문자 데이터를 조회했더니:

    2026-08-18  landing_view 33 · room_detail_click 7 · HourplaceClick 1 · **ViewContent 0**

같은 날 룸 상세로 넘어간 사람이 7명인데 ViewContent 가 0 이면 발화 자체가 안 되는 것이다.

**원인 = threshold 0.4 의 「천장」.**
`#rooms` 는 룸 카드 2장 + 가격 블록이라 **뷰포트보다 크다.** 요소가 뷰포트보다 크면
화면에 보일 수 있는 최대 비율이 `vh / height` 로 «막히고», 그 값이 0.4 미만이면
아무리 스크롤해도 threshold 를 못 넘는다. 모바일일수록 심하다(뷰포트는 짧고 섹션은 더 길어진다).

**그리고 폴백이 폴백 구실을 못 했다** — `geoCheck` 도 같은 `0.4` 를 따로 들고 있어서
두 겹이 «같은 결함을 공유»했다. 두 겹으로 걸어둔 의미가 없었다.

⇒ 인스턴스(#rooms 의 threshold 숫자)가 아니라 **클래스**를 고쳤다:
   판정을 `seenEnough()` 한 곳으로 모으고, **비율 OR 절대픽셀** 두 갈래로 만들었다.
   작은 요소는 「40% 보임」, 큰 요소는 「화면의 60%를 채움」으로 통과한다.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HUB = (ROOT / "index.html").read_text(encoding="utf-8")


def _vc_block() -> str:
    """ViewContent IIFE 본문만 잘라낸다."""
    start = HUB.index("ViewContent(가격·시설 조회)")
    end = HUB.index("예약 현황 클릭", start)
    return HUB[start:end]


def test_judgement_is_shared_by_observer_and_fallback():
    """🔴 실사고 재현 — 두 겹이 각자 0.4 를 들고 있으면 «같은 결함을 공유»한다."""
    block = _vc_block()
    assert "function seenEnough(" in block, (
        "IO 와 폴백이 공유하는 판정 함수가 없다 — 각자 기준을 들면 폴백이 폴백 구실을 못 한다"
    )
    # geoCheck 가 자기만의 비율 계산을 다시 하고 있으면 안 된다
    geo = block[block.index("function geoCheck("):]
    geo_body = geo[:geo.index("}")+1]
    assert "seenEnough(" in geo_body, "geoCheck 가 공유 판정을 쓰지 않는다"
    assert "0.4" not in geo_body, (
        f"geoCheck 안에 독자 임계가 남아 있다 — 공유 판정으로 모아야 한다:\n{geo_body}"
    )


def test_large_element_can_still_fire():
    """🔴 핵심 재현 — 뷰포트보다 큰 요소는 비율만으로는 «영원히» 못 넘는다."""
    block = _vc_block()
    m = re.search(r"function seenEnough\(r\)\{(.*?)\n    \}", block, re.S)
    assert m, "seenEnough 본문을 찾지 못했다"
    body = m.group(1)
    # 절대픽셀 갈래(화면의 일정 비율을 채우면 통과)가 반드시 있어야 한다
    assert re.search(r"vis\s*>=\s*vh\s*\*", body), (
        "절대픽셀 갈래가 없다 — 요소가 뷰포트보다 크면 비율은 vh/height 에서 «천장에 막힌다».\n"
        f"현재 본문:\n{body}"
    )
    assert "||" in body, "두 갈래가 OR 로 묶여 있어야 한다(하나만 통과해도 발화)"


def test_observer_thresholds_include_low_steps():
    """threshold 가 0.4 단일이면 큰 요소에서 콜백 자체를 못 받는다."""
    block = _vc_block()
    m = re.search(r"threshold:\s*\[([^\]]+)\]", block)
    assert m, "threshold 가 배열이 아니다 — 큰 요소는 0.4 에 절대 닿지 않으므로 낮은 단계가 필요하다"
    steps = [float(x.strip()) for x in m.group(1).split(",")]
    assert min(steps) <= 0.05, f"낮은 단계가 없다: {steps}"


def test_one_shot_guard_survived_the_fix():
    """⚠️ 수정하다 한 번만 쏘는 가드를 깨면 모수가 부풀고 메타 학습이 오염된다."""
    block = _vc_block()
    assert "var fired = false;" in block and "if(fired) return;" in block
    assert "fired = true;" in block
    assert "io.disconnect()" in block


def test_viewcontent_still_carries_utm_and_both_pixels():
    """수정이 파라미터·Meta 발화를 떨어뜨리지 않았는지."""
    block = _vc_block()
    for token in ("utm_source", "utm_medium", "utm_campaign", "utm_content",
                  "content_type", "pricing_and_rooms"):
        assert token in block, f"ViewContent 에서 {token} 이 사라졌다"
    assert "fbq('track','ViewContent'" in block, "Meta ViewContent 가 사라졌다"
    assert "gtag('event','ViewContent'" in block, "GA4 ViewContent 가 사라졌다"
