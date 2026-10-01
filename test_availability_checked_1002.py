# -*- coding: utf-8 -*-
"""예약 달력 «확인 시각» 분리와 오래됨 경고 — 2026-10-02 폴백 점검 우선순위 1 의 8번(총괄 결정).

문제: 페이지는 availability.json 의 «마지막 변경 시각»만 보여 줬다. 예약이 안 바뀌면 크론이 정상이어도
      시각이 멈춰 보이고, 반대로 크론이 멈춰도 손님은 알 수 없었다. «오늘 N시 빈 시간» 라벨도 데이터 나이를 안 봤다.
결정(총괄 10-02): 확인 시각은 별도 파일 availability_checked.json. 예약이 바뀌면 지금처럼 그때 함께 push,
      안 바뀌어도 3시간마다 확인 시각만 push(하루 최대 8번 — 매 회차 쓰면 dirty 스톨 사고(07-23)와 배포 폭증).
      화면은 확인 시각이 6시간을 넘기면 빈 시간 라벨을 끄고 달력에 오래됨 경고. «마지막 변경» → «마지막 확인».
⚠️ 실 네트워크·git push 금지.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_availability as BA  # noqa: E402

ROOT = Path(__file__).parent
TODAY = datetime.date.today()
FUT = (TODAY + datetime.timedelta(days=5)).isoformat()


def _ics(date_iso, s, e):
    d = date_iso.replace("-", "")
    return ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\n"
            f"DTSTART:{d}T{s:02d}0000\r\nDTEND:{d}T{e:02d}0000\r\nUID:u\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")


EV = {"date": FUT, "start": 10.0, "end": 12.0, "room": "A", "kind": "booking"}
ENV = {"ICAL_URL_HOURPLACE": "uA", "ICAL_URL_HOURPLACE_B": "uB", "ICAL_URL_BLOCK_A": "kA", "ICAL_URL_BLOCK_B": "kB"}


def _repo(events, checked_age_h=None):
    d = tempfile.mkdtemp(prefix="nuvie_checked_")
    with open(os.path.join(d, "availability.json"), "w", encoding="utf-8") as f:
        json.dump({"events": events, "busyDates": sorted({e["date"] for e in events}), "note": BA.NOTE}, f, ensure_ascii=False)
    if checked_age_h is not None:
        t = datetime.datetime.now() - datetime.timedelta(hours=checked_age_h)
        with open(os.path.join(d, BA.CHECKED_FILE), "w", encoding="utf-8") as f:
            json.dump({"checked": t.isoformat(timespec="minutes")}, f)
    return d


def _run(monkeypatch, repo, feed_a):
    monkeypatch.setattr(BA, "load_env", lambda *a, **k: dict(ENV))
    monkeypatch.setattr(BA, "fetch", lambda u: feed_a if u == "uA" else "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n")
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: None)
    monkeypatch.setattr(BA, "_update_history", lambda *a, **k: None)
    pushes = []
    monkeypatch.setattr(BA, "push_changes", lambda r, n: pushes.append(n) or True)
    monkeypatch.setattr(BA.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    BA.main(argv=["--push"], repo=repo)
    return pushes


def _checked(repo):
    p = os.path.join(repo, BA.CHECKED_FILE)
    return json.load(open(p, encoding="utf-8"))["checked"] if os.path.exists(p) else None


# ── backend ────────────────────────────────────────────────────
def test_checked_file_name_and_interval():
    assert BA.CHECKED_FILE == "availability_checked.json"
    assert BA.CHECKED_PUSH_EVERY_H == 3


def test_changed_events_write_checked_and_push(monkeypatch):
    repo = _repo([], checked_age_h=0.5)
    pushes = _run(monkeypatch, repo, _ics(FUT, 10, 12))
    assert pushes, "예약이 바뀌었는데 push 하지 않았다"
    assert _checked(repo) and _checked(repo) >= (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat(timespec="minutes")


def test_unchanged_and_recent_check_does_nothing(monkeypatch):
    repo = _repo([EV], checked_age_h=1)
    before = _checked(repo)
    pushes = _run(monkeypatch, repo, _ics(FUT, 10, 12))
    assert pushes == [] and _checked(repo) == before


def test_unchanged_but_check_older_than_3h_pushes_checked_only(monkeypatch):
    repo = _repo([EV], checked_age_h=3.5)
    before_av = open(os.path.join(repo, "availability.json"), encoding="utf-8").read()
    pushes = _run(monkeypatch, repo, _ics(FUT, 10, 12))
    assert pushes, "3시간 넘게 확인 시각을 안 올렸는데 push 하지 않았다"
    assert open(os.path.join(repo, "availability.json"), encoding="utf-8").read() == before_av, "예약 파일은 그대로여야 한다"
    assert _checked(repo) > (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat(timespec="minutes")


def test_missing_checked_file_is_due(monkeypatch):
    repo = _repo([EV], checked_age_h=None)
    pushes = _run(monkeypatch, repo, _ics(FUT, 10, 12))
    assert pushes and _checked(repo)


def test_total_fetch_failure_does_not_touch_checked(monkeypatch):
    repo = _repo([EV], checked_age_h=5)
    before = _checked(repo)
    monkeypatch.setattr(BA, "load_env", lambda *a, **k: dict(ENV))
    monkeypatch.setattr(BA, "fetch", lambda u: None)
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: None)
    monkeypatch.setattr(BA, "_update_history", lambda *a, **k: None)
    monkeypatch.setattr(BA, "push_changes", lambda r, n: True)
    BA.main(argv=["--push"], repo=repo)
    assert _checked(repo) == before, "확인을 못 했는데 확인 시각을 올렸다(거짓 신선)"


def test_push_adds_checked_file_too():
    src = (ROOT / "build_availability.py").read_text(encoding="utf-8")
    body = src[src.index("def push_changes("):]
    body = body[:body.index("\ndef ", 1)]
    assert "CHECKED_FILE" in body


def test_dirty_check_ignores_checked_file():
    src = (ROOT / "build_availability.py").read_text(encoding="utf-8")
    body = src[src.index("def _worktree_dirty_besides_availability("):]
    body = body[:body.index("\ndef ", 1)]
    assert "CHECKED_FILE" in body


def test_checked_file_is_deployed():
    ignore = (ROOT / ".vercelignore").read_text(encoding="utf-8")
    assert "availability_checked.json" not in ignore and "*.json" not in ignore.split()


# ── front-end (node) ───────────────────────────────────────────
JS = (ROOT / "avail-label.js").read_text(encoding="utf-8")


def _js(expr):
    code = "var window={};var document=undefined;" + JS + "\nprocess.stdout.write(JSON.stringify(" + expr + "));"
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_fresh_within_6h():
    assert _js('window.nvAvailFresh("2026-10-02T09:00", Date.parse("2026-10-02T14:59:00+09:00"))') is True


def test_stale_after_6h():
    assert _js('window.nvAvailFresh("2026-10-02T09:00", Date.parse("2026-10-02T15:01:00+09:00"))') is False


def test_missing_or_bad_checked_is_stale():
    assert _js('window.nvAvailFresh(null, Date.parse("2026-10-02T10:00:00+09:00"))') is False
    assert _js('window.nvAvailFresh("garbage", Date.parse("2026-10-02T10:00:00+09:00"))') is False


def test_stale_hours_constant():
    assert re.search(r"STALE_H\s*=\s*6\b", JS)


def test_room_pages_check_freshness_before_labels():
    assert "availability_checked.json" in JS and "nvAvailFresh" in JS


HUB = (ROOT / "index.html").read_text(encoding="utf-8")


def test_hub_reads_checked_file_and_gates_labels():
    seg = HUB[HUB.index("function loadAvailability"):HUB.index("renderCal();              // 즉시 빈 달력")]
    assert "availability_checked.json" in seg
    assert "nvAvailFresh" in seg and "nvResetFreeLabels" in seg


def test_hub_label_says_last_checked_not_last_changed():
    assert "'마지막 변경 '" not in HUB
    assert "마지막 확인" in HUB


def test_hub_shows_stale_warning_text():
    assert "확인이 6시간 넘게" in HUB


def test_stale_warning_breaks_lines_instead_of_dot_joining():
    """랜딩 « · » 줄바꿈 규칙(대표 10-01): 문장을 잇는 «·»는 줄바꿈. 경고는 세 문장이라 줄로 나눈다."""
    seg = HUB[HUB.index("function setCheckedStatus"):HUB.index("function loadAvailability")]
    stale = seg[seg.index("확인이 6시간 넘게"):]
    stale = stale[:stale.index(";")]
    assert " · " not in stale, "문장을 «·»로 이었다 — 줄바꿈 규칙 위반"
    assert "pre-line" in seg, "줄바꿈이 화면에 보이려면 white-space:pre-line 이 필요하다"
