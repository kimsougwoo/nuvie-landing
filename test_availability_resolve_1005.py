# -*- coding: utf-8 -*-
"""Resolve availability alerts and distinguish refused pulls from rebase conflicts."""
import json
import os
import subprocess
from pathlib import Path

import build_availability as BA


ICS = "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
ENV = {
    "ICAL_URL_HOURPLACE": "booking-a",
    "ICAL_URL_HOURPLACE_B": "booking-b",
    "ICAL_URL_BLOCK_A": "block-a",
    "ICAL_URL_BLOCK_B": "block-b",
}


def _seed_availability_repo(path):
    path.mkdir()
    (path / "availability.json").write_text(
        json.dumps({"events": [], "busyDates": [], "note": BA.NOTE}), encoding="utf-8"
    )
    return path


def _run_main(monkeypatch, path, feed):
    env_file = path / ".test-env"
    env_file.write_text("test=true\n", encoding="utf-8")
    monkeypatch.setattr(BA, "ENV", str(env_file))
    monkeypatch.setattr(BA, "load_env", lambda *args, **kwargs: dict(ENV))
    monkeypatch.setattr(BA, "fetch", feed)
    monkeypatch.setattr(BA, "_update_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(BA, "push_changes", lambda repo, count: True)
    return BA.main(argv=["--push"], repo=str(path))


def _keys(records):
    return [key for key, _ in records]


def _git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=check, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )


def _identity(repo):
    _git(repo, "config", "user.name", "Availability test")
    _git(repo, "config", "user.email", "availability-test@example.invalid")


def _clone(remote, destination):
    subprocess.run(
        ["git", "clone", "-q", str(remote), str(destination)], check=True,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    _identity(destination)
    return destination


def _local_remote(tmp_path):
    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", "--initial-branch=main", str(remote)],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    _identity(remote)

    seed = tmp_path / "seed"
    seed.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=seed, check=True,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    _identity(seed)
    (seed / "availability.json").write_text('{"events": []}\n', encoding="utf-8")
    (seed / "index.html").write_bytes(b"<html>base</html>\n")
    _git(seed, "add", "availability.json", "index.html")
    _git(seed, "commit", "-q", "-m", "initial")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-q", "-u", "origin", "main")

    work = _clone(remote, tmp_path / "work")
    return remote, work


def _advance(remote, tmp_path, name, write):
    other = _clone(remote, tmp_path / name)
    write(other)
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "advance origin")
    _git(other, "push", "-q", "origin", "main")
    return other


def _rebase_dirs(repo):
    found = []
    for name in ("rebase-merge", "rebase-apply"):
        result = _git(repo, "rev-parse", "--git-path", name)
        path = result.stdout.strip()
        if not os.path.isabs(path):
            path = os.path.join(str(repo), path)
        if os.path.isdir(path):
            found.append(path)
    return found


def test_push_success_resolves_previous_push_failure(monkeypatch, tmp_path, availability_alerts,
                                                     availability_resolves):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(BA, "_landing_session_hold", lambda: None)

    def successful_run(args, **kwargs):
        stdout = "availability.json\n" if args[3:4] == ["diff"] else ""
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(BA.subprocess, "run", successful_run)
    assert BA.push_changes(str(repo), 3) is True
    assert "availability_push_failed" in _keys(availability_resolves)
    assert availability_alerts == []


def test_healthy_main_resolves_all_feed_alerts(monkeypatch, tmp_path, availability_alerts,
                                               availability_resolves):
    repo = _seed_availability_repo(tmp_path / "repo")
    assert _run_main(monkeypatch, repo, lambda url: ICS) is True
    assert availability_alerts == []
    assert set(_keys(availability_resolves)) == {
        "availability_fetch_down",
        "availability_config_missing",
        "availability_feed_failed",
        "availability_unreadable_events",
        "availability_previous_unreadable",
    }


def test_fired_feed_alert_is_not_resolved_in_same_run(monkeypatch, tmp_path, availability_alerts,
                                                       availability_resolves):
    repo = _seed_availability_repo(tmp_path / "repo")
    _run_main(monkeypatch, repo, lambda url: None if url == "booking-a" else ICS)
    assert "availability_feed_failed" in _keys(availability_alerts)
    assert "availability_feed_failed" not in _keys(availability_resolves)


