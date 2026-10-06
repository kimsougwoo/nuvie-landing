# -*- coding: utf-8 -*-
"""예약현황 알림에도 #이상감지 첫 줄 라벨(owner=)을 붙인다 (2026-10-06 A2 · 총괄 요청).

엔진 report 는 owner 를 빠뜨린 알림에 «[대표님 할 일] 확인 필요»를 붙인다. 예약현황 알림은 대부분 AI 가 처리하는
기술 문제라 «할 일 없음»이어야 하고, 피드 주소 같은 설정값만 대표가 넣는다.
"""
import re
import sys
import types

import build_availability as BA


def test_every_alert_key_has_an_owner_label():
    src = open(BA.__file__, encoding="utf-8").read()
    keys = set(re.findall(r'_alert\(\s*"(availability_[a-z_]+)"', src)) | set(BA.OWNER_BY_KEY)
    assert keys and keys <= set(BA.OWNER_BY_KEY), keys - set(BA.OWNER_BY_KEY)


def test_alert_passes_owner_to_engine(monkeypatch):
    sent = []
    fake = types.SimpleNamespace(
        alert_text=lambda *a, **k: "본문",
        alert_throttled=lambda key, msg, hours=6, owner=None: sent.append((key, owner)) or (True, "ok"),
    )
    monkeypatch.setitem(sys.modules, "nuvie_morning.report", fake)
    pkg = types.ModuleType("nuvie_morning")
    pkg.report = fake
    monkeypatch.setitem(sys.modules, "nuvie_morning", pkg)
    # conftest 가 BA._alert 를 막아 두므로(실알림 방지) 원본 모듈을 따로 읽어 진짜 _alert 를 부른다.
    import importlib.util
    spec = importlib.util.spec_from_file_location("ba_real_1006", BA.__file__)
    real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real)
    real._alert("availability_push_failed", "push 실패")
    real._alert("availability_config_missing", "설정 없음")
    assert sent == [("availability_push_failed", "fyi"),
                    ("availability_config_missing", ("todo", "예약 피드 주소(.env) 설정을 넣어 주세요"))]
