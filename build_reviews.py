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


STATIC_START = "<!-- REVIEWS:STATIC:START -->"
STATIC_END = "<!-- REVIEWS:STATIC:END -->"
STATIC_N = 3          # 크롤러가 읽을 대표 후기 수(최신순). 늘리면 HTML 만 무거워진다.


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_static_reviews(data, n=STATIC_N):
    """크롤러용 정적 후기 카드 HTML 을 만든다(최신순 n건).

    왜 필요한가 — 후기 카드는 `fetch('reviews.json')` 으로 **브라우저에서만** 그려진다.
    GPTBot·ClaudeBot·PerplexityBot 등 상당수 AI 크롤러는 JS 를 실행하지 않으므로,
    우리가 가진 가장 설득력 있는 자산(실제 게스트 후기)이 그들에게는 **존재하지 않았다.**
    AEO 가 목표인데 근거 문장이 크롤러에게 없는 상태였다(2026-07-26).

    ⚠️ 사람이 손으로 박지 않는다 — `reviews.json` 이 바뀔 때마다 이 함수가 다시 만든다.
       손으로 박으면 정본이 또 하나 늘고, 그게 오늘 내내 고친 결함들의 원인이다.
    ⚠️ 마크업은 JS 카드와 같은 모양을 쓰되 사진은 넣지 않는다 — 크롤러가 읽는 건 텍스트이고,
       클릭 확대는 어차피 JS 가 붙여야 동작한다. JS 가 뜨면 이 블록은 통째로 교체된다.
    """
    rv = sorted((data or {}).get("reviews", []),
                key=lambda v: v.get("date") or "0000-00-00", reverse=True)[:n]
    card = ('background:var(--elev);border-radius:5px;padding:18px 20px;border:1px solid var(--line);'
            'break-inside:avoid;-webkit-column-break-inside:avoid;margin-bottom:14px')
    out = [STATIC_START]
    for v in rv:
        stars = "★★★★★"[:int(v.get("rating") or 5)]
        who = _esc(v.get("name", "")) + (f" · {_esc(v['date'])}" if v.get("date") else "")
        out.append(
            f'        <div role="listitem" style="{card}">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
            f'<span aria-hidden="true" style="color:var(--accent);font-size:13px">{stars}</span>'
            f'<span class="sr-only">5점 만점에 {int(v.get("rating") or 5)}점</span>'
            f'<span style="font-family:var(--label-font);font-size:12px;color:var(--dim)">{who}</span>'
            f'</div>'
            f'<p style="margin:0;font-size:13.5px;color:var(--ink);line-height:1.75;white-space:pre-line">'
            f'"{_esc(v.get("text", ""))}"</p></div>')
    out.append("        " + STATIC_END)
    return "\n".join(out)


def sync_static_reviews(html, data):
    """index.html 의 마커 사이를 정적 후기 카드로 갈아끼운다. 마커가 없으면 원본 유지."""
    i, j = html.find(STATIC_START), html.find(STATIC_END)
    if i == -1 or j == -1 or j < i:
        return html
    return html[:i] + render_static_reviews(data) + html[j + len(STATIC_END):]


ORIGINALS = os.path.join(HERE, "reviews_originals.json")

SENT_END = ("!", ".", "?", "~")


def mask_name(name):
    """후기 작성자 닉네임을 부분만 노출 (대표 지시 2026-08-05).

    규칙: 앞 2글자(1글자 이름은 1글자) + 고정 `***`.
      · 별표를 **고정 3개**로 두는 건 의도다 — 길이에 맞춰 늘리면 원래 닉네임 길이가 새어나간다.
      · 아워플레이스에 공개된 닉네임이긴 하지만, 우리 사이트가 이름과 후기를 한 줄로 묶어
        재게시하는 표면이라 노출을 줄인다.
    ⚠️ 이 레포는 **공개(public)** 다 — reviews.json 이 그대로 GitHub 에 노출된다.
       그래서 마스킹을 «렌더 시점»이 아니라 **저장 시점(SSOT)** 에 건다. 렌더러가 하나라도
       마스킹을 빠뜨리면 새기 때문이다.
    """
    n = (name or "").strip()
    if not n:
        return n
    keep = 1 if len(n) <= 2 else 2
    return n[:keep] + "***"


