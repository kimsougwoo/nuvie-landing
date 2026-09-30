"""룸 페이지 생성기 — rooms.json(값) + room.template.html(틀) -> a.html · b.html · rooms.data.js · sitemap.xml

    python build_rooms.py            # 생성
    python build_rooms.py --check    # 생성물이 최신인지만 검사(쓰지 않음, CI/테스트용)

⚠️ a.html·b.html·rooms.data.js 를 직접 고치지 말 것 — 다음 빌드에서 덮어쓴다.
   값은 rooms.json, 틀은 room.template.html.

🔜 PortOne V2 자사몰 전환:
   rooms.json 의 catalog.fulfillment.mode 를 'own' 으로 바꾸고 다시 빌드하면
   예약 CTA 가 /book/<slug> 로 넘어간다(site.js 의 NUVIE.bookingUrl 한 곳에서 갈린다).
   가격·최소시간·정원은 이미 결제 모듈이 그대로 먹을 수 있는 형태로 rooms.json 에 있다.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = "https://www.nuviestudio.com"
BUSINESS_ID = f"{SITE}/#business"


def esc(s: str) -> str:
    """속성/텍스트 공용 이스케이프. 카피에 이미 <br> 이 들어있는 필드에는 쓰지 않는다."""
    return html.escape(str(s), quote=True)


def won(n: int) -> str:
    return f"{n:,}원"


def booking_href(room: dict, catalog: dict) -> str:
    """예약 CTA 의 href 를 빌드 시점에 채운다.

    ⚠️ 하드코딩이 아니다 — 목적지는 rooms.json(catalog.fulfillment.mode + external.placeId)에서만 나온다.
    site.js 가 로드되면 같은 값으로 다시 덮어쓴다. 굳이 두 번 하는 이유:
    rooms.data.js 404·캐시 스큐·JS 차단이면 site.js 의 `if(!ROOMS[slug]) return;` 에 걸려
    예약 경로가 통째로 죽는데, 그게 무증상이라 아무도 모른다(2026-08-04 검수 지적).
    HTML 에 실제 목적지가 박혀 있으면 JS 가 죽어도 예약은 된다.
    """
    if catalog["fulfillment"]["mode"] == "own":
        return f"/book/{room['slug']}"
    return f"https://www.hourplace.co.kr/place/{room['external']['placeId']}"


# ---------------------------------------------------------------- 조각 렌더


PRETENDARD_CDN = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css"
# 🧊 11/11 까지 동결된 룸 — 글꼴 head 를 옛 두 줄 그대로(b.html 바이트 동일). 동결이 풀리면 이 집합에서 뺀다.
FONT_HEAD_FROZEN = {"b"}
# 미리 받을 굵기 — 번갈아 실측으로 정한다(4종 모두는 첫 방문 FCP·LCP +0.4~0.9초). index.html head 도 같은 값으로 맞춘다.
FONT_PRELOAD = ()   # 09-30 번갈아 실측: 미리 불러오기 없음이 FCP·CLS·느린 4G LCP 모두 가장 좋음(400·700 은 FCP +0.3~0.5초)


def font_head(slug: str) -> str:
    """룸 페이지 head 의 글꼴 줄(2026-09-29).

    새 방식(09-30 대표 결정 «optional») = 사이트 글자 서브셋 NuvieSans(fonts.css, font-display: optional) + FONT_PRELOAD 굵기만
      preload. CDN Pretendard 는 싣지 않는다 — 남기면 NuvieSans 를 못 쓴 페이지가 결국 Pretendard(swap)로 바뀌며 다시 밀린다.
    동결 룸 = 종전 두 줄(preconnect + 렌더를 막는 CDN CSS) 그대로.
    """
    if slug in FONT_HEAD_FROZEN:
        return ('<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>\n'
                f'<link rel="stylesheet" href="{PRETENDARD_CDN}">')
    lines = [f'<link rel="preload" href="/fonts/nuvie-sans-{w}.woff2" as="font" type="font/woff2" crossorigin>'
             for w in FONT_PRELOAD]
    lines.append('<link rel="stylesheet" href="/fonts.css">')
    return "\n".join(lines)


def render_info_cells(room: dict) -> str:
    """히어로 아래 4칸 지표. 값은 rooms.json 에서만 온다."""
    p, cap = room["pricing"], room["capacity"]
    # ⚠️ 「기준 인원」은 4다(5인째부터 추가요금). 종전 「1–4 / 기본 인원」은 수용범위를
    #    기준인원처럼 보이게 해 요금 조건을 흐렸다 — 2026-08-04 검수 지적.
    cells = [
        (str(p["minHours"]), "H", "최소 대관"),
        (str(p["baseGuests"]), "인", "기준 인원"),
        (f'{p["weekday"] // 10000}', "만원~", "시간당"),
        ("10", "분", "까치산역 도보"),
    ]
    out = []
    for i, (big, unit, label) in enumerate(cells):
        border = "" if i == len(cells) - 1 else "border-right:1px solid var(--line)"
        out.append(
            f'<div class="it" style="padding:34px 30px;{border}">'
            f'<div style="font-family:var(--label-font);font-weight:700;font-size:clamp(32px,3.6vw,50px);'
            f'line-height:1;letter-spacing:-.02em;color:var(--ink)">{esc(big)}'
            f'<span style="font-size:.5em;color:var(--accent);margin-left:2px">{esc(unit)}</span></div>'
            f'<div style="font-family:var(--label-font);font-size:11px;letter-spacing:.16em;'
            f'text-transform:uppercase;color:var(--dim);margin-top:10px">{esc(label)}</div></div>'
        )
    return "".join(out)


def render_season_note(room: dict) -> str:
    """시즌 안내(2026-09-30 U-01) — rooms.json seasonNote {text, until}. 없으면 빈 문자열(b.html 바이트 불변).
    until(KST 날짜)부터 스스로 숨는다 — 홈 룸 카드 #seasonNoteA 와 같은 방식·같은 문장."""
    sn = room.get("seasonNote")
    if not sn:
        return ""
    style = "margin:14px 0 0;color:#FFFFFF;font-size:14.5px;font-weight:600;line-height:1.6"
    js = ("(function(){var n=document.getElementById('seasonNote');if(!n)return;"
          "var today=new Date(Date.now()+9*3600*1000).toISOString().slice(0,10);if(today<n.dataset.until)n.hidden=false;})();")
    # 대표 09-30 «기간 줄바꿈 처리»: « · » 자리에서 줄을 바꿔 기간(«10월 31일까지»)을 둘째 줄에
    parts = [esc(part) for part in sn["text"].split(" · ")]
    # 대표 09-30 «강조표시»(A룸 상세 = 두 줄 모두): 굵고 조금 크게 — 새 색은 들이지 않는다. 홈 A룸 카드도 두 줄 모두.
    body = '<strong style="font-weight:700;font-size:16.5px">' + "<br>".join(parts) + "</strong>"
    return (f'<p id="seasonNote" data-until="{esc(sn["until"])}" hidden style="{style}">{body}</p>'
            f'<script>{js}</script>')


