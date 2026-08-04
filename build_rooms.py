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
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = "https://www.nuviestudio.com"


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
            f'<p style="margin:0;color:var(--dim);font-size:15.5px;line-height:1.85">{b["body"]}</p>'
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
        # ✅ G4(초상권) 경계 — 대표 결정 2026-08-04: **후기 사진은 인물이 있어도 된다.**
        #    사유 = 게스트 본인이 자기 후기에 직접 올린 사진이라, 우리가 촬영·발행하는 콘텐츠와 층이 다르다.
        #    ⇒ 얼굴 블러(G4)는 **우리 촬영물**에 적용하고 게스트 후기 UGC 에는 적용하지 않는다.
        #    (종전 reviews.json 주석의 「인물 0명」은 사실이 아니었고 — rv_ragang.jpg 에 1명 —
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
            pg = (
                f'<div style="display:grid;grid-template-columns:repeat({len(photos)},1fr);'
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
    if room.get("showReviews") and reviews_doc.get("reviews"):
        product["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(reviews_doc.get("rating")),
            "reviewCount": str(reviews_doc.get("count", len(reviews_doc["reviews"]))),
            "bestRating": "5",
        }
        product["review"] = [
            {
                "@type": "Review",
                "author": {"@type": "Person", "name": r.get("name", "")},
                "datePublished": r.get("date", ""),
                "reviewRating": {
                    "@type": "Rating",
                    "ratingValue": str(r.get("rating", 5)),
                    "bestRating": "5",
                },
                "reviewBody": r.get("text", ""),
                "publisher": {"@type": "Organization", "name": "아워플레이스"},
            }
            for r in sorted(reviews_doc["reviews"], key=lambda x: x.get("date", ""), reverse=True)[:6]
        ]
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "누비 스튜디오", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": f"{room['label']} {room['name']}", "item": url},
        ],
    }
    out = json.dumps([product, breadcrumb], ensure_ascii=False, indent=2)
    # 카피에 "</script>" 가 들어오면 문서를 이탈한다. JSON 문자열 안에서 \/ 는 / 와 동치라 안전.
    return out.replace("</", "<\\/")


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
        "예약·결제는 아워플레이스에서 진행돼요. 1~4인 단독 대관이라 다른 팀과 겹치지 않아요."
        if catalog["fulfillment"]["mode"] == "external"
        else "예약·결제를 이 페이지에서 바로 진행하실 수 있어요."
    )
    hero = room["hero"]
    if len(hero["h1"]) != 2:
        raise SystemExit(f"[build_rooms] {room['slug']}: hero.h1 은 2줄이어야 한다")
    # h1 첫 줄 상한. 공백은 한글 글자보다 훨씬 좁으므로 폭 기준에서 제외한다
    # (라이브 정본 "남과 겹치지 않는" = 공백 2 + 글자 7 로 안 깨진다 — 공백까지 세면 이 값이 걸린다).
    glyphs = len(hero["h1"][0].replace(" ", ""))
    if glyphs > 8:
        raise SystemExit(
            f"[build_rooms] {room['slug']}: h1 첫 줄 '{hero['h1'][0]}' 이 {glyphs}글자다(상한 8) "
            "— 모바일 390px 에서 3줄로 깨진다"
        )

    repl = {
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


def build_sitemap(rooms: list[dict]) -> str:
    urls = [("/", "weekly", "1.0")]
    urls += [(f"/{r['slug']}", "weekly", "0.9") for r in rooms]
    # ⚠️ cleanUrls:true 라 /privacy.html 은 /privacy 로 308 된다 —
    #    사이트맵에 리다이렉트 URL 을 넣지 않는다(2026-08-04 검수 지적).
    urls += [("/privacy", "yearly", "0.3")]
    body = "\n".join(
        f"  <url><loc>{SITE}{loc}</loc><changefreq>{cf}</changefreq><priority>{pr}</priority></url>"
        for loc, cf, pr in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


# ---------------------------------------------------------------- main


def generate() -> dict[str, str]:
    spec = json.loads((ROOT / "rooms.json").read_text(encoding="utf-8"))
    template = (ROOT / "room.template.html").read_text(encoding="utf-8")
    reviews_doc = json.loads((ROOT / "reviews.json").read_text(encoding="utf-8"))

    catalog, rooms = spec["catalog"], spec["rooms"]

    # 후기 정본 가드 — reviews.json 은 place 하나에서 긁어온 것이라
    # 그 place 가 아닌 룸에 후기를 붙이면 거짓 사회적 증거가 된다.
    rp = reviews_doc.get("place_id")
    for r in rooms:
        if r.get("showReviews") and rp not in (None, r["external"]["placeId"]):
            raise SystemExit(
                f"[build_rooms] {r['slug']}: showReviews=true 인데 reviews.json place_id={rp} "
                f"가 이 룸({r['external']['placeId']})이 아니다"
            )

    out: dict[str, str] = {}
    for i, room in enumerate(rooms):
        other = rooms[(i + 1) % len(rooms)]
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
