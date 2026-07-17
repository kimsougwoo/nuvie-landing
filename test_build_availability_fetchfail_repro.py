# -*- coding: utf-8 -*-
"""페치 실패↔예약0 구분 실패(#2) 재현 테스트 — 3R CONFIRMED 🔴HIGH (2026-07-17).

버그: fetch()가 타임아웃/5xx/순단 시 print만 하고 빈 문자열 ""를 반환 →
      parse_events("", room)→[] 로 흘러 '진짜 실패'와 '예약 0건'을 구분 못 함.
      A룸 fetch만 순단해도 꽉 찬 날짜가 사라져 changed=True→git commit+push→Vercel
      재배포로 공개 예약현황이 '예약된 날'을 '가능'으로 표시(둘 다 실패면 120일 전체 '가능').
      형제 nuvie_morning/booking_watch.py:fetch_ical 은 실패 시 None 반환으로 이미 구분 —
      이 파일엔 그 P0-1 수정이 없음.

수정: fetch() 실패 시 None(구분가능 실패신호). 호출부(compute_events)는 None인 룸을
      이번 런에서 제외(직전 availability.json 값 유지). 두 iCal 모두 실패면 main()이
      push 자체 스킵 + 경보. 정상 빈 캘린더(진짜 예약0)는 기존대로 push.

⚠️ 실 네트워크·git push 금지(전부 monkeypatch).
"""
import os
import sys
import json
import datetime
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_availability as BA


# ── 공용 픽스처 ───────────────────────────────────────────────
TODAY = datetime.date.today()


def _fut(offset_days):
    return (TODAY + datetime.timedelta(days=offset_days)).isoformat()


def _ics_event(date_iso, start_h, end_h):
    """parse_events가 읽는 VEVENT 한 건짜리 iCal 문자열(로컬 시각, Z 없음)."""
    d = date_iso.replace("-", "")
    return (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\n"
        f"DTSTART:{d}T{start_h:02d}0000\r\n"
        f"DTEND:{d}T{end_h:02d}0000\r\n"
        "UID:test-uid-1\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


ICS_EMPTY = "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"  # 정상 빈 캘린더(진짜 예약 0건)


def _ev(date_iso, start, end, room):
    return {"date": date_iso, "start": float(start), "end": float(end), "room": room}


def _seed_repo(old_events):
    """임시 repo 디렉터리에 직전 availability.json을 심고 경로 반환(실 파일 미접촉)."""
    d = tempfile.mkdtemp(prefix="nuvie_avail_test_")
    with open(os.path.join(d, "availability.json"), "w", encoding="utf-8") as f:
        json.dump({"events": old_events, "busyDates": sorted({e["date"] for e in old_events})},
                  f, ensure_ascii=False)
    return d


def _read_json(repo):
    with open(os.path.join(repo, "availability.json"), encoding="utf-8") as f:
        return json.load(f)


# ── #2 핵심: 실패 신호 구분 ────────────────────────────────────
def test_fetch_returns_none_on_failure(monkeypatch):
    """fetch()는 네트워크 실패 시 '' 가 아니라 None(구분가능 실패신호)을 반환해야 한다.
    수정 전: except에서 '' 반환 → parse_events('')=[] 로 '예약0'과 동일 취급 → FAIL."""
    def boom(*a, **k):
        raise TimeoutError("simulated blip")
    monkeypatch.setattr(BA.urllib.request, "urlopen", boom)
    assert BA.fetch("https://example.test/a.ics") is None


# ── (a) 한 룸 실패 → 그 룸 직전값 유지, 다른 룸은 신선 반영 ──────
def test_partial_fail_preserves_failed_room(monkeypatch):
    """A 페치 실패 + B 정상: A는 직전값 유지(꽉 찬 날 안 사라짐), B는 신선 반영. push 판단됨."""
    old = [_ev(_fut(10), 10, 12, "A"), _ev(_fut(11), 13, 15, "B")]
    repo = _seed_repo(old)

    def fake_fetch(url):
        return None if url == "urlA" else _ics_event(_fut(20), 16, 18)  # B만 신선(다른 날)

    monkeypatch.setattr(BA, "load_env", lambda *a, **k: {
        "ICAL_URL_HOURPLACE": "urlA", "ICAL_URL_HOURPLACE_B": "urlB"})
    monkeypatch.setattr(BA, "fetch", fake_fetch)
    pushes = []
    monkeypatch.setattr(BA, "push_changes", lambda repo, n: pushes.append(n) or True)
    alerts = []
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: alerts.append(msg))

    BA.main(argv=["--push"], repo=repo)

    ev = _read_json(repo)["events"]
    a = [e for e in ev if e["room"] == "A"]
    b = [e for e in ev if e["room"] == "B"]
    # A(실패)는 직전값 그대로 보존 — 빈 []로 덮이면 예약된 날이 '가능'으로 뒤집힘
    assert a == [_ev(_fut(10), 10, 12, "A")], a
    # B(정상)는 신선 반영
    assert b == [_ev(_fut(20), 16, 18, "B")], b
    # 한 룸이라도 신선 페치가 있으면 변경분 push 진행, 총실패 경보는 아님
    assert pushes == [len(ev)], pushes
    assert alerts == [], alerts


