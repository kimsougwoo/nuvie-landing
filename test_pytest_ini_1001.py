# -*- coding: utf-8 -*-
"""랜딩 폴더 전용 pytest 설정(10-01). 랜딩 폴더에서 인자 없이 `pytest` 를 돌리면 홈 C:\\Users\\kgr96\\pytest.ini 가 위에서 잡혀
(rootdir = 홈, norecursedirs 에 «.*» 없음) .vercel/output/static 의 테스트 복사본까지 수집하고 이름이 겹쳐 수집 오류 9건이 났다.
랜딩 폴더에 자체 pytest.ini 를 두면 rootdir 이 여기로 고정되고 점 폴더를 건너뛴다. 배포에는 싣지 않는다."""
import configparser
from pathlib import Path

ROOT = Path(__file__).parent


def test_landing_has_own_pytest_ini_skipping_dot_dirs():
    cp = configparser.ConfigParser()
    cp.read(ROOT / "pytest.ini", encoding="utf-8")
    assert cp.has_section("pytest"), "랜딩 폴더 전용 pytest.ini 가 있어야 함"
    dirs = cp.get("pytest", "norecursedirs").split()
    assert ".*" in dirs, "점 폴더(.vercel 배포 복사본 등)를 건너뛰어야 함"


def test_pytest_ini_is_not_deployed():
    lines = [l.strip() for l in (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()]
    assert "pytest.ini" in lines
