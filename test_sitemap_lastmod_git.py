# -*- coding: utf-8 -*-
"""sitemap lastmod 는 체크아웃과 무관하게 같아야 한다 (2026-09-27).

종전: 소스 파일의 mtime 을 썼다 → 같은 커밋이라도 워크트리·새 클론·checkout 마다 mtime 이 달라
`build_rooms.py --check`(= test_build_rooms 의 check 테스트)가 체크아웃에 따라 실패했다(09-27 본체에서 실패·워크트리에서 통과).
이제: 커밋된 채 안 바뀐 파일은 git 마지막 커밋 날짜, 수정 중이거나 git 밖이면 mtime.
"""
import importlib.util
import os
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("build_rooms_lastmod_test", HERE / "build_rooms.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(repo, *args, env=None):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def test_clean_committed_file_uses_commit_date_not_mtime(tmp_path):
    br = _load()
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    f = repo / "index.html"
    f.write_text("x", encoding="utf-8")
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-01-02T12:00:00+09:00", GIT_COMMITTER_DATE="2026-01-02T12:00:00+09:00",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    _git(repo, "add", "index.html", env=env)
    _git(repo, "commit", "-q", "-m", "c", env=env)
    os.utime(f, (1893456000, 1893456000))          # 2030-01-01 — 체크아웃이 mtime 을 바꾼 상황
    assert br._source_lastmod(f) == "2026-01-02"


def test_dirty_file_uses_mtime(tmp_path):
    br = _load()
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    f = repo / "index.html"
    f.write_text("x", encoding="utf-8")
    env = dict(os.environ, GIT_AUTHOR_DATE="2026-01-02T12:00:00+09:00", GIT_COMMITTER_DATE="2026-01-02T12:00:00+09:00",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    _git(repo, "add", "index.html", env=env)
    _git(repo, "commit", "-q", "-m", "c", env=env)
    f.write_text("changed", encoding="utf-8")
    os.utime(f, (1893456000, 1893456000))
    assert br._source_lastmod(f) == "2030-01-01"


def test_file_outside_git_uses_mtime(tmp_path):
    br = _load()
    f = tmp_path / "rooms.json"
    f.write_text("{}", encoding="utf-8")
    os.utime(f, (1893456000, 1893456000))
    assert br._source_lastmod(f) == "2030-01-01"


# 2026-09-28: 두 갈래가 서로 다른 시간대로 날짜를 셌다.
#   clean = `git log --format=%cs`(커밋한 사람의 시간대 = 보통 KST) / dirty·git 밖 = mtime 을 UTC 로.
#   그래서 KST 00:00~08:59 에 고친 파일은 dirty 일 때 하루 전 날짜가 되고, 커밋하면 하루가 뛴다.
#   이제 둘 다 KST(+09:00) 한 가지로 센다. 종전 커밋은 KST 에서 만들어져 날짜가 그대로다.
_KST_0103_0100 = 1767369600   # 2026-01-02T16:00:00Z = 2026-01-03 01:00 KST


def _commit(repo, when):
    env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    _git(repo, "add", "index.html", env=env)
    _git(repo, "commit", "-q", "-m", "c", env=env)


def test_dirty_mtime_is_counted_in_kst_not_utc(tmp_path):
    br = _load()
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    f = repo / "index.html"
    f.write_text("x", encoding="utf-8")
    _commit(repo, "2026-01-01T12:00:00+09:00")
    f.write_text("changed", encoding="utf-8")
    os.utime(f, (_KST_0103_0100, _KST_0103_0100))
    assert br._source_lastmod(f) == "2026-01-03"


def test_clean_commit_date_is_counted_in_kst_whatever_committer_tz(tmp_path):
    br = _load()
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    f = repo / "index.html"
    f.write_text("x", encoding="utf-8")
    _commit(repo, "2026-01-02T11:00:00-05:00")        # = 2026-01-03 01:00 KST
    assert br._source_lastmod(f) == "2026-01-03"


def test_same_instant_gives_same_day_dirty_or_clean(tmp_path):
    br = _load()
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    f = repo / "index.html"
    f.write_text("x", encoding="utf-8")
    os.utime(f, (_KST_0103_0100, _KST_0103_0100))
    outside = br._source_lastmod(f)                    # 아직 추적 안 됨 = mtime 경로
    _commit(repo, "2026-01-03T01:00:00+09:00")
    assert br._source_lastmod(f) == outside == "2026-01-03"
