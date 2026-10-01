# -*- coding: utf-8 -*-
"""후기 조용한 대체 제거 — 2026-10-02 폴백 점검 «우선순위 1» 9~11(총괄 결정 문서).

  9. B룸 스크레이프가 0건이면 후기 파일을 0건으로 덮어쓴다(A룸에만 보호) → B 도 같은 보호 + 알림(A 보호도 알림).
 10. 평점 없는 후기를 5점으로 채워 평균·검색 구조화 데이터에 넣는다 → 사실과 다른 숫자라 채우지 않는다
     (평균에서 빼고 건수만 센다. 별·«5점 만점에 N점»·JSON-LD reviewRating 은 평점이 있을 때만).
 11. 사진 축소 실패 시 24.8MB 원본을 쓴다 → 원본으로 대신하지 않고 그 사진을 빼고 알린다.
⚠️ 실 스크래이프·네트워크·디스코드 금지(전부 monkeypatch).
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_reviews as BR  # noqa: E402
import sync_reviews as S  # noqa: E402

ROOT = Path(__file__).parent


def _rev(fid, rating, text="좋아요", date="2026.09.20", photos=None):
    r = {"feedback_id": fid, "작성자": "abcdef", "작성일": date, "후기": text, "사진": photos or [], "blind": False}
    if rating is not None:
        r["평점"] = rating
    return r


# 10 ────────────────────────────────────────────────────────────
def test_missing_rating_is_not_filled_with_five():
    doc = S._room_doc({"place_id": 1, "reviews": [_rev(1, 4.0), _rev(2, None)]}, "t")
    assert doc["count"] == 2
    ratings = [r["rating"] for r in doc["reviews"]]
    assert None in ratings and 5 not in ratings
    assert doc["rating"] == 4.0, "평균은 평점이 있는 후기로만"


def test_room_with_no_ratings_has_no_average():
    doc = S._room_doc({"place_id": 1, "reviews": [_rev(1, None)]}, "t")
    assert doc["count"] == 1 and doc["rating"] is None


def test_all_doc_average_skips_missing():
    a = S._room_doc({"place_id": 1, "reviews": [_rev(1, 4.0)]}, "a")
    b = S._room_doc({"place_id": 2, "reviews": [_rev(2, None)]}, "b")
    all_doc = S._all_doc([a, b])
    assert all_doc["count"] == 2 and all_doc["rating"] == 4.0


def test_originals_keep_missing_rating_as_none():
    out = S._originals([{"reviews": [_rev(1, None)]}])
    rows = out["reviews"] if isinstance(out, dict) and "reviews" in out else out
    first = rows[0] if isinstance(rows, list) else list(rows.values())[0]
    assert first["rating"] is None


def test_load_facts_average_skips_missing():
    count, rating = BR.load_facts({"reviews": [{"rating": 4}, {"rating": None}, {"rating": 5}]})
    assert count == 3 and rating == "4.5"


def test_static_card_shows_no_stars_without_rating():
    html = BR.render_static_reviews({"reviews": [{"name": "ab***", "date": "2026-09-20", "rating": None,
                                                  "text": "좋아요", "photos": []}]}, n=1, img_map={})
    assert "★" not in html and "5점 만점에" not in html


def test_static_card_still_shows_stars_with_rating():
    html = BR.render_static_reviews({"reviews": [{"name": "ab***", "date": "2026-09-20", "rating": 4,
                                                  "text": "좋아요", "photos": []}]}, n=1, img_map={})
    assert "★★★★<" in html and "5점 만점에 4점" in html


def test_jsonld_omits_review_rating_without_rating():
    html = 'A"review":[{"@type":"Review","reviewBody":"x"}]B'
    src = (ROOT / "build_reviews.py").read_text(encoding="utf-8")
    assert 'r.get("rating", 5)' not in src and "r.get('rating', 5)" not in src, "JSON-LD 에 평점 5 기본값"


def test_hub_js_does_not_default_rating_to_five():
    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    seg = hub[hub.index("var sum=0;"):hub.index("host.innerHTML='';")]
    assert "||5" not in seg.replace(" ", ""), "평균 계산에서 평점 없는 후기를 5점으로 센다"
    card = hub[hub.index("rv.forEach(function(v){"):hub.index("h.appendChild(st);")]
    assert "(v.rating||5)" not in card.replace(" ", ""), "카드 별·스크린리더 문구가 평점 없는 후기를 5점으로 보인다"


# 9 ─────────────────────────────────────────────────────────────
def _scrape(a_reviews, b_reviews):
    return {"ok": True, "rooms": [{"place_id": S.PLACE_A, "reviews": a_reviews},
                                  {"place_id": S.PLACE_B, "reviews": b_reviews}]}


def _sandbox(monkeypatch, tmp_path, b_count_before):
    for name in ("reviews.json", "reviews_b.json", "reviews_originals.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / "reviews_b.json").write_text(json.dumps({"count": b_count_before, "reviews": [{}] * b_count_before}),
                                             encoding="utf-8")
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "REVIEWS_ALL", tmp_path / "reviews_all.json")
    alerts = []
    monkeypatch.setattr(S, "_alert", lambda key, msg: alerts.append((key, msg)))
    return alerts


def test_b_room_zero_with_previous_reviews_stops_and_alerts(monkeypatch, tmp_path):
    alerts = _sandbox(monkeypatch, tmp_path, b_count_before=3)
    path = tmp_path / "s.json"
    path.write_text(json.dumps(_scrape([_rev(1, 5.0)], []), ensure_ascii=False), encoding="utf-8")
    try:
        S.main(["--from", str(path), "--no-build"])
    except SystemExit:
        pass
    assert json.loads((tmp_path / "reviews_b.json").read_text(encoding="utf-8"))["count"] == 3, "B룸 후기를 0건으로 덮어썼다"
    assert any(k == "reviews_zero_guard" and "B룸" in m for k, m in alerts)


def test_a_room_zero_guard_also_alerts(monkeypatch, tmp_path):
    alerts = _sandbox(monkeypatch, tmp_path, b_count_before=3)
    path = tmp_path / "s.json"
    path.write_text(json.dumps(_scrape([], [_rev(2, 5.0)]), ensure_ascii=False), encoding="utf-8")
    try:
        S.main(["--from", str(path), "--no-build"])
    except SystemExit:
        pass
    assert any(k == "reviews_zero_guard" and "A룸" in m for k, m in alerts)


def test_b_room_zero_when_it_was_already_zero_is_fine(monkeypatch, tmp_path):
    alerts = _sandbox(monkeypatch, tmp_path, b_count_before=0)
    path = tmp_path / "s.json"
    path.write_text(json.dumps(_scrape([_rev(1, 5.0)], []), ensure_ascii=False), encoding="utf-8")
    assert S.main(["--from", str(path), "--no-build"]) == 0
    assert alerts == []


# 11 ────────────────────────────────────────────────────────────
def test_photo_without_resized_copy_is_left_out_of_static_card():
    html = BR._static_photo_grid(["https://img.hourplace.co.kr/a/b/huge.jpg"], {})
    assert "huge.jpg" not in html, "축소 사본이 없는 사진을 원본으로 대신 넣었다"


def test_hub_js_skips_photos_without_map_entry():
    hub = (ROOT / "index.html").read_text(encoding="utf-8")
    seg = hub[hub.index("v.photos.slice(0,2)"):hub.index("card.appendChild(pg);")]
    assert "||src" not in seg.replace(" ", ""), "map 에 없는 사진을 원본 src 로 대신 띄운다"


def test_image_build_failure_is_alerted_not_just_printed():
    src = (ROOT / "sync_reviews.py").read_text(encoding="utf-8")
    body = src[src.index("def _run_build("):]
    body = body[:body.index("\ndef ", 1)]
    assert "_alert(" in body


def test_sync_reviews_alert_goes_through_report():
    src = (ROOT / "sync_reviews.py").read_text(encoding="utf-8")
    body = src[src.index("def _alert("):]
    body = body[:body.index("\ndef ", 1)]
    assert "alert_throttled" in body
