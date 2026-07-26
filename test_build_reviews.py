#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G2 후기 전파 재현·정합 테스트. 순수함수만 검증(파일 I/O 없음)."""
import json, os
import build_reviews as B

HERE = os.path.dirname(os.path.abspath(__file__))


def test_reproduce_llms_drift():
    """재현: llms에 '후기 5개'인데 SSOT는 7 → 전파가 7로 고쳐야 한다(이 세션의 실제 드리프트)."""
    stale = "- A룸은 아워플레이스 후기 5개·평점 5.0★."
    fixed = B.sync_llms_text(stale, 7, "5.0")
    assert "후기 7개·평점 5.0★" in fixed
    assert "후기 5개" not in fixed


def test_llms_rating_change():
    stale = "후기 3개·평점 4.5★"
    assert B.sync_llms_text(stale, 10, "4.8") == "후기 10개·평점 4.8★"


def test_index_aggregate_only():
    """aggregateRating의 reviewCount·ratingValue만 바뀌고 개별 review의 ratingValue는 불변."""
    html = ('X"aggregateRating":{"@type":"AggregateRating","ratingValue":"4.0","reviewCount":"3","bestRating":"5"}'
            'Y"reviewRating":{"@type":"Rating","ratingValue":"5","bestRating":"5"}Z')
    out = B.sync_index_html(html, 9, "5.0")
    assert '"ratingValue":"5.0","reviewCount":"9"' in out          # aggregate 갱신됨
    assert '"reviewRating":{"@type":"Rating","ratingValue":"5"' in out  # 개별 review 불변


def test_index_static_spans():
    html = '<span id="reviewCount">3</span> … 전체 <span id="reviewTotal">3</span>건 ★4.0'
    out = B.sync_index_html(html, 7, "5.0")
    assert 'id="reviewCount">7</span>' in out
    assert 'id="reviewTotal">7</span>건 ★5.0' in out


def test_load_facts_counts_actual_reviews():
    data = {"count": 999, "rating": 1.0, "reviews": [{"rating": 5}, {"rating": 5}, {"rating": 4}]}
    count, rating = B.load_facts(data)
    assert count == 3
    assert rating == "4.7"   # (5+5+4)/3 = 4.666… → 4.7


def test_real_reviews_json_all_surfaces_consistent():
    """실제 파일: build_reviews.py 실행 후 세 표면이 reviews.json과 정합해야(멱등 idempotent check)."""
    data = json.load(open(os.path.join(HERE, "reviews.json"), encoding="utf-8"))
    count, rating = B.load_facts(data)
    html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
    llms = open(os.path.join(HERE, "llms.txt"), encoding="utf-8").read()
    # sync 후 변화가 없어야 정합(=이미 전파됨). 이 테스트가 실패하면 build_reviews.py 재실행 필요.
    assert B.sync_index_html(html, count, rating) == html, "index.html 미정합 — build_reviews.py 실행 필요"
    assert B.sync_llms_text(llms, count, rating) == llms, "llms.txt 미정합 — build_reviews.py 실행 필요"


def test_every_review_rating_is_a_number_not_a_string():
    """🔥 2026-07-26 라이브 사고의 재현 — 히어로 배지에 **6944444.4** 가 찍혔다.

    원인은 JS 타입 강제 변환이다. `reviews.json` 의 후기 8건 중 **한 건만** rating 이
    숫자 5 가 아니라 문자열 "5" 였는데, `sum += v.rating` 이 문자열을 만나는 순간
    덧셈이 **이어붙이기**로 바뀐다:  0 + "5" → "05" → "055" → … → "05555555"
    그리고 "05555555" / 8 = 6944444.375 → toFixed(1) = 6944444.4.

    파이썬 쪽(`load_facts`)은 `float()` 로 감싸서 멀쩡했기 때문에 **빌드 스크립트도,
    표면 정합 테스트도 전부 통과했다** — 깨진 건 브라우저에서만 보이는 JS 경로뿐이었다.
    그래서 데이터 타입 자체를 여기서 못박는다.
    """
    data = json.load(open(os.path.join(HERE, "reviews.json"), encoding="utf-8"))
    bad = [(i, r.get("rating")) for i, r in enumerate(data.get("reviews", []))
           if not isinstance(r.get("rating"), (int, float)) or isinstance(r.get("rating"), bool)]
    assert not bad, (
        f"rating 이 숫자가 아닌 후기: {bad} — JS 에서 문자열 덧셈이 되어 평점이 폭주한다"
        " (2026-07-26 히어로 배지 6944444.4 사고)")


def test_hero_badge_js_coerces_rating_to_number():
    """데이터를 고치는 것만으로는 **또 들어온다** — 소비하는 코드도 방어해야 한다.

    후기는 사람이 손으로 큐레이션하므로(`build_reviews.py` 주석 참조) 언제든 따옴표가
    다시 붙을 수 있다. 클래스를 고친다 = 합산 시점에 숫자로 강제한다.
    """
    html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
    assert "sum+=(Number(v.rating)||5)" in html.replace(" ", ""), (
        "히어로 평점 합산이 v.rating 을 숫자로 강제하지 않는다 — "
        "문자열 rating 하나가 다시 들어오면 평점이 또 폭주한다")


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL {fn.__name__}: {e}")
    print(f"== {len(fns)-failed}/{len(fns)} passed ==")
    sys.exit(1 if failed else 0)