# ── (b) 두 룸 모두 실패 → push 스킵 + 경보, 파일 미변경 ─────────
def test_both_fail_skips_push_and_alerts(monkeypatch):
    """A·B 둘 다 실패: git push 자체 스킵(직전 파일 유지) + #이상감지 경보 1회."""
    old = [_ev(_fut(10), 10, 12, "A"), _ev(_fut(11), 13, 15, "B")]
    repo = _seed_repo(old)
    before = _read_json(repo)

    monkeypatch.setattr(BA, "load_env", lambda *a, **k: {
        "ICAL_URL_HOURPLACE": "urlA", "ICAL_URL_HOURPLACE_B": "urlB"})
    monkeypatch.setattr(BA, "fetch", lambda url: None)  # 둘 다 실패
    pushes = []
    monkeypatch.setattr(BA, "push_changes", lambda repo, n: pushes.append(n) or True)
    alerts = []
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: alerts.append(msg))

    BA.main(argv=["--push"], repo=repo)

    assert pushes == [], "두 룸 실패 시 push 하면 120일 전체가 '가능'으로 배포됨"
    assert len(alerts) == 1, alerts
    # 직전 availability.json 미접촉(예약된 날 그대로)
    assert _read_json(repo) == before, "총실패 시 파일은 직전값 그대로 유지"


# ── (c) 정상 빈 캘린더(진짜 예약0)는 기존대로 push ──────────────
def test_genuine_empty_still_pushes(monkeypatch):
    """두 룸 모두 정상 응답이나 예약 0건 → 진짜 0건이므로 빈 캘린더로 push(예약 해제 반영)."""
    old = [_ev(_fut(10), 10, 12, "A")]  # 직전엔 예약 있었음
    repo = _seed_repo(old)

    monkeypatch.setattr(BA, "load_env", lambda *a, **k: {
        "ICAL_URL_HOURPLACE": "urlA", "ICAL_URL_HOURPLACE_B": "urlB"})
    monkeypatch.setattr(BA, "fetch", lambda url: ICS_EMPTY)  # 둘 다 정상·빈
    pushes = []
    monkeypatch.setattr(BA, "push_changes", lambda repo, n: pushes.append(n) or True)
    alerts = []
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: alerts.append(msg))

    BA.main(argv=["--push"], repo=repo)

    ev = _read_json(repo)["events"]
    assert ev == [], ev                       # 진짜 0건 → 빈 캘린더
    assert pushes == [0], pushes              # push 진행(예약 해제 공개 반영)
    assert alerts == [], alerts               # 실패 아님 → 경보 없음


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
