# -*- coding: utf-8 -*-
"""재현 테스트 — 공개 note 문구를 고쳐도 availability.json 이 안 바뀌던 문제 (2026-09-28).

build_availability.main() 은 «이벤트가 바뀔 때만» 파일을 쓴다(07-23 dirty 스톨 대책).
그래서 note 에서 «휴무»를 뺐어도(대표 결정 3) 배포된 availability.json 에는 예약이 바뀌는 첫 런까지
옛 note(«휴무·차단 캘린더», «(청소·점검·답사·휴무)»)가 남았다.

고친 뒤 계약:
- 이벤트가 같아도 note 가 다르면 한 번 새로 쓴다(changed=True).
- 그 다음 런은 note·이벤트가 모두 같으니 쓰지 않는다(스톨 대책 유지).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_availability as B

EVENTS = [{"date": "2026-10-07", "start": 14.0, "end": 17.0, "room": "A", "kind": "booking"}]
OLD_NOTE = ("free/busy (아워플레이스 iCal + 휴무·차단 캘린더 · 이름 비노출, 시간·룸·종류만). "
            "kind=booking 예약 / kind=block 예약 불가(청소·점검·답사·휴무). 참고용 — 확정은 아워플레이스.")


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def _init(repo, note):
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    dst = os.path.join(repo, "availability.json")
    json.dump({"updated": "2026-09-28T00:15", "note": note, "events": EVENTS,
               "busyDates": ["2026-10-07"]}, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 2026-10-02: 확인 시각 파일(없거나 3시간 넘으면 «확인만» push)도 방금 확인한 상태로 심는다.
    import datetime
    json.dump({"checked": datetime.datetime.now().isoformat(timespec="minutes")},
              open(os.path.join(repo, B.CHECKED_FILE), "w", encoding="utf-8"))
    _git(repo, "add", "availability.json", B.CHECKED_FILE)
    _git(repo, "commit", "-q", "-m", "init")
    return dst


def _run(monkeypatch, repo, called):
    monkeypatch.setattr(B, "load_env", lambda p: {})
    monkeypatch.setattr(B, "compute_events", lambda env, today, old, **kw: (list(EVENTS), 2, 0))
    monkeypatch.setattr(B, "_update_history", lambda *a, **k: None)
    monkeypatch.setattr(B, "push_changes", lambda repo, n: called.append(n))
    B.main(["x", "--push"], repo=repo)


def test_old_note_is_rewritten_even_if_events_same(tmp_path, monkeypatch):
    repo = str(tmp_path)
    dst = _init(repo, OLD_NOTE)
    called = []
    _run(monkeypatch, repo, called)
    written = json.load(open(dst, encoding="utf-8"))
    assert "휴무" not in written["note"], written["note"]
    assert written["events"] == EVENTS
    assert called == [len(EVENTS)], "note 가 바뀌었으면 push 경로를 타야 배포본이 바뀐다"


def test_same_note_and_events_is_still_noop(tmp_path, monkeypatch):
    repo = str(tmp_path)
    dst = _init(repo, B.NOTE)
    before = open(dst, encoding="utf-8").read()
    called = []
    _run(monkeypatch, repo, called)
    assert open(dst, encoding="utf-8").read() == before
    assert called == []
    assert _git(repo, "status", "--porcelain").stdout.strip() == ""
