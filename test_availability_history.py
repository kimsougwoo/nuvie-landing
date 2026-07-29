# -*- coding: utf-8 -*-
"""과거 예약 누적(히스토리) 신규 기능 테스트 — repo 밖 로컬 파일에 append-only 병합.

배경: 아워플레이스 iCal은 과거 예약을 보존하지 않는다(실측 오늘 이전 VEVENT 0건) → 폴링
      스냅샷을 남기지 않으면 과거 예약 기록이 영구 소실된다. 표시 여부는 아직 미정이라
      히스토리는 공개 레포(availability.json) 밖, HISTORY_PATH(=C:\\Users\\kgr96\\nuvie_morning
      \\data\\availability_history.json)에만 쌓는다.

⚠️ 실 파일시스템 경로(HISTORY_PATH)는 매 테스트에서 tmp_path로 monkeypatch — 실 nuvie_morning
   데이터 디렉터리를 절대 건드리지 않는다. 실 네트워크·git push도 전부 monkeypatch.
"""
import os
import sys
import json
import datetime
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_availability as BA


TODAY = datetime.date.today()


def _iso(offset_days):
    return (TODAY + datetime.timedelta(days=offset_days)).isoformat()


def _ev(date_iso, start, end, room):
    return {"date": date_iso, "start": float(start), "end": float(end), "room": room}


def _seed_repo(old_events):
    """임시 repo 디렉터리에 직전 availability.json을 심고 경로 반환(실 파일 미접촉)."""
    d = tempfile.mkdtemp(prefix="nuvie_avail_hist_test_")
    with open(os.path.join(d, "availability.json"), "w", encoding="utf-8") as f:
        json.dump({"events": old_events, "busyDates": sorted({e["date"] for e in old_events})},
                  f, ensure_ascii=False)
    return d


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _ics_event(date_iso, start_h, end_h):
    d = date_iso.replace("-", "")
    return (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        f"DTSTART:{d}T{start_h:02d}0000\r\n"
        f"DTEND:{d}T{end_h:02d}0000\r\n"
        "UID:test-uid-hist\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


ICS_EMPTY = "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"


# ── (a) 과거로 넘어간 이벤트가 히스토리에 들어간다 ───────────────────
def test_past_event_moves_into_history(tmp_path, monkeypatch):
    hist_path = str(tmp_path / "availability_history.json")
    monkeypatch.setattr(BA, "HISTORY_PATH", hist_path)

    old = [_ev(_iso(-2), 10, 12, "A"), _ev(_iso(5), 13, 15, "B")]  # 하나는 이미 과거, 하나는 미래
    BA._update_history(old, TODAY)

    hist = _read_json(hist_path)
    assert hist["events"] == [_ev(_iso(-2), 10, 12, "A")], hist["events"]  # 과거만 들어감


def test_history_append_only_dedup(tmp_path, monkeypatch):
    """반복 호출해도 중복 없이 누적되고, 기존 기록은 절대 사라지거나 바뀌지 않는다(append-only)."""
    hist_path = str(tmp_path / "availability_history.json")
    monkeypatch.setattr(BA, "HISTORY_PATH", hist_path)

    old1 = [_ev(_iso(-3), 9, 11, "A")]
    BA._update_history(old1, TODAY)
    old2 = [_ev(_iso(-3), 9, 11, "A"), _ev(_iso(-1), 14, 16, "B")]  # 첫번째는 중복, 두번째는 신규 과거
    BA._update_history(old2, TODAY)

    hist = _read_json(hist_path)
    got = sorted(hist["events"], key=lambda e: e["date"])
    want = sorted([_ev(_iso(-3), 9, 11, "A"), _ev(_iso(-1), 14, 16, "B")], key=lambda e: e["date"])
    assert got == want, got
    assert len(hist["events"]) == 2  # 중복 제거됨(3번째 호출에도 안 늘어남 확인)

    BA._update_history(old2, TODAY)
    assert len(_read_json(hist_path)["events"]) == 2


# ── (b) fetch 실패 시 히스토리가 오염되지 않는다 ─────────────────────
def test_fetch_fail_does_not_corrupt_history(tmp_path, monkeypatch):
    """A룸 fetch 실패해도:
    (1) A의 아직 미래인 이벤트는 히스토리로 새지 않는다(실패=모름≠사라짐 — 미래를 과거로 오판 금지).
    (2) A의 이미 과거인 직전값은 정상적으로 히스토리에 들어간다(날짜만으로 판단, fetch 상태 무관).
    """
    hist_path = str(tmp_path / "availability_history.json")
    monkeypatch.setattr(BA, "HISTORY_PATH", hist_path)

    old = [_ev(_iso(-1), 9, 11, "A"),    # A: 이미 과거 → 히스토리로 가야 정상
           _ev(_iso(10), 14, 16, "A"),   # A: 아직 미래 → fetch 실패해도 사라진 걸로 오판 금지
           _ev(_iso(20), 10, 12, "B")]   # B: 미래, B는 정상 fetch
    repo = _seed_repo(old)

    monkeypatch.setattr(BA, "load_env", lambda *a, **k: {
        "ICAL_URL_HOURPLACE": "urlA", "ICAL_URL_HOURPLACE_B": "urlB"})

    def fake_fetch(url):
        if url == "urlA":
            return None  # A 페치 실패
        return _ics_event(_iso(21), 10, 12)  # B는 정상, 다른 신선 이벤트

    monkeypatch.setattr(BA, "fetch", fake_fetch)
    monkeypatch.setattr(BA, "push_changes", lambda repo, n: True)
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: None)

    BA.main(argv=["--push"], repo=repo)

    hist = _read_json(hist_path)
    # 과거로 넘어간 A 이벤트만 히스토리에 존재 — 미래 A 이벤트(fetch 실패 룸)는 없음
    assert hist["events"] == [_ev(_iso(-1), 9, 11, "A")], hist["events"]

    # availability.json 쪽엔 A의 미래값(직전 유지)이 여전히 살아있어야 함(사라진 걸로 오판 안 됨)
    ev = _read_json(os.path.join(repo, "availability.json"))["events"]
    a_events = [e for e in ev if e["room"] == "A"]
    assert _ev(_iso(10), 14, 16, "A") in a_events, a_events