def render_hero_tags(room: dict) -> str:
    # ⚠️ 히어로는 테마와 무관하게 항상 어두운 사진 위다 → 테마 토큰을 쓰면 라이트에서 글자가 사라진다.
    #    고정 라이트 값으로 못박는다(2026-08-04 Stayfolio 전환 시 실제로 밟은 함정).
    style = (
        "font-family:var(--label-font);font-size:11.5px;letter-spacing:.06em;color:#EDEDEF;"
        "border:1px solid rgba(255,255,255,.28);padding:5px 12px;border-radius:999px;"
        "white-space:nowrap;text-decoration:none"
    )
    return "".join(
        f'<a href="#about" style="{style}">{esc(t)}</a>' for t in room["tags"]
    )


def render_blocks(room: dict) -> str:
    """소개 본문. head 는 액센트 강조, body 는 rooms.json 카피 그대로."""
    out = []
    for b in room["blocks"]:
        out.append(
            '<div data-reveal style="max-width:60ch;margin:0 0 26px">'
            f'<div style="font-family:var(--label-font);font-size:12px;letter-spacing:.16em;'
            f'text-transform:uppercase;color:var(--accentSoft);margin-bottom:8px">{esc(b["head"])}</div>'
            f'<p style="margin:0;color:var(--dim);font-size:15.5px;line-height:1.85;text-wrap:pretty">{b["body"]}</p>'
            "</div>"
        )
    return "\n      ".join(out)


