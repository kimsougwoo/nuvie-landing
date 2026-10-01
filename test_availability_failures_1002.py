# -*- coding: utf-8 -*-
"""예약 달력(availability.json) 조용한 대체 제거 — 2026-10-02 폴백 점검 «우선순위 1» 1~7.

대표 10-01 «폴백 같은 건 없어요. 망가지면 알리고 고치라고 감시 붙인 건데». 총괄 결정 문서
Desktop\\NUVIE_폴백점검_결정_2026-10-01.md 우선순위 1:
  1. iCal 주소가 200 인데 iCal 이 아닌 본문(점검 페이지 등)이면 0건으로 읽어 그 룸 예약을 지운다 → 실패로 센다.
  2. 예약 피드 한 룸만 실패하면 옛 값 유지 + 알림 없음 → 알린다.
  3. 차단 피드(청소·휴무) 실패를 세지 않는다 → 세고 알린다.
  4. 읽을 수 없는 VEVENT 를 조용히 버린다(그 시간이 비어 보임) → 건수를 세고 알린다.
  5. availability.json 이 깨졌고 룸 조회도 실패하면 그 룸이 빈 배열로 지워진다 → 멈춤(파일 미갱신) + 알림.
  6. .env 가 없거나 주소 키가 없으면 «미설정»으로 조용히 동결 → 알린다.
  7. push 실패가 print 뿐 → 알린다.
⚠️ 실 네트워크·git push 금지(전부 monkeypatch). 알림은 conftest 의 availability_alerts 가 받는다.
"""
import datetime
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_availability as BA  # noqa: E402

TODAY = datetime.date.today()


def _fut(n):
    return (TODAY + datetime.timedelta(days=n)).isoformat()


def _ics(date_iso, s, e, extra=""):
    d = date_iso.replace("-", "")
    return ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\n"
            f"DTSTART:{d}T{s:02d}0000\r\nDTEND:{d}T{e:02d}0000\r\nUID:u\r\nEND:VEVENT\r\n"
            + extra + "END:VCALENDAR\r\n")


def _ev(date_iso, s, e, room, kind="booking"):
    return {"date": date_iso, "start": float(s), "end": float(e), "room": room, "kind": kind}


def _repo(old_events=None, raw=None):
    d = tempfile.mkdtemp(prefix="nuvie_avail_fail_")
    p = os.path.join(d, "availability.json")
    with open(p, "w", encoding="utf-8") as f:
        if raw is not None:
            f.write(raw)
        else:
            json.dump({"events": old_events or [], "busyDates": [], "note": BA.NOTE}, f, ensure_ascii=False)
    return d


ALL_KEYS = {"ICAL_URL_HOURPLACE": "uA", "ICAL_URL_HOURPLACE_B": "uB",
            "ICAL_URL_BLOCK_A": "kA", "ICAL_URL_BLOCK_B": "kB"}


def _run(monkeypatch, fetch, env=None, repo=None, push=True):
    monkeypatch.setattr(BA, "load_env", lambda *a, **k: dict(ALL_KEYS if env is None else env))
    monkeypatch.setattr(BA, "fetch", fetch)
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: None)
    monkeypatch.setattr(BA, "_update_history", lambda *a, **k: None)
    pushes = []
    monkeypatch.setattr(BA, "push_changes", lambda r, n: pushes.append(n) or True)
    repo = repo or _repo()
    ok = BA.main(argv=["--push"] if push else [], repo=repo)
    return ok, repo, pushes


def _keys(alerts):
    return [k for k, _ in alerts]


# 1 ─────────────────────────────────────────────────────────────
def test_fetch_rejects_non_ical_body(monkeypatch):
    class R:
        def read(self):
            return "<html><body>점검 중입니다</body></html>".encode("utf-8")

    monkeypatch.setattr(BA.urllib.request, "urlopen", lambda *a, **k: R())
    assert BA.fetch("https://example.test/a.ics") is None


def test_fetch_still_accepts_empty_calendar(monkeypatch):
    class R:
        def read(self):
            return b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"

    monkeypatch.setattr(BA.urllib.request, "urlopen", lambda *a, **k: R())
    assert BA.fetch("https://example.test/a.ics") == "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"


# 2 ─────────────────────────────────────────────────────────────
def test_one_booking_feed_failing_alerts_and_keeps_old_value(monkeypatch, availability_alerts):
    old = [_ev(_fut(10), 10, 12, "A")]
    fresh_b = _ics(_fut(20), 16, 18)
    ok, repo, pushes = _run(monkeypatch, lambda u: None if u == "uA" else (fresh_b if u == "uB" else _ics(_fut(30), 1, 2)),
                            repo=_repo(old))
    evs = json.load(open(os.path.join(repo, "availability.json"), encoding="utf-8"))["events"]
    assert [e for e in evs if e["room"] == "A" and e["kind"] == "booking"] == old
    assert "availability_feed_failed" in _keys(availability_alerts)
    assert any("A룸" in m for k, m in availability_alerts if k == "availability_feed_failed")