def test_dirty_nonavailability_edit_refuses_pull_without_reset(monkeypatch, tmp_path,
                                                               availability_alerts):
    remote, repo = _local_remote(tmp_path)
    _advance(remote, tmp_path, "external", lambda other: (other / "other.txt").write_text(
        "origin advanced\n", encoding="utf-8"))
    dirty_html = b"<html>uncommitted local edit</html>\r\n"
    (repo / "index.html").write_bytes(dirty_html)
    (repo / "availability.json").write_text('{"events": ["local availability"]}\n', encoding="utf-8")
    monkeypatch.setattr(BA, "_landing_session_hold", lambda: None)

    assert BA.push_changes(str(repo), 1) is False
    messages = [msg for key, msg in availability_alerts if key == "availability_push_failed"]
    assert messages
    message = messages[-1]
    assert "충돌 아님" in message
    assert message.count("충돌") == 1
    assert "원격 최신본을 받지 못했습니다" in message and "미커밋" in message
    assert "커밋하거나 정리하면 다음 회차에 자동으로 반영" in message
    assert (repo / "index.html").read_bytes() == dirty_html
    assert "local availability" in _git(repo, "show", "HEAD:availability.json").stdout
    assert not _rebase_dirs(repo)


def test_real_nonavailability_rebase_conflict_aborts_and_holds(monkeypatch, tmp_path,
                                                              availability_alerts):
    remote, repo = _local_remote(tmp_path)
    _advance(remote, tmp_path, "external", lambda other: (other / "index.html").write_bytes(
        b"<html>origin edit</html>\n"))
    (repo / "index.html").write_bytes(b"<html>local committed edit</html>\n")
    _git(repo, "add", "index.html")
    _git(repo, "commit", "-q", "-m", "local index edit")
    (repo / "availability.json").write_text('{"events": ["local availability"]}\n', encoding="utf-8")
    monkeypatch.setattr(BA, "_landing_session_hold", lambda: None)

    assert BA.push_changes(str(repo), 1) is False
    messages = [msg for key, msg in availability_alerts if key == "availability_push_failed"]
    assert messages and "충돌" in messages[-1]
    assert "local committed edit" in _git(repo, "show", "HEAD:index.html").stdout
    assert "local availability" in _git(repo, "show", "HEAD:availability.json").stdout
    assert not _rebase_dirs(repo)


def test_availability_only_rebase_conflict_still_self_heals(monkeypatch, tmp_path,
                                                           availability_alerts):
    remote, repo = _local_remote(tmp_path)
    _advance(remote, tmp_path, "external", lambda other: (other / "availability.json").write_text(
        '{"events": ["origin availability"]}\n', encoding="utf-8"))
    (repo / "availability.json").write_text('{"events": ["local availability"]}\n', encoding="utf-8")
    monkeypatch.setattr(BA, "_landing_session_hold", lambda: None)

    assert BA.push_changes(str(repo), 1) is False
    assert availability_alerts == []
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == _git(
        repo, "rev-parse", "origin/main"
    ).stdout.strip()
    assert "origin availability" in (repo / "availability.json").read_text(encoding="utf-8")
    assert not _rebase_dirs(repo)


def test_pull_fetch_failure_is_classified_without_reset(monkeypatch, tmp_path, availability_alerts):
    _, repo = _local_remote(tmp_path)
    missing_remote = tmp_path / "missing-origin.git"
    _git(repo, "remote", "set-url", "origin", str(missing_remote))
    (repo / "availability.json").write_text('{"events": ["local availability"]}\n', encoding="utf-8")
    monkeypatch.setattr(BA, "_landing_session_hold", lambda: None)

    assert BA.push_changes(str(repo), 1) is False
    messages = [msg for key, msg in availability_alerts if key == "availability_push_failed"]
    assert messages and "원격 가져오기 단계 실패" in messages[-1]
    assert "local availability" in _git(repo, "show", "HEAD:availability.json").stdout
    assert not _rebase_dirs(repo)


def test_untracked_only_fetch_failure_is_not_blamed_on_edits(monkeypatch, tmp_path, availability_alerts):
    """미추적 파일은 git 이 rebase 를 거부하는 사유가 아니다 — 네트워크 실패를 «편집 탓»으로 적지 않는다."""
    _, repo = _local_remote(tmp_path)
    _git(repo, "remote", "set-url", "origin", str(tmp_path / "missing-origin.git"))
    (repo / "새로_쓰던_파일.md").write_text("draft\n", encoding="utf-8")
    (repo / "availability.json").write_text('{"events": ["local availability"]}\n', encoding="utf-8")
    monkeypatch.setattr(BA, "_landing_session_hold", lambda: None)

    assert BA.push_changes(str(repo), 1) is False
    messages = [msg for key, msg in availability_alerts if key == "availability_push_failed"]
    assert messages and "원격 가져오기 단계 실패" in messages[-1]
    assert "미커밋 편집" not in messages[-1]
    assert (repo / "새로_쓰던_파일.md").exists()


def test_rebase_directory_check_precedes_abort_in_push_source():
    source = Path(BA.__file__).read_text(encoding="utf-8")
    body = source[source.index("def push_changes("):]
    body = body[:body.index("\ndef ", 1)]
    check = body.index('"--git-path"')
    abort = body.index('"rebase", "--abort"')
    assert check < abort
