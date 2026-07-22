# -*- coding: utf-8 -*-
"""재현 테스트 — 크론 dirty-잔류 스톨 버그 (2026-07-23).

버그(라이브 예약현황 8일 고착 사고): 종전 build_availability.main()은 매 런 `updated`
타임스탬프와 함께 availability.json을 **무조건 재기록**했다. 이벤트 변화가 없어도(changed=False)
파일이 dirty가 되고, --push 경로는 그냥 return → 워킹트리에 타임스탬프-only 변경이 남는다.
다음 30분 런의 `git pull --rebase`가 dirty 트리로 막혀 크론이 스톨했다.

수정: 변경이 있을 때만 파일을 쓰고, 변경 없을 때 --push는 멱등 `git checkout -- availability.json`로
잔류를 정리한다. 이 테스트는 임시 git repo로 그 불변식을 박제한다(네트워크 없음).

실행: cd C:\\Users\\kgr96\\Projects\\nuvie-landing && python -m pytest test_availability_no_dirty.py -q
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_availability as B


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def _init_repo(repo, events):
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    dst = os.path.join(repo, "availability.json")
    json.dump({"updated": "2026-07-01T00:00", "note": "n", "events": events,
               "busyDates": sorted({e["date"] for e in events})},
              open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _git(repo, "add", "availability.json")
    _git(repo, "commit", "-q", "-m", "init")
    return dst


EVENTS = [{"date": "2026-07-30", "start": 13.0, "end": 17.0, "room": "A"}]


def test_no_change_leaves_working_tree_clean(tmp_path, monkeypatch):
    """이벤트 변화 없음 + --push → 워킹트리가 clean해야 한다(스톨 원인 제거)."""
    repo = str(tmp_path)
    _init_repo(repo, EVENTS)
    monkeypatch.setattr(B, "load_env", lambda p: {})
    monkeypatch.setattr(B, "compute_events", lambda env, today, old: (list(EVENTS), 2, 0))
    called = []
    monkeypatch.setattr(B, "push_changes", lambda *a, **k: called.append(1))

    B.main(["x", "--push"], repo=repo)

    status = _git(repo, "status", "--porcelain").stdout.strip()
    assert status == "", f"변화 없는데 워킹트리가 dirty다(스톨 재발): {status!r}"
    assert called == [], "변화 없는데 push_changes가 호출됐다"


def test_no_change_cleans_preexisting_dirty(tmp_path, monkeypatch):
    """과거 버그로 이미 dirty해진 상태에서도 --push가 멱등 정리해 clean으로 만든다."""
    repo = str(tmp_path)
    dst = _init_repo(repo, EVENTS)
    # 과거 버그 재현: 타임스탬프만 바뀐 dirty 파일을 남겨둔다
    d = json.load(open(dst, encoding="utf-8"))
    d["updated"] = "2026-07-23T09:99"[:16]
    json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    assert _git(repo, "status", "--porcelain").stdout.strip() != ""  # 지금은 dirty

    monkeypatch.setattr(B, "load_env", lambda p: {})
    monkeypatch.setattr(B, "compute_events", lambda env, today, old: (list(EVENTS), 2, 0))
    monkeypatch.setattr(B, "push_changes", lambda *a, **k: None)
    B.main(["x", "--push"], repo=repo)

    assert _git(repo, "status", "--porcelain").stdout.strip() == "", "잔류 dirty가 정리되지 않았다"


def test_change_writes_and_pushes(tmp_path, monkeypatch):
    """이벤트가 바뀌면 파일을 쓰고 push_changes를 호출한다(정상 경로 보존)."""
    repo = str(tmp_path)
    dst = _init_repo(repo, EVENTS)
    new_events = EVENTS + [{"date": "2026-07-31", "start": 10.0, "end": 12.0, "room": "B"}]
    monkeypatch.setattr(B, "load_env", lambda p: {})
    monkeypatch.setattr(B, "compute_events", lambda env, today, old: (list(new_events), 2, 0))
    called = []
    monkeypatch.setattr(B, "push_changes", lambda repo, n: called.append(n))

    B.main(["x", "--push"], repo=repo)

    written = json.load(open(dst, encoding="utf-8"))
    assert written["events"] == new_events, "변경분이 파일에 기록되지 않았다"
    assert called == [len(new_events)], "변경인데 push_changes가 호출되지 않았다"


def test_fetch_fail_does_not_touch_file(tmp_path, monkeypatch):
    """페치 전멸(fetched_ok=0)이면 파일 미접촉(직전값 유지 — 공개사이트 안전, 기존 계약)."""
    repo = str(tmp_path)
    dst = _init_repo(repo, EVENTS)
    before = open(dst, encoding="utf-8").read()
    monkeypatch.setattr(B, "load_env", lambda p: {})
    monkeypatch.setattr(B, "compute_events", lambda env, today, old: ([], 0, 2))
    monkeypatch.setattr(B, "_alert_fetch_fail", lambda msg: None)
    monkeypatch.setattr(B, "push_changes", lambda *a, **k: (_ for _ in ()).throw(AssertionError("push 금지")))

    B.main(["x", "--push"], repo=repo)

    assert open(dst, encoding="utf-8").read() == before, "페치 실패인데 파일이 바뀌었다"