# 3 ─────────────────────────────────────────────────────────────
def test_block_feed_failure_is_alerted(monkeypatch, availability_alerts):
    ok, repo, pushes = _run(monkeypatch, lambda u: None if u == "kB" else _ics(_fut(5), 10, 12))
    msgs = [m for k, m in availability_alerts if k == "availability_feed_failed"]
    assert msgs and any("B룸 차단" in m for m in msgs)


# 4 ─────────────────────────────────────────────────────────────
def test_parse_events_counts_unreadable_vevents():
    bad = "BEGIN:VEVENT\r\nDTSTART:2026XX01T100000\r\nDTEND:20261001T120000\r\nEND:VEVENT\r\n"
    stats = {}
    out = BA.parse_events(_ics("2026-10-05", 10, 12, extra=bad), "A", stats=stats)
    assert len(out) == 1
    assert stats.get("skipped") == 1


def test_unreadable_vevent_is_alerted(monkeypatch, availability_alerts):
    bad = "BEGIN:VEVENT\r\nDTSTART:2026XX01T100000\r\nEND:VEVENT\r\n"
    feed = _ics(_fut(5), 10, 12, extra=bad)
    _run(monkeypatch, lambda u: feed if u == "uA" else _ics(_fut(6), 10, 12))
    msgs = [m for k, m in availability_alerts if k == "availability_unreadable_events"]
    assert msgs and "1" in msgs[0]


# 5 ─────────────────────────────────────────────────────────────
def test_corrupt_previous_file_with_failed_feed_stops_without_writing(monkeypatch, availability_alerts):
    repo = _repo(raw="{ broken json")
    ok, repo, pushes = _run(monkeypatch, lambda u: None if u == "uA" else _ics(_fut(5), 10, 12), repo=repo)
    assert ok is False
    assert open(os.path.join(repo, "availability.json"), encoding="utf-8").read() == "{ broken json"
    assert pushes == []
    assert "availability_previous_unreadable" in _keys(availability_alerts)


def test_corrupt_previous_file_with_all_feeds_ok_rewrites(monkeypatch, availability_alerts):
    repo = _repo(raw="{ broken json")
    ok, repo, pushes = _run(monkeypatch, lambda u: _ics(_fut(5), 10, 12))
    assert ok is True


# 6 ─────────────────────────────────────────────────────────────
def test_missing_env_key_is_alerted(monkeypatch, availability_alerts):
    env = dict(ALL_KEYS)
    env.pop("ICAL_URL_HOURPLACE_B")
    _run(monkeypatch, lambda u: _ics(_fut(5), 10, 12), env=env)
    msgs = [m for k, m in availability_alerts if k == "availability_config_missing"]
    assert msgs and "ICAL_URL_HOURPLACE_B" in msgs[0]


def test_missing_env_file_is_alerted(monkeypatch, availability_alerts):
    monkeypatch.setattr(BA, "ENV", os.path.join(tempfile.mkdtemp(), "no.env"))
    monkeypatch.setattr(BA, "fetch", lambda u: _ics(_fut(5), 10, 12))
    monkeypatch.setattr(BA, "_alert_fetch_fail", lambda msg: None)
    monkeypatch.setattr(BA, "_update_history", lambda *a, **k: None)
    monkeypatch.setattr(BA, "push_changes", lambda r, n: True)
    BA.main(argv=[], repo=_repo())
    assert "availability_config_missing" in _keys(availability_alerts)


def test_all_keys_present_no_config_alert(monkeypatch, availability_alerts):
    _run(monkeypatch, lambda u: _ics(_fut(5), 10, 12))
    assert availability_alerts == []


# 7 ─────────────────────────────────────────────────────────────
def test_push_failure_is_alerted(monkeypatch, availability_alerts):
    import subprocess

    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, a[0] if a else "git")

    monkeypatch.setattr(BA, "_landing_session_hold", lambda: None)
    monkeypatch.setattr(BA.subprocess, "run", boom)
    assert BA.push_changes(_repo(), 3) is False
    assert "availability_push_failed" in _keys(availability_alerts)


def test_alert_wrapper_uses_report_alert_text_and_throttle(monkeypatch):
    """_alert 는 엔진 report.alert_throttled 로 보낸다(조용히 print 로 끝내지 않는다)."""
    src = open(BA.__file__, encoding="utf-8").read()
    body = src[src.index("def _alert("):]
    body = body[:body.index("\ndef ", 1)]
    assert "alert_throttled" in body