def render_gallery(room: dict) -> str:
    cardstyle = (
        "aspect-ratio:3/4;overflow:hidden;border-radius:6px;border:1px solid var(--line);"
        "position:relative;background:linear-gradient(135deg,var(--elev),var(--panel))"
    )
    imgstyle = (
        "position:absolute;inset:0;width:100%;height:100%;object-fit:cover;"
        "transition:transform .6s cubic-bezier(.22,.61,.36,1)"
    )
    out = []
    for g in room["gallery"]:
        out.append(
            f'<div style="{cardstyle}"><img data-fallback="1" data-zoom loading="lazy" '
            f'decoding="async" src="{esc(g["src"])}" alt="{esc(g["alt"])}" style="{imgstyle}"></div>'
        )
    return "".join(out)


def render_reviews(room: dict, reviews_doc: dict) -> str:
    """A룸 후기 — 빌드 시점 정적 렌더(상품 페이지 SEO 목적. JS 렌더는 색인에 안 잡힌다)."""
    if not room.get("showReviews"):
        return ""
    items = reviews_doc.get("reviews", [])
    if not items:
        return ""
    items = sorted(items, key=lambda r: r.get("date", ""), reverse=True)
    label = room["label"]
    cards = []
    for r in items:
        rating = int(r.get("rating", 5))
        stars = "★" * rating

        # 후기 사진 — 게스트가 아워플레이스에 올린 컷 중 수기 큐레이션된 것.
        # ⚠️ 허브(index.html)는 이걸 렌더하는데 룸 페이지만 빠져 있었다(2026-08-04 대표 지적).
        # ✅ 대표 결정 2026-08-04: **후기 사진은 인물이 있어도 된다.**
        #    사유 = 게스트 본인이 자기 후기에 직접 올린 사진이라, 우리가 촬영·발행하는 콘텐츠와 층이 다르다.
        #    ⇒ 게스트 후기 UGC 는 우리 촬영물과 별개로 그대로 게시한다.
        #    (종전 reviews.json 주석의 「인물 0명」은 사실이 아니었고 — rv_20260723_1.jpg 에 1명 —
        #     그래서 이 규칙이 필요했다. 다시 「인물 있으니 빼자」로 되돌리지 말 것.)
        # 확대는 라이트박스 JS 대신 <a target="_blank"> 로 연다 — 키보드 접근이 기본으로 되고 JS 의존이 없다.
        photos = [p for p in (r.get("photos") or []) if p][:2]
        pg = ""
        if photos:
            cells = "".join(
                f'<a href="{esc(src)}" target="_blank" rel="noopener" '
                f'aria-label="후기 사진 크게 보기" style="display:block;min-width:0">'
                f'<img loading="lazy" decoding="async" src="{esc(src)}" '
                f'alt="{esc(label)} 후기 사진" '
                'style="width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:4px;display:block"></a>'
                for src in photos
            )
            # 항상 2열 고정 — 사진 1장짜리 후기가 전체폭으로 커지면 2장짜리 카드와
            # 나란히 스크롤될 때 사진 크기가 들쭉날쭉해 보인다(2026-08-07 대표 지적).
            pg = (
                f'<div style="display:grid;grid-template-columns:repeat(2,1fr);'
                f'gap:6px;margin:0 0 11px">{cells}</div>'
            )

        # white-space:pre-line — 게스트 원문의 줄바꿈을 살린다(허브와 동일).
        # 기본값이면 여러 줄 후기가 한 덩어리로 접혀 읽기 나빠진다(2026-07-24 대표 지적).
        # verbatim 인용 규칙과도 정합 — 원문을 원문대로 보인다.
        cards.append(
            '<div style="border:1px solid var(--line);min-width:0;'
            'border-radius:6px;padding:18px 18px 16px;background:var(--panel)">'
            f'<div style="color:var(--accent);font-size:12px;letter-spacing:.1em" aria-hidden="true">{stars}</div>'
            f'<span class="sr-only">5점 만점에 {rating}점</span>'
            f"{pg}"
            f'<p style="margin:9px 0 12px;color:var(--ink);font-size:14px;line-height:1.75;'
            f'white-space:pre-line">{esc(r.get("text", ""))}</p>'
            f'<div style="color:var(--faint);font-size:11.5px">{esc(r.get("name", ""))} · {esc(r.get("date", ""))}</div>'
            "</div>"
        )
    rating = reviews_doc.get("rating")
    count = reviews_doc.get("count", len(items))
    # ⚠️ .sec/.inner 를 쓰지 않는다 — 2단 그리드(.roomgrid-main) 안에 들어가므로
    #    그리드가 이미 폭·여백을 잡는다(붙이면 패딩이 이중으로 걸린다).
    return f"""<section id="reviews">
      <div class="sechead" data-reveal>
        <span class="snum">03</span>
        <div><div class="skick">Reviews</div><h2 style="margin:0;font-size:clamp(26px,3vw,40px);letter-spacing:-.02em">후기</h2></div>
      </div>
      <p class="desc" data-reveal style="margin:0 0 30px">아워플레이스에 남겨주신 후기예요 · 평점 {esc(rating)} / 5 · {esc(count)}건</p>
      <!-- ⚠️ column-width(멀티컬럼)를 쓰지 않는다 — 이 사이트에서 핀치줌 가로넘침 버그의
           근본원인으로 특정돼 데스크탑 전용으로 격리된 기법이다(styles.css #reviewCards 주석).
           auto-fill 그리드는 같은 매이슨리 느낌을 내면서 그 버그 계열을 통째로 피하고 JS 도 필요 없다. -->
      <div data-reveal style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;align-items:start">{''.join(cards)}</div>
    </section>"""


