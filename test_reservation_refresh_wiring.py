# -*- coding: utf-8 -*-
"""예약현황 갱신 런처가 실제 랜딩 저장소를 호출하는지 검증한다."""
from pathlib import Path


LANDING = Path(r"C:\Users\kgr96\Projects\nuvie-landing")
RUNNER = Path(r"C:\Users\kgr96\nuvie_morning\run_cs_watch.bat")


def test_cs_watch_points_to_the_actual_landing_repo_and_log():
    text = RUNNER.read_text(encoding="utf-8")
    expected_script = f'"{LANDING}\\build_availability.py" --push'
    expected_log = f'>> "{LANDING}\\refresh_log.txt" 2>&1'

    assert LANDING.joinpath("build_availability.py").is_file()
    assert expected_script in text
    assert expected_log in text
    assert 'Python310\\python.exe" nuvie-landing\\build_availability.py' not in text


def test_cs_watch_keeps_the_hidden_launcher_and_working_home():
    text = RUNNER.read_text(encoding="utf-8")
    assert "cd /d C:\\Users\\kgr96" in text
    assert "nuvie_morning\\booking_watch.py" not in text


def test_availability_push_decodes_git_output_as_utf8_on_windows():
    text = LANDING.joinpath("build_availability.py").read_text(encoding="utf-8")
    assert text.count('capture_output=True, text=True, encoding="utf-8", errors="replace"') >= 2
