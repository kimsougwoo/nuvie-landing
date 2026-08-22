# -*- coding: utf-8 -*-
"""node 기반 .js 계약 테스트를 pytest 스위트에 편입 (2026-08-22).

왜: `test_attribution_contract.js` 가 없어진 `enrich()` API 를 참조하며 오래 썩어 있었는데
    **pytest 가 .js 를 안 돌려서 아무도 못 잡았다**(node 수동 실행만 실패). 인스턴스(그 파일)를
    고치는 데 그치지 않고 **클래스**(「.js 계약이 CI 밖에 있음」)를 고친다 — 이제 `pytest` 가
    node 로 각 .js 를 돌려 exit 0 을 강제한다. node 가 없는 환경에서는 조용히 skip(가짜 실패 방지).
"""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
JS_CONTRACT_TESTS = ["test_attribution_contract.js", "test_interest_api.js", "test_webmcp.js"]
_NODE = shutil.which("node")


@pytest.mark.skipif(_NODE is None, reason="node 미설치 — .js 계약 테스트 건너뜀")
@pytest.mark.parametrize("js", JS_CONTRACT_TESTS)
def test_js_contract_passes(js):
    path = HERE / js
    # 🔴 Codex 독립검토(2026-08-22) #5 반영: 파일 누락을 skip 하면 계약 파일이 지워져도 초록으로 위장된다.
    #   node 부재(환경)만 skip 하고, 계약 파일 부재는 «회귀»이므로 fail 한다.
    assert path.exists(), f"{js} 계약 파일이 사라졌다 — 삭제/이동됐는지 확인(회귀)"
    r = subprocess.run([_NODE, str(path)], cwd=str(HERE),
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"{js} node 계약 테스트 실패:\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}"