def render_jsonld(room: dict, other: dict, catalog: dict, reviews_doc: dict) -> str:
    p = room["pricing"]
    url = f"{SITE}/{room['slug']}"
    # 평일가만 price 로 내보내면 주말 이용자에게 과소 표시가 된다 → AggregateOffer(low/high).
    # 최소 이용시간은 referenceQuantity(=단가의 기준 수량 1시간)가 아니라 eligibleQuantity 로 분리한다
    # (value:1 과 minValue:2 를 한 객체에 같이 두면 의미가 충돌한다 — 2026-08-04 검수 지적).
    def unit_price(amount: int) -> dict:
        return {
            "@type": "UnitPriceSpecification",
            "price": amount,
            "priceCurrency": p["currency"],
            "valueAddedTaxIncluded": p["taxIncluded"],
            "unitCode": "HUR",
            "referenceQuantity": {"@type": "QuantitativeValue", "value": 1, "unitCode": "HUR"},
            "eligibleQuantity": {
                "@type": "QuantitativeValue",
                "minValue": p["minHours"],
                "unitCode": "HUR",
            },
        }

    offer = {
        "@type": "AggregateOffer",
        "url": url,
        "seller": {"@id": BUSINESS_ID},
        "lowPrice": p["weekday"],
        "highPrice": p["weekend"],
        "priceCurrency": p["currency"],
        "offerCount": 2,
        "availability": "https://schema.org/InStock",
        "priceSpecification": [unit_price(p["weekday"]), unit_price(p["weekend"])],
    }
    product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"{room['label']} — {room['name']} · 누비 스튜디오",
        "sku": room["sku"],
        "description": room["seo"]["description"],
        "url": url,
        "image": [SITE + g["src"] for g in room["gallery"][:4]],
        "brand": {"@type": "Brand", "name": "누비 스튜디오 NUVIE STUDIO"},
        "category": "코스프레 스튜디오 대관",
        "offers": offer,
    }
    if reviews_doc.get("updated"):
        product["dateModified"] = reviews_doc["updated"]
    # 2026-09-28: aggregateRating·review[] 를 내보내지 않는다. 후기는 전부 아워플레이스 것이라
    #   구글 리뷰 스니펫 규칙 «Don't aggregate reviews or ratings from other websites» 위반이다.
    #   화면의 후기 목록(render_reviews, 출처 표기)은 그대로 둔다. 테스트 = test_jsonld_no_thirdparty_reviews.py
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "누비 스튜디오", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": f"{room['label']} {room['name']}", "item": url},
        ],
    }
    # 노드마다 <script> 한 개(= @context 를 가진 객체 한 개). [Product, Breadcrumb] 배열 한 블록은
    # Safari 쪽 주입 스크립트가 r["@context"].toLowerCase() 로 읽다 TypeError 를 냈다
    # (Clarity 2026-09, /a Safari 2세션). index.html 도 이미 객체-블록 두 개 방식이다.
    blocks = []
    for node in (product, breadcrumb):
        # 카피에 "</script>" 가 들어오면 문서를 이탈한다. JSON 문자열 안에서 \/ 는 / 와 동치라 안전.
        body = json.dumps(node, ensure_ascii=False, indent=2).replace("</", "<\\/")
        blocks.append(f'<script type="application/ld+json">\n{body}\n</script>')
    return "\n".join(blocks)