def test_both_fetch_fail_history_still_updates_from_dates_only(tmp_path, monkeypatch):
    """두 룸 다 fetch 실패(push 자체 스킵되는 케이스)해도, 히스토리는 old_events의 날짜만 보고
    독립적으로 갱신된다 — fetch 실패가 히스토리를 막거나 오염시키지 않는다."""
    hist_path = str(tmp_path / "availability_history.json")
    monkeypatch.setattr(BA, "HISTORY_PATH", hist_path)

    old = [_ev(_iso(-1), 9, 11, "A"), _ev(_iso(5), 13, 15, "B")]
    repo = _seed_repo(old)

    monkeypatch.setattr(BA, "load_env", lambda *a, **k: {
        "ICAL_URL_HOURPLACE": "urlA", "ICAL_URL_HOURPLACE_B": "urlB"})
    monkeypatch.setattr(BA, "fetch", lambda url: None)  # 둘 다 실패
    monkeypatch.setattr(BA, "push_changes", lambda repo, n: (_ for _ in ()).throw(
        AssertionError("push 금지")))
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: None)

    BA.main(argv=["--push"], repo=repo)

    hist = _read_json(hist_path)
    assert hist["events"] == [_ev(_iso(-1), 9, 11, "A")], hist["events"]


# ── (c) availability.json엔 과거 이벤트가 절대 포함되지 않는다 ───────
def test_availability_json_never_contains_past(tmp_path, monkeypatch):
    """A룸 fetch 실패로 직전값(과거+미래 섞임)이 그대로 유입돼도, compute_events의 날짜 필터가
    과거 이벤트를 걸러내 availability.json에는 미래 이벤트만 남는다."""
    hist_path = str(tmp_path / "availability_history.json")
    monkeypatch.setattr(BA, "HISTORY_PATH", hist_path)

    old = [_ev(_iso(-5), 9, 11, "A"), _ev(_iso(3), 13, 15, "A")]
    repo = _seed_repo(old)

    monkeypatch.setattr(BA, "load_env", lambda *a, **k: {
        "ICAL_URL_HOURPLACE": "urlA", "ICAL_URL_HOURPLACE_B": "urlB"})

    def fake_fetch(url):
        return None if url == "urlA" else ICS_EMPTY  # A 실패(직전값 유입), B 정상·빈

    monkeypatch.setattr(BA, "fetch", fake_fetch)
    monkeypatch.setattr(BA, "push_changes", lambda repo, n: True)
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: None)

    BA.main(argv=["--push"], repo=repo)

    ev = _read_json(os.path.join(repo, "availability.json"))["events"]
    assert ev == [_ev(_iso(3), 13, 15, "A")], ev
    assert all(e["date"] >= TODAY.isoformat() for e in ev), ev
    assert _ev(_iso(-5), 9, 11, "A") not in ev


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
