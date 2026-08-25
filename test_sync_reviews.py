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