# ---------------------------------------------------------------- 페이지 조립


def build_page(room: dict, other: dict, catalog: dict, reviews_doc: dict, template: str) -> str:
    p = room["pricing"]
    price_line = (
        f'평일 <b style="font-weight:700">{won(p["weekday"])}</b> / '
        f'주말 <b style="font-weight:700">{won(p["weekend"])}</b> · 시간당 · '
        f'최소 {p["minHours"]}시간 · {p["baseGuests"]}인 기준 · '
        f'{"부가세 포함" if p["taxIncluded"] else "부가세 별도"}'
    )
    # 추가요금 고지 — 룸 페이지엔 FAQ 가 없어 조건이 통째로 빠져 있었다(2026-08-04 검수).
    # CTA 를 태우는 페이지에서 조건을 숨기면 기대 불일치 = 보이스 1층(정직) 위반이다.
    price_conditions = (
        f'{p["baseGuests"] + 1}인째부터 시간당 {won(p["extraGuestPerHour"])}이 자동 추가돼요 · '
        f'일부 조명 액세서리는 개당 {won(p["accessoryFeePerItem"])}(대관 1회당, 이용 시간과 무관) · '
        f'주말은 {p["weekendDefinition"]} 기준 · 실제 결제 금액은 예약 페이지에서 확인하실 수 있어요.'
    )
    # ⚠️ 룸 간 가격 비교 금지(대표 2026-07-26): 이 페이지엔 이 룸 값만 적는다.
    #    다른 룸 카드(OTHER_*)에 가격을 넣지 않는 것도 같은 이유다.
    booking_note = (
        "예약·결제는 아워플레이스에서 진행돼요. 예약한 룸은 그 팀만 단독으로 사용해요."
        if catalog["fulfillment"]["mode"] == "external"
        else "예약·결제를 이 페이지에서 바로 진행하실 수 있어요."
    )
    hero = room["hero"]
    if len(hero["h1"]) != 2:
        raise SystemExit(f"[build_rooms] {room['slug']}: hero.h1 은 2줄이어야 한다")
    # h1 첫 줄 상한. 공백은 한글 글자보다 훨씬 좁으므로 폭 기준에서 제외한다
    # (현행 허브 h1 첫 줄 "내 의도대로 찍는" = 공백 2 + 글자 7 로 안 깨진다 — 공백까지 세면 이 값이 걸린다).
    glyphs = len(hero["h1"][0].replace(" ", ""))
    if glyphs > 8:
        raise SystemExit(
            f"[build_rooms] {room['slug']}: h1 첫 줄 '{hero['h1'][0]}' 이 {glyphs}글자다(상한 8) "
            "— 모바일 390px 에서 3줄로 깨진다"
        )

    repl = {
        "FONT_HEAD": font_head(room["slug"]),
        "TITLE": esc(room["seo"]["title"]),
        "DESC": esc(room["seo"]["description"]),
        "OG_TITLE": esc(f'{room["label"]} {room["name"]} — 누비 스튜디오'),
        "OG_IMAGE": SITE + room["seo"]["ogImage"],
        "CANONICAL": f"{SITE}/{room['slug']}",
        "JSONLD": render_jsonld(room, other, catalog, reviews_doc),
        "SLUG": room["slug"],
        "LABEL": esc(room["label"]),
        "NAME": esc(room["name"]),
        "KICKER": esc(hero["kicker"]),
        "H1_1": esc(hero["h1"][0]),
        "H1_2": esc(hero["h1"][1]),
        "SUB": hero["sub"],  # <br> 허용 필드
        "SEASON_NOTE": render_season_note(room),
        "HERO_IMG": esc(hero["image"]),
        "HERO_ALT": esc(hero["alt"]),
        "HERO_TAGS": render_hero_tags(room),
        "INFO_CELLS": render_info_cells(room),
        "BLOCKS": render_blocks(room),
        "GALLERY": render_gallery(room),
        "REVIEWS": render_reviews(room, reviews_doc),
        "PRICE_LINE": price_line,
        "PRICE_CONDITIONS": price_conditions,
        "BOOKING_HREF": booking_href(room, catalog),
        "BOOKING_NOTE": booking_note,
        "OTHER_LABEL": esc(other["label"]),
        "OTHER_NAME": esc(other["name"]),
        "OTHER_SLUG": other["slug"],
    }
    out = template
    for k, v in repl.items():
        out = out.replace("{{" + k + "}}", str(v))
    if "{{" in out:
        leftover = out[out.index("{{") : out.index("{{") + 40]
        raise SystemExit(f"[build_rooms] 치환 안 된 자리표시자: {leftover}")
    return out


