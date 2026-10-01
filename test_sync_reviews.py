# -*- coding: utf-8 -*-
"""sync_reviews 후기 완전 자동화 회귀 (2026-08-25).

순수 변환만 검증한다(스크래이프·파일쓰기 제외 — 라이브 의존이라 여기서 안 건드림).
기계적 판정 기준:
  · 날짜 '2026.08.23' → '2026-08-23'
  · blind 후기는 제외 · 본문 없는 후기 제외
  · 이름은 마스킹(앞2+***) · 평점 int · 사진 URL 보존 · 최신순 정렬
  · 원문 스냅샷엔 이름 없음(feedback_id·본문만)
"""
import sync_reviews as S


def _room(reviews):
    return {"room": "B룸", "place_id": 62341, "reviews": reviews}


def test_iso_date():
    assert S._iso_date("2026.08.23") == "2026-08-23"
    assert S._iso_date("2026-08-23") == "2026-08-23"
    assert S._iso_date("") == ""


def test_room_doc_masks_excludes_and_sorts():
    room = _room([
        {"feedback_id": 1, "작성자": "paie", "평점": 5.0, "작성일": "2026.08.20",
         "후기": "좋아요", "사진": ["https://img.hourplace.co.kr/x/y/z"], "blind": False},
        {"feedback_id": 2, "작성자": "hidden", "평점": 5.0, "작성일": "2026.08.25",
         "후기": "숨김", "사진": [], "blind": True},          # blind → 제외
        {"feedback_id": 3, "작성자": "김", "평점": 4.0, "작성일": "2026.08.22",
         "후기": "", "사진": [], "blind": False},              # 본문 없음 → 제외
        {"feedback_id": 4, "작성자": "abcdef", "평점": 5.0, "작성일": "2026.08.24",
         "후기": "최신", "사진": [], "blind": False},
    ])
    doc = S._room_doc(room, "테스트")
    assert doc["count"] == 2                        # blind·빈본문 제외
    assert doc["reviews"][0]["date"] == "2026-08-24"  # 최신순
    assert doc["reviews"][0]["name"] == "ab***"       # 6자 → 앞2
    assert doc["reviews"][1]["name"] == "pa***"
    assert doc["reviews"][1]["photos"] == ["https://img.hourplace.co.kr/x/y/z"]
    assert all(isinstance(r["rating"], int) for r in doc["reviews"])
    assert doc["place_id"] == 62341


def test_empty_room_doc_count_zero():
    assert S._room_doc(_room([]), "테스트")["count"] == 0


def test_originals_have_no_names():
    room = _room([{"feedback_id": 9, "작성자": "someone", "평점": 5.0,
                   "작성일": "2026.08.23", "후기": "본문", "사진": [], "blind": False}])
    orig = S._originals([room])
    assert orig["reviews"][0]["feedback_id"] == 9
    assert "name" not in orig["reviews"][0] and "작성자" not in orig["reviews"][0]
    assert orig["reviews"][0]["text"] == "본문"


def test_all_doc_merges_rooms_and_aggregates_from_reviews():
    data = S._all_doc([
        {"reviews": [{"date": "2026-09-03", "rating": 5, "text": "A 후기"}]},
        {"reviews": [
            {"date": "2026-09-10", "rating": 4, "text": "B 최신 후기"},
            {"date": "2026-08-23", "rating": 5, "text": "B 이전 후기"},
        ]},
    ])

    assert data["source"] == "A+B 통합(메인 집계)"
    assert data["count"] == 3
    assert data["rating"] == 4.7
    assert data["updated"] == "2026-09-10"
    assert [review["text"] for review in data["reviews"]] == [
        "B 최신 후기", "A 후기", "B 이전 후기"
    ]


# ── 2026-09-29: 새 후기 사진 축소 사본 자동화 ────────────────────────────────────────────
#   축소 사본(build_review_images)이 체인에 없어 새 후기 사진은 원본(최대 25MB)으로 떴다.
#   체인 = build_review_images(실패해도 계속) → build_reviews(map.json 으로 정적 카드) → build_rooms.
import json as _json
import subprocess as _sp


def _fake_scrape(tmp_path):
    rev = {"feedback_id": 1, "작성자": "홍길동", "작성일": "2026.09.01", "평점": 5, "후기": "좋아요", "사진": [], "blind": False}
    # 2026-10-02: B룸 0건 가드(기존 후기가 있으면 0건 덮어쓰기 중단)가 생겨서, 체인 테스트는 B 에도 한 건을 둔다.
    data = {"ok": True, "rooms": [{"room": "A룸", "place_id": S.PLACE_A, "reviews": [rev]},
                                  {"room": "B룸", "place_id": S.PLACE_B, "reviews": [dict(rev, feedback_id=2)]}]}
    p = tmp_path / "scrape.json"
    p.write_text(_json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _record(monkeypatch):
    calls = []
    monkeypatch.setattr(S, "_dump", lambda *a, **k: None)   # 실제 후기 파일은 건드리지 않는다
    monkeypatch.setattr(S, "_run_build", lambda mod, fatal=True: calls.append((mod, fatal)))
    return calls


def test_build_chain_makes_review_images_first_and_non_fatal(tmp_path, monkeypatch):
    calls = _record(monkeypatch)
    assert S.main(["--from", _fake_scrape(tmp_path)]) == 0
    # 글꼴 서브셋은 HTML(build_reviews·build_rooms 결과)의 글자로 만들므로 맨 끝, 실패해도 계속(예비 = CDN 동적 서브셋)
    assert calls == [("build_review_images", False), ("build_reviews", True), ("build_rooms", True), ("build_fonts", False)]


def test_no_build_and_offline_skip_image_download(tmp_path, monkeypatch):
    calls = _record(monkeypatch)
    S.main(["--from", _fake_scrape(tmp_path), "--no-build"])
    assert calls == []
    monkeypatch.setattr(S, "_load_existing_docs", lambda: ({"reviews": [{"date": "2026-09-01", "rating": 5, "text": "a"}]}, {"reviews": []}))
    S.main(["--offline"])
    assert calls == [("build_reviews", True)], "오프라인은 내려받기(축소 사본) 없이 메인만 재빌드"


def test_non_fatal_build_failure_does_not_stop_chain(monkeypatch):
    monkeypatch.setattr(_sp, "run", lambda *a, **k: _sp.CompletedProcess(a, 1, stdout="", stderr="ModuleNotFoundError: PIL"))
    S._run_build("build_review_images", fatal=False)   # 경고만, 예외 없음
    import pytest
    with pytest.raises(SystemExit):
        S._run_build("build_reviews")
