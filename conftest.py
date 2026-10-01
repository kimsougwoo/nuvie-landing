# -*- coding: utf-8 -*-
"""랜딩 테스트 공용 — 실제 디스코드 알림을 보내지 않는다(2026-10-02 폴백 점검 우선순위 1).

build_availability 의 새 알림 경로(_alert)는 nuvie_morning.report.alert_throttled 로 나간다.
테스트가 실패 경로를 태우면 진짜 #이상감지로 나가므로, 모든 테스트에서 기록용으로 바꿔 둔다.
알림을 확인하려는 테스트는 `availability_alerts` 픽스처로 받은 목록을 본다.
(배포 제외: .vercelignore 의 *.py)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def availability_alerts(monkeypatch):
    sent = []
    try:
        import build_availability as BA
    except Exception:
        yield sent
        return
    if hasattr(BA, "_alert"):
        monkeypatch.setattr(BA, "_alert", lambda key, msg: sent.append((key, msg)))
    yield sent