def build_rooms_data(rooms: list[dict], catalog: dict) -> str:
    data = {
        r["slug"]: {
            "slug": r["slug"],
            "label": r["label"],
            "name": r["name"],
            "placeId": r["external"]["placeId"],
            "availabilityKey": r["availabilityKey"],
            "pricing": r["pricing"],
            "capacity": r["capacity"],
            "status": r["status"],
        }
        for r in rooms
    }
    return (
        "/* 생성 파일 — 고치지 말 것. 값은 rooms.json, 생성은 build_rooms.py */\n"
        "window.NUVIE = window.NUVIE || {};\n"
        f"window.NUVIE.rooms = {json.dumps(data, ensure_ascii=False, indent=2)};\n"
        f"window.NUVIE.fulfillment = {json.dumps(catalog['fulfillment'], ensure_ascii=False, indent=2)};\n"
    )


def _source_lastmod(*paths: Path) -> str:
    """소스 파일의 최신 mtime을 sitemap용 ISO 날짜로 변환한다.

    build_rooms.generate()는 테스트에서 임시 ROOT를 사용하기도 하므로, 존재하는
    소스만 취한다. 실제 저장소에서는 index.html/rooms.json/템플릿이 모두 존재한다.
    """
    existing = [path for path in paths if path.exists()]
    if not existing:
        raise FileNotFoundError("sitemap lastmod source is missing")
    # 2026-09-27: 커밋된 채 안 바뀐 파일은 git 마지막 커밋 날짜 — mtime 은 체크아웃마다 달라
    #   `--check` 가 워크트리에선 통과·본체에선 실패했다. 수정 중이거나 git 밖이면 mtime(종전 방식).
    return max(_file_lastmod(path) for path in existing)


# 날짜는 한 시간대(KST)로만 센다. 종전엔 커밋 날짜(%cs = 커밋한 사람 시간대)와 mtime(UTC)이 달라
# KST 00:00~08:59 에 고친 파일은 수정 중엔 하루 전, 커밋하면 하루 뒤 날짜가 됐다(2026-09-28).
_LASTMOD_TZ = timezone(timedelta(hours=9))