def _flat(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def verify_verbatim(data, originals):
    """reviews.json 의 인용이 원문에서 벗어나지 않았는지 판정. 위반 목록을 돌려준다.

    🔴 2026-08-05 신설 — 이 검사가 없어서 **개작·스플라이스 6건이 라이브에 떠 있었다**:
       · "빠방하구" → "빵빵하고" (게스트 말투 개작)
       · 원문 문장을 요약·어미 변경해 다시 씀
       · **스플라이스** — 원문 앞·뒤를 붙여 한 문장처럼 보이게 하고 그 사이 불만 2건을 흔적 없이 삭제
       작성자 닉네임과 함께 공개되는 글이라 «내가 이렇게 안 썼는데»가 되는 상태였다.

    판정 2조건:
      ① 원문의 **연속 부분문자열**인가 (말줄임 «…» 로 표시된 잘림은 허용)
      ② 발췌 시작점이 **문장 경계**인가 (원문 시작이거나 직전이 . ! ? ~)
    """
    srcs = [(o.get("name", ""), _flat(o.get("text", ""))) for o in originals.get("reviews") or []]
    bad = []
    for r in data.get("reviews") or []:
        q = _flat(r.get("text", "")).rstrip("…").strip()
        if not q:
            continue
        hit = None
        for name, src in srcs:
            if q in src:
                hit = (name, src, src.index(q))
                break
        if hit is None:
            bad.append((r.get("name", "?"), "원문에 없음(개작·이어붙임)", q[:48]))
            continue
        _, src, i = hit
        if i > 0 and not src[:i].rstrip().endswith(SENT_END):
            bad.append((r.get("name", "?"), "문장 중간에서 시작", q[:48]))
    return bad


def jsonld_snippet(text, limit=80):
    """JSON-LD reviewBody 용 짧은 인용. **연속 구간만**, 자르면 «…» 를 붙인다.

    ⚠️ 이 함수가 생긴 이유(2026-08-05): reviewBody 가 손으로 적혀 있어 원문과 어긋나 있었다 —
       "기존 동양풍 스튜디오**와 다르게**"(원문: "**와는 또 다른** 분위기를"). JSON-LD 는 구글
       리치결과로 나가는 **외부 표면**이라, 개작된 인용이 우리 이름으로 검색결과에 실린다.
       ⇒ 손으로 적지 말고 reviews.json(SSOT)에서 파생시킨다.
    """
    one = re.sub(r"\s+", " ", (text or "")).strip().rstrip("…").strip()
    if len(one) <= limit:
        return one
    head = one[:limit]
    sp = head.rfind(" ")
    return (head[:sp] if sp > 20 else head).strip() + "…"


def _jsonld_esc(s):
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def sync_jsonld_reviews(html, data):
    """JSON-LD 의 `"review":[...]` 배열을 reviews.json 에서 통째로 파생한다.

    ⚠️ 종전엔 «작성자 이름으로 매칭해 본문만» 갈아끼웠는데, 닉네임 마스킹(2026-08-05)이 들어가면서
       매칭 키 자체가 바뀌어 그 방식이 성립하지 않는다. 이름·본문 둘 다 SSOT 에서 나오게 재작성한다.
    ⚠️ 손으로 적힌 값이 남지 않게 배열을 **전량 재생성**한다 — 실제로 여기 개작이 있었다
       ("기존 동양풍 스튜디오**와 다르게**" / 원문은 "**와는 또 다른** 분위기를").
    개수는 기존 배열의 항목 수를 유지한다(리치결과 노출 범위를 임의로 늘리지 않는다).
    """
    m = re.search(r'"review":\[', html)
    if not m:
        return html
    # 대괄호 균형으로 배열 끝을 찾는다(정규식으로는 중첩 객체를 못 센다)
    start = m.end() - 1
    depth, end = 0, None
    for i in range(start, len(html)):
        c = html[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return html
    old = html[start:end]
    keep = old.count('"@type":"Review"') or 4

    items = []
    for r in (data.get("reviews") or [])[:keep]:
        obj = {
            "@type": "Review",
            "author": {"@type": "Person", "name": r.get("name", "")},
            "reviewRating": {"@type": "Rating",
                             "ratingValue": str(int(float(r.get("rating", 5)))),
                             "bestRating": "5"},
            "reviewBody": jsonld_snippet(r.get("text", "")),
            "publisher": {"@type": "Organization", "name": "아워플레이스"},
        }
        items.append(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    return html[:start] + "[" + ",".join(items) + "]" + html[end:]


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

    new_html = sync_jsonld_reviews(sync_static_reviews(sync_index_html(html, count, rating), data), data)
    new_llms = sync_llms_text(llms, count, rating)
    new_raw = sync_reviews_json_text(raw, count, rating)
    drift = (new_html != html) or (new_llms != llms) or (new_raw != raw)

    # verbatim 검사 — 원문 스냅샷이 있을 때만(없으면 조용히 건너뛰지 말고 알린다)
    violations = None
    if os.path.exists(ORIGINALS):
        with open(ORIGINALS, encoding="utf-8") as f:
            violations = verify_verbatim(data, json.load(f))
        for name, why, q in violations:
            print(f"[reviews][VERBATIM] {name}: {why} — {q}")
    else:
        print(f"[reviews][WARN] 원문 스냅샷 없음 → verbatim 검사 건너뜀: {ORIGINALS}")

    if check_only:
        if violations:
            return 1
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
