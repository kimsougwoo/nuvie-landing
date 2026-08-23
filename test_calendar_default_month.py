# -*- coding: utf-8 -*-
"""예약현황 달력의 첫 화면이 현재 월에서 시작하는지 고정한다."""
import re
from pathlib import Path


INDEX = Path(__file__).with_name("index.html")


def test_calendar_starts_in_current_month_by_default():
    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r"var\s+monthOffset\s*=\s*([^,]+),\s*EVENTS", html)
    assert match, "달력 초기 monthOffset 배선을 찾지 못함"
    assert match.group(1).strip() == "0", (
        "예약현황은 매월 20일 이후에도 다음 달이 아니라 현재 월에서 시작해야 함"
    )