def _file_lastmod(path: Path) -> str:
    import subprocess
    try:
        cwd = str(path.parent)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", path.name], cwd=cwd,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        if dirty.returncode == 0 and not dirty.stdout.strip():
            log = subprocess.run(["git", "log", "-1", "--format=%ct", "--", path.name], cwd=cwd,
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
            stamp = log.stdout.strip()
            if log.returncode == 0 and stamp.isdigit():
                return datetime.fromtimestamp(int(stamp), tz=_LASTMOD_TZ).date().isoformat()
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=_LASTMOD_TZ).date().isoformat()


def build_sitemap(rooms: list[dict]) -> str:
    root_lastmod = _source_lastmod(ROOT / "index.html", ROOT / "rooms.json")
    room_lastmod = _source_lastmod(
        ROOT / "rooms.json", ROOT / "room.template.html", ROOT / "build_rooms.py"
    )
    urls = [("/", "weekly", "1.0", root_lastmod)]
    urls += [(f"/{r['slug']}", "weekly", "0.9", room_lastmod) for r in rooms]
    body = "\n".join(
        f"  <url><loc>{SITE}{loc}</loc><lastmod>{lastmod}</lastmod>"
        f"<changefreq>{cf}</changefreq><priority>{pr}</priority></url>"
        for loc, cf, pr, lastmod in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


# ---------------------------------------------------------------- main


def _load_reviews_by_place() -> dict[int, dict]:
    """룸별 후기 문서를 place_id 로 색인한다. reviews.json=A룸(61823)·reviews_b.json=B룸(62341).
    2026-08-25: 종전엔 단일 reviews.json 이라 B룸 후기 표면이 없었다 → 룸별 파일로 분리(완전 자동 = sync_reviews.py)."""
    by_place: dict[int, dict] = {}
    for fname in ("reviews.json", "reviews_b.json"):
        path = ROOT / fname
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        pid = doc.get("place_id")
        if pid is not None:
            by_place[int(pid)] = doc
    return by_place


def generate() -> dict[str, str]:
    spec = json.loads((ROOT / "rooms.json").read_text(encoding="utf-8"))
    template = (ROOT / "room.template.html").read_text(encoding="utf-8")
    reviews_by_place = _load_reviews_by_place()

    catalog, rooms = spec["catalog"], spec["rooms"]

    # 후기 정본 가드 — 룸엔 «그 룸 place 의» 후기만 붙인다(다른 place 후기 = 거짓 사회적 증거).
    for r in rooms:
        if r.get("showReviews") and int(r["external"]["placeId"]) not in reviews_by_place:
            raise SystemExit(
                f"[build_rooms] {r['slug']}: showReviews=true 인데 place {r['external']['placeId']} "
                f"후기 문서(reviews*.json)가 없다"
            )

    out: dict[str, str] = {}
    for i, room in enumerate(rooms):
        other = rooms[(i + 1) % len(rooms)]
        reviews_doc = reviews_by_place.get(int(room["external"]["placeId"]), {"reviews": []})
        out[f"{room['slug']}.html"] = build_page(room, other, catalog, reviews_doc, template)
    out["rooms.data.js"] = build_rooms_data(rooms, catalog)
    out["sitemap.xml"] = build_sitemap(rooms)
    return out


def main(argv: list[str]) -> int:
    check = "--check" in argv
    files = generate()
    stale = []
    for name, content in files.items():
        path = ROOT / name
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        if check:
            stale.append(name)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"  wrote {name} ({len(content):,} chars)")
    if check:
        if stale:
            print("생성물이 최신이 아니다: " + ", ".join(stale))
            print("→ python build_rooms.py 를 실행하고 커밋할 것")
            return 1
        # ⚠️ 콘솔이 cp949 라 비ASCII 기호(✓·이모지)는 UnicodeEncodeError 를 낸다 — 쓰지 말 것.
        print("생성물 최신 OK")
        return 0
    # ⚠️ cp949 콘솔에서 em-dash·✓ 등 비ASCII 기호는 UnicodeEncodeError 를 낸다. 출력은 ASCII 로.
    print(f"완료 {len(files)}개 파일")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
