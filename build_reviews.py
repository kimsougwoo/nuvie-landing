#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2 후기 전파 제너레이터 — reviews.json(SSOT) → index.html JSON-LD + 정적 스팬 + llms.txt.

문제(D2/G2): 후기가 reviews.json·JSON-LD·llms.txt 세 곳에 따로 적혀 "후기 5 vs 7" 드리프트 발생.
해결: reviews.json 하나만 수정 → 이 스크립트가 나머지 표면(count·rating)을 파생시켜 정합.
      사진은 reviews.json에 수기 큐레이션(G4 공간컷·인물0)한 그대로 — 이 스크립트는 count/rating만 전파(초상권 무관).

사용: python build_reviews.py [--check]
  기본  = reviews.json 읽어 index.html·llms.txt 갱신(멱등).
  --check = 갱신 없이 드리프트만 보고(비정합이면 exit 1). CI/surface_lint 훅용.
순수함수(sync_*)는 파일 I/O 없이 문자열만 변환 → 재현 테스트에서 그대로 검증.
"""
import sys, os, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEWS = os.path.join(HERE, "reviews.json")
INDEX = os.path.join(HERE, "index.html")
LLMS = os.path.join(HERE, "llms.txt")


def load_facts(reviews_json):
    """reviews.json dict → (count, rating_str). count=실제 리뷰 수(권위), rating=평균 1자리."""
    rv = reviews_json.get("reviews") or []
    count = len(rv)
    if rv:
        avg = sum(float(r.get("rating", 0)) for r in rv) / count
        rating = f"{round(avg, 1):.1f}"
    else:
        rating = f"{float(reviews_json.get('rating', 0)):.1f}"
    return count, rating


def sync_llms_text(text, count, rating):
    """llms.txt의 '후기 N개·평점 X★' 문구를 SSOT값으로. 문구 없으면 원본 유지."""
    return re.sub(r"후기\s*\d+\s*개·평점\s*[\d.]+★",
                  f"후기 {count}개·평점 {rating}★", text)


def sync_index_html(html, count, rating):
    """index.html의 aggregateRating(JSON-LD) + 정적 스팬(reviewCount/reviewTotal)을 SSOT값으로.
    ⚠️ 개별 review의 ratingValue는 건드리지 않는다(aggregateRating 객체만 타깃)."""
    # JSON-LD aggregateRating (ratingValue + reviewCount) — 이 객체만 정확히 매칭
    html = re.sub(
        r'("aggregateRating":\{"@type":"AggregateRating","ratingValue":")[\d.]+(","reviewCount":")\d+(")',
        lambda m: f'{m.group(1)}{rating}{m.group(2)}{count}{m.group(3)}',
        html)
    # 정적 폴백 스팬(JS가 덮어쓰나 no-JS·크롤러 대비 정합 유지)
    html = re.sub(r'(id="reviewCount">)\d+(</span>)', lambda m: f'{m.group(1)}{count}{m.group(2)}', html)
    html = re.sub(r'(id="reviewTotal">)\d+(</span>)', lambda m: f'{m.group(1)}{count}{m.group(2)}', html)
    # "전체 …건 ★5.0" 의 별점 표기
    html = re.sub(r'(reviewTotal">\d+</span>건 ★)[\d.]+', lambda m: f'{m.group(1)}{rating}', html)
    return html


def sync_reviews_json_text(text, count, rating):
    """reviews.json 원문의 최상위 count/rating 필드만 targeted 치환(수기 포맷·photos 배열 보존).
    ⚠️ 개별 review의 'rating': 5는 건드리지 않는다(최상위 필드만 — 앞 들여쓰기 2칸 기준)."""
    text = re.sub(r'(\n  "count":\s*)\d+', lambda m: f'{m.group(1)}{count}', text)
    text = re.sub(r'(\n  "rating":\s*)[\d.]+', lambda m: f'{m.group(1)}{float(rating)}', text)
    return text


def main(check_only=False):
    raw = open(REVIEWS, encoding="utf-8").read()
    data = json.loads(raw)
    count, rating = load_facts(data)
    html = open(INDEX, encoding="utf-8").read()
    llms = open(LLMS, encoding="utf-8").read()

    new_html = sync_index_html(html, count, rating)
    new_llms = sync_llms_text(llms, count, rating)
    new_raw = sync_reviews_json_text(raw, count, rating)
    drift = (new_html != html) or (new_llms != llms) or (new_raw != raw)

    if check_only:
        if drift:
            print(f"[reviews][DRIFT] SSOT count={count} rating={rating} — 표면 불일치 발견")
            if new_html != html: print("  · index.html 불일치")
            if new_llms != llms: print("  · llms.txt 불일치")
            if new_raw != raw: print("  · reviews.json count/rating 불일치")
            return 1
        print(f"[reviews][OK] 전 표면 정합 (count={count} rating={rating})")
        return 0

    if new_raw != raw: open(REVIEWS, "w", encoding="utf-8").write(new_raw)
    if new_html != html: open(INDEX, "w", encoding="utf-8").write(new_html)
    if new_llms != llms: open(LLMS, "w", encoding="utf-8").write(new_llms)
    print(f"[reviews] 전파 완료 → count={count} rating={rating} (index.html·llms.txt·reviews.json 정합)")
    return 0


if __name__ == "__main__":
    sys.exit(main(check_only="--check" in sys.argv))
