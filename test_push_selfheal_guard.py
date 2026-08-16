# -*- coding: utf-8 -*-
"""🔴 재현→수정: 30분 크론의 «자가치유»가 작업 중인 미커밋 편집을 지웠다 (2026-08-16 실사고).

## 무슨 일이 있었나
`push_changes` 는 rebase 충돌 시 「로컬 커밋이 availability.json 만 건드렸으면 origin 에 맞춘다」로
`git reset --hard origin/main` 을 돌린다(2026-07-23 스톨 자가치유). 그런데
- 판정에 쓰던 `touched` 는 `git diff origin/main..HEAD` = **커밋된 차이**만 본다.
- `reset --hard` 는 **워킹트리도** 되돌린다.
⇒ 그날 편집 중이던 `build_availability.py` · `index.html` · 테스트 **3파일이 통째로 사라졌다**
   (refresh_log 에 「스톨 자가치유」 한 줄, reflog 에 `reset: moving to origin/main`).

## 계약
**작업 중인 미커밋 변경이 하나라도 있으면 자가치유를 하지 않는다.**
스톨은 눈에 보이고 다음 런이 다시 시도하지만, 지워진 작업은 되돌릴 수 없다.
"""
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
import build_availability as BA


def _run(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")


def _init_repo(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _run(repo, "init", "-q", "-b", "main")
    _run(repo, "config", "user.email", "t@t"); _run(repo, "config", "user.name", "t")
    (repo / "availability.json").write_text('{"events":[]}', encoding="utf-8")
    (repo / "index.html").write_text("<html>원본</html>", encoding="utf-8")
    _run(repo, "add", "-A"); _run(repo, "commit", "-q", "-m", "init")
    return repo


def test_깨끗하면_변경없음(tmp_path):
    repo = _init_repo(tmp_path)
    assert BA._worktree_dirty_besides_availability(repo) == set()


def test_availability만_바뀐_건_자가치유_대상이다(tmp_path):
    """이 파일은 봇 전용이라 덮어써도 안전 — 자가치유를 막지 않아야 한다(과잉 차단 방지)."""
    repo = _init_repo(tmp_path)
    (repo / "availability.json").write_text('{"events":[1]}', encoding="utf-8")
    assert BA._worktree_dirty_besides_availability(repo) == set()


def test_다른_파일이_수정중이면_잡는다(tmp_path):
    """🔴 이게 실사고 지점 — 편집 중인 소스가 있으면 리셋을 막아야 한다."""
    repo = _init_repo(tmp_path)
    (repo / "index.html").write_text("<html>작업중</html>", encoding="utf-8")
    assert BA._worktree_dirty_besides_availability(repo) == {"index.html"}


def test_추적안된_새_파일도_잡는다(tmp_path):
    """새로 쓰던 파일이 제일 위험하다 — git 에 사본이 없어 복구 수단이 아예 없다."""
    repo = _init_repo(tmp_path)
    (repo / "새기능.py").write_text("print(1)", encoding="utf-8")
    assert BA._worktree_dirty_besides_availability(repo), "미추적 파일을 놓쳤다"


def test_판정불가면_더럽다고_본다(tmp_path):
    """git 이 안 돌면 «모른다» — 모를 때 파괴하는 쪽으로 기울면 안 된다."""
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    assert BA._worktree_dirty_besides_availability(not_a_repo), "판정 불가를 깨끗함으로 취급했다"


def test_자가치유_분기가_가드를_실제로_호출한다():
    """순수함수만 만들고 배선을 잊는 사고 방지 — 소스에 호출이 있는지 본다."""
    src = open(__file__.replace("test_push_selfheal_guard.py", "build_availability.py"),
               encoding="utf-8").read()
    i = src.index("def push_changes")
    body = src[i:]
    guard = body.index("_worktree_dirty_besides_availability")
    reset = body.index('"reset", "--hard"')
    assert guard < reset, "가드가 reset --hard 보다 뒤에 있다(순서가 뒤집히면 무의미)"
