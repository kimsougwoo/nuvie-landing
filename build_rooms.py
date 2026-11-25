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
from ko_glue import glue_html, _glue_inner

import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = "https://www.nuviestudio.com"
BUSINESS_ID = f"{SITE}/#business"


def esc(s: str) -> str:
    """속성/텍스트 공용 이스케이프. 카피에 이미 <br> 이 들어있는 필드에는 쓰지 않는다."""
    return html.escape(str(s), quote=True)


def format_business_phone(tel: str) -> str:
    """화면 표기용 전화번호. 원본은 rooms.json business.tel 이며 임의 번호는 두지 않는다."""
    digits = re.sub(r"\D", "", tel)
    if len(digits) != 11:
        raise SystemExit("[build_rooms] business.tel 은 11자리 국내 번호여야 한다")
    return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"


def render_footer_lines(room: dict, phone_display: str) -> str:
    """B룸의 기존 인라인 푸터는 유지하고, 여러 줄 푸터는 줄바꿈으로 잇는다."""
    lines = room["footerLines"]
    if not isinstance(lines, list) or not lines:
        raise SystemExit(f"[build_rooms] {room['slug']}: footerLines 는 비어 있지 않은 배열이어야 한다")
    lines = [line.replace("{business.tel}", phone_display) for line in lines]
    rendered = "<br>".join(esc(line) for line in lines)
    return (" / " if len(lines) == 1 else "<br>") + rendered


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
FONT_HEAD_FROZEN = set()   # 10/1 /b 1안(대표): B룸도 자체 호스팅 글꼴
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


def hero_srcset(image):
    """히어로 사진에 800w 변형(img/<이름>-800.jpg)이 있으면 (img 의 srcset 속성, head 의 preload 줄)을 돌려준다.
    10-01 SEO 점검: 홈은 srcset+preload 인데 /a·/b 는 모바일에서도 1600w 원본(/b 248KB)을 받았다. 사진은 그대로, 파일만 작게.
    변형이 없으면 둘 다 빈 문자열(예전 그대로)."""
    if not image.endswith('.jpg'):
        return '', ''
    small = image[:-4] + '-800.jpg'
    if not (ROOT / small.lstrip('/')).exists():
        return '', ''
    mid = image[:-4] + '-1200.jpg'   # 10-01: 360×DPR3·390×DPR3 폰은 1080~1170px 이 필요해 800w 를 건너뛰고 1600w 원본을 받았다
    rungs = [f'{small} 800w'] + ([f'{mid} 1200w'] if (ROOT / mid.lstrip('/')).exists() else []) + [f'{image} 1600w']
    srcset = ', '.join(rungs)
    return (f' srcset="{esc(srcset)}" sizes="100vw"',
            f'<link rel="preload" as="image" href="{esc(image)}" imagesrcset="{esc(srcset)}" imagesizes="100vw" fetchpriority="high">')


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


def render_setups(room: dict, today: str | None = None, no: str = "03") -> str:
    """꾸며 놓았던 세팅 기록(2026-10-01 대표 «블랙호리존 꾸며놓았던 사진들 따로 섹션» · «매일 조금씩 디테일이 달라질 순 있습니다 표기»).
    rooms.json setups 가 없으면 빈 문자열(b.html 바이트 불변). 시즌 라벨은 until(KST 날짜) 전 = «지금», 그날부터 = «지난».
    빌드 날짜로 한 번 정하고(스크립트 없는 수집기용), 페이지 안 스크립트가 방문 날짜로 다시 맞춘다(10/31 에 빌드한 페이지도 11/1 엔 «지난»)."""
    st = room.get("setups")
    if not st:
        return ""
    # 11-22: 시즌 라벨은 선택. season 이 없으면 «지난»/«지금» 문구와 스크립트를 넣지 않는다(상시 세팅 기록).
    season = st.get("season")
    past = False
    if season:
        today = today or datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
        past = today >= season["until"]
    cardstyle = (
        "aspect-ratio:{ar};overflow:hidden;border-radius:6px;border:1px solid var(--line);"
        "position:relative;background:linear-gradient(135deg,var(--elev),var(--panel))"
    )
    imgstyle = "position:absolute;inset:0;width:100%;height:100%;object-fit:cover"
    # 10-01 대표 «일자는 빼주세요» → 사진마다 붙이던 촬영일 표기·alt 속 날짜를 뺐다(운영 기간 라벨은 위 season 이 맡는다)
    def _card(it, ar_override=None, extra="", sizes="(max-width: 760px) 82vw, 560px"):
        src = it["src"]
        p400 = src[:-4] + "-400.jpg"
        p800 = src[:-4] + "-800.jpg"
        fw = it.get("w") or 825
        ar = ar_override or (f'{it["w"]}/{it["h"]}' if it.get("w") and it.get("h") else "3/4")
        srcset = f"{esc(p400)} 400w, {esc(p800)} 800w, {esc(src)} {fw}w"
        return (
            f'<div style="{extra}{cardstyle.format(ar=ar)}"><img data-fallback="1" data-zoom loading="lazy" decoding="async" '
            f'src="{esc(src)}" srcset="{srcset}" sizes="{sizes}" '
            f'alt="{esc(it["alt"])}" style="{imgstyle}"></div>'
        )
    # 11-24: 크롭 없이(원본 비율) 한 줄 안에서 폭을 비율대로 나눠 높이를 맞춘다(필름스트립).
    #   flex-grow = 가로/세로 비율 → 모든 칸 높이가 같아지고 이미지는 잘리지 않는다.
    #   sizes 는 줄의 칸 수에 맞춰 추정 → 모바일에선 400w 를 골라 용량을 줄인다.
    def _row(items, margin="0 0 14px"):
        n = len(items)
        if n >= 3:
            sizes = "(max-width: 760px) 31vw, 335px"
        elif n == 2:
            sizes = "(max-width: 760px) 46vw, 503px"
        else:
            sizes = "(max-width: 900px) 100vw, 900px"
        parts = []
        for it in items:
            a = (it["w"] / it["h"]) if it.get("w") and it.get("h") else 0.75
            parts.append(_card(it, extra=f"flex:{a:.4f} 1 0;min-width:0;", sizes=sizes))
        return (f'<div class="setup-row" data-reveal style="display:flex;gap:10px;align-items:flex-start;{margin}">'
                + "".join(parts) + '</div>')
    hero = st.get("hero") or []
    trio = st.get("trio") or []
    items2 = st.get("items") or []
    hero_html = _row(hero) if hero else ""
    trio_html = _row(trio) if trio else ""
    grid_html = "".join(_row(items2[i:i + 2]) for i in range(0, len(items2), 2)) if items2 else ""
    js = ("(function(){var s=document.getElementById('setupSeason');if(!s)return;"
          "var today=new Date(Date.now()+9*3600*1000).toISOString().slice(0,10);var past=today>=s.dataset.until;"
          "s.querySelector('[data-now]').hidden=past;s.querySelector('[data-past]').hidden=!past;})();")
    season_html = ""
    if season:
        season_html = (
            f'<p id="setupSeason" data-until="{esc(season["until"])}" data-reveal style="margin:0 0 8px;color:var(--ink);font-size:15px;font-weight:600">'
            f'<span data-now{" hidden" if past else ""}>{esc(season["now"])}</span>'
            f'<span data-past{"" if past else " hidden"}>{esc(season["past"])}</span></p>'
        )
    else:
        js = ""
    script_html = f"<script>{js}</script>" if js else ""
    free = (st.get("free") or "").strip()
    free_html = ""
    if free:
        free_html = (
            f'<div data-reveal style="margin:0 0 26px;padding:16px 18px;border:1px solid var(--line);'
            f'border-radius:6px;background:var(--panel)">'
            f'<p style="margin:0;color:var(--ink);font-size:14.5px;line-height:1.8">'
            f'{esc(free).replace(chr(10), "<br>")}</p></div>'
        )
    return f"""<section id="setups">
          <div class="sechead" data-reveal>
            <span class="snum">{esc(no)}</span>
            <div>{kick(room, "Setups")}<h2 style="margin:0;font-size:clamp(26px,3vw,40px);letter-spacing:-.02em">{esc(st["title"])}</h2></div>
          </div>
          {season_html}
          <p class="desc" data-reveal style="margin:0 0 16px">{esc(st["intro"])}<br>{esc(st["note"])}</p>
          {free_html}
          {hero_html}
          {trio_html}
          {grid_html}
          {script_html}
        </section>"""


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


def render_faq_links(room):
    """U-09(2026-09-30): 룸 페이지 예약 카드 아래 홈 FAQ 바로가기. faqLinks 가 없는 룸은 빈 문자열(= 기존 HTML 그대로)."""
    links = room.get("faqLinks") or []
    if not links:
        return ""
    items = "".join(
        f'<a class="btn line" href="{esc(href)}" style="min-height:44px;padding:8px 14px;font-size:13px">{esc(label)}</a>'
        for label, href in links
    )
    return ('<div class="faqlinks" style="margin-top:18px;padding-top:16px;border-top:1px solid var(--line)">'
            '<div style="color:var(--dim);font-size:12.5px;margin-bottom:10px">자주 묻는 질문</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:8px">{items}</div></div>')


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
    # 11-22: 방 사진은 원본 비율 유지(강제 3:4 크롭 제거). w/h 가 있으면 그 비율로, 없으면 기존 3/4.
    cardstyle = (
        "aspect-ratio:{ar};overflow:hidden;border-radius:6px;border:1px solid var(--line);"
        "position:relative;background:linear-gradient(135deg,var(--elev),var(--panel))"
    )
    imgstyle = (
        "position:absolute;inset:0;width:100%;height:100%;object-fit:cover;"
        "transition:transform .6s cubic-bezier(.22,.61,.36,1)"
    )
    out = []
    # 10-01: caption 이 있는 항목만 사진 아래쪽에 짧은 설명(활용 예시임을 밝힌다 — 대표 «이렇게 세팅할수 있는거에요»). 없으면 예전과 같은 마크업.
    capstyle = ("position:absolute;left:0;right:0;bottom:0;padding:26px 12px 10px;font-size:12.5px;line-height:1.5;color:#FFFFFF;"
                "background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.66));pointer-events:none")
    for g in room["gallery"]:
        ar = f'{g["w"]}/{g["h"]}' if g.get("w") and g.get("h") else "3/4"
        cs = cardstyle.format(ar=ar)
        if g.get("video"):
            # 10-01: 영상 칸. poster·src 를 HTML 에 두지 않는다(poster 는 위치와 상관없이 바로 받아져 LCP 대역을 먹는다).
            #   site.js wireGalVideo 가 갤러리 근처에서 채우고 화면 안에서만 재생한다. <img> 를 두지 않아 /b 동결 픽스처(갤러리 사진 목록)가 그대로다.
            out.append(
                f'<div class="galvid" style="{cs}"><video muted loop playsinline preload="none" '
                f'data-src="{esc(g["video"])}" data-poster="{esc(g["poster"])}" aria-label="{esc(g["alt"])}" style="{imgstyle}"></video>'
                f'<button type="button" class="galvid-btn" aria-label="영상 일시정지" hidden></button></div>'
            )
            continue
        cap = f'<span style="{capstyle}">{esc(g["caption"])}</span>' if g.get("caption") else ""
        out.append(
            f'<div style="{cs}"><img data-fallback="1" data-zoom loading="lazy" '
            f'decoding="async" src="{esc(g["src"])}" alt="{esc(g["alt"])}" style="{imgstyle}">{cap}</div>'
        )
    return "".join(out)


_REVIEW_MAP = None


def review_thumb(src: str) -> str:
    """후기 사진 원본 주소 → 축소본(reviews/img/map.json 의 thumb). 매핑이 없으면 원본 그대로."""
    global _REVIEW_MAP
    if _REVIEW_MAP is None:
        p = ROOT / "reviews" / "img" / "map.json"
        _REVIEW_MAP = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    ent = _REVIEW_MAP.get(src) or {}
    return ent.get("thumb") or src


def render_reviews(room: dict, reviews_doc: dict, no: str | None = None) -> str:
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
            # 2026-09-30: 축소본(reviews/img/map.json thumb)이 있으면 처음부터 그걸 쓴다 — /b 는 원본(최대 약 24MB)을 받고 있었다.
            #   href 는 원본 그대로(라이트박스가 href 로 축소 확대본을 찾고, JS 가 없으면 새 탭 원본).
            cells = "".join(
                f'<a href="{esc(src)}" target="_blank" rel="noopener" '
                f'aria-label="후기 사진 크게 보기" style="display:block;min-width:0">'
                f'<img loading="lazy" decoding="async" src="{esc(review_thumb(src))}" '
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
    q = room.get("reviewQuote")
    quote_html = ""
    if q:
        quote_html = (
            '<figure data-reveal style="margin:0 0 26px;padding:22px 24px;border:1px solid var(--line);border-radius:6px;background:var(--panel)">'
            '<div style="font-family:var(--label-font);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:10px">실제 손님 한마디</div>'
            f'<blockquote style="margin:0;color:var(--ink);font-size:16.5px;line-height:1.8;white-space:pre-line">“{esc(q.get("text", ""))}”</blockquote>'
            f'<figcaption style="margin-top:12px;color:var(--faint);font-size:12px">{esc(q.get("name", ""))} · {esc(q.get("date", ""))}</figcaption>'
            '</figure>'
        )
    # ⚠️ .sec/.inner 를 쓰지 않는다 — 2단 그리드(.roomgrid-main) 안에 들어가므로
    #    그리드가 이미 폭·여백을 잡는다(붙이면 패딩이 이중으로 걸린다).
    return f"""<section id="reviews">
      <div class="sechead" data-reveal>
        <span class="snum">{esc(no or ("04" if room.get("setups") else "03"))}</span>
        <div>{kick(room, "Reviews")}<h2 style="margin:0;font-size:clamp(26px,3vw,40px);letter-spacing:-.02em">후기</h2></div>
      </div>
      <p class="desc" data-reveal style="margin:0 0 30px">아워플레이스에 남겨주신 후기예요 · 평점 {esc(rating)} / 5 · {esc(count)}건</p>
      {quote_html}
      <!-- ⚠️ column-width(멀티컬럼)를 쓰지 않는다 — 이 사이트에서 핀치줌 가로넘침 버그의
           근본원인으로 특정돼 데스크탑 전용으로 격리된 기법이다(styles.css #reviewCards 주석).
           auto-fill 그리드는 같은 매이슨리 느낌을 내면서 그 버그 계열을 통째로 피하고 JS 도 필요 없다. -->
      <div class="room-reviews" data-reveal style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;align-items:start">{''.join(cards)}</div>
    </section>"""


def kick(room: dict, label: str) -> str:
    """11-22 대표: /a 는 kicker 제거(hideKickers), /b 는 11/11 동결 계약으로 원본 유지."""
    return "" if room.get("hideKickers") else f'<div class="skick">{label}</div>'


def render_prep(room: dict, no: str = "04") -> str:
    """촬영 준비 — 현장에서 바로 확인할 것(천·레일·조명·신발·자연광). 가격·장비 목록은 사이드바와 중복하지 않는다."""
    pr = room.get("prep") or {}
    items = pr.get("items") or []
    if not items:
        return ""
    cells = "".join(
        f'<div style="padding:18px 0;border-top:1px solid var(--line)">'
        f'<div style="font-family:var(--label-font);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accentSoft);margin-bottom:6px">{esc(it["head"])}</div>'
        f'<p style="margin:0;color:var(--dim);font-size:14.5px;line-height:1.8">{esc(it["body"])}</p></div>'
        for it in items
    )
    return f"""<section id="prep">
          <div class="sechead" data-reveal>
            <span class="snum">{esc(no)}</span>
            <div>{kick(room, "Prepare")}<h2 style="margin:0;font-size:clamp(26px,3vw,40px);letter-spacing:-.02em">{esc(pr.get("title") or "촬영 준비")}</h2></div>
          </div>
          <p class="desc" data-reveal style="margin:0 0 10px">{esc(pr.get("note") or "")}</p>
          <div class="prepgrid" data-reveal>{cells}</div>
        </section>"""


def render_notice(room: dict, no: str = "06") -> str:
    """이용 전 확인 — 입실·층/주차·취소. 가격·인원은 예약 카드가 이미 말한다."""
    nt = room.get("notice") or {}
    items = nt.get("items") or []
    if not items:
        return ""
    rows = "".join(
        f'<div class="noticerow"><div class="noticehead">{esc(it["head"])}</div>'
        f'<p>{esc(it["body"]).replace(chr(10), "<br>")}</p></div>'
        for it in items
    )
    return f"""<section id="notice">
          <div class="sechead" data-reveal>
            <span class="snum">{esc(no)}</span>
            <div>{kick(room, "Before you book")}<h2 style="margin:0;font-size:clamp(26px,3vw,40px);letter-spacing:-.02em">{esc(nt.get("title") or "이용 전 확인")}</h2></div>
          </div>
          <div data-reveal>{rows}</div>
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
        "seller": {"@type": "Organization", "@id": BUSINESS_ID, "name": "누비 스튜디오 NUVIE STUDIO", "url": "https://www.nuviestudio.com/"},
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
        "image": [SITE + g["src"] for g in room["gallery"] if not g.get("video")][:4],
        "brand": {"@type": "Brand", "name": "누비 스튜디오 NUVIE STUDIO"},
        "category": "코스프레 스튜디오 대관",
        "offers": offer,
    }
    if room.get("blackCyc"):
        product["additionalProperty"] = [
            {"@type": "PropertyValue", "name": "블랙 호리존(BLACK CYC) 크기", "value": room["blackCyc"]}
        ]
    if room.get("jsonldProps"):
        product["additionalProperty"] = [
            {"@type": "PropertyValue", "name": p["name"], "value": p["value"]} for p in room["jsonldProps"]
        ]
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



def render_props_teaser(room: dict) -> str:
    """A/B 상세 안 «비치 소품 전체 인라인» — 2026-11-25 대표(D안) · 내부작업 검수 반영.

    조건: ①상세에는 사진 0장(히어로 제외) ②원단은 1줄(이미지 4장 넣지 않음)
          ③렌더 스킵(content-visibility) ④링크 2곳(위·아래) + «무엇이 있는지» 문구
    값은 props.json 하나만 쓴다. 사진은 /props#<slug> 에서만.
    """
    import json as _json
    path = ROOT / "props.json"
    if not path.exists():
        return ""
    doc = _json.loads(path.read_text(encoding="utf-8"))
    slug = room["slug"]
    # 유료 장비는 아래 «유료 장비» 줄에서 금액과 함께 한 번만 적는다(칩 중복 금지).
    paid_rows = doc.get("paid", {}).get(slug, [])
    eq = []
    eq_paid = 0
    for x in doc.get("equipment", {}).get(slug, []):
        if x.get("tag") == "유료":
            eq_paid += 1
            continue
        label = x["name"] + (" · " + x["sub"] if x.get("sub") else "")
        eq.append(label)
    rm = next((r for r in doc.get("rooms", []) if r["slug"] == slug), {"items": []})
    items = [x["name"] + (" · " + x["sub"] if x.get("sub") else "") for x in rm["items"]]
    total = len(eq) + len(items) + eq_paid
    extra = " · 원단 14색" if slug == "a" else ""
    link_label = "사진으로 전체 보기 (" + room["label"] + " " + str(total) + "종" + extra + ")"

    def chips(names):
        return "".join(
            '<li style="background:var(--panel);border:1px solid var(--line);border-radius:2px;'
            'padding:10px 12px;font-size:13px;color:var(--dim);line-height:1.55">' + esc(n) + "</li>"
            for n in names)

    link = ('<a class="btn line" style="padding:11px 20px;font-size:13.5px;white-space:nowrap" href="/props#' + slug + '">'
            + esc(link_label) + " &rarr;</a>")
    paid_line = ""
    if paid_rows:
        parts = " · ".join('%s %s' % (r["name"].split(" + ")[0], r["price"]) for r in paid_rows)
        paid_line = ('<p style="margin:0 0 14px;font-size:13px;color:var(--dim)">'
                     '<b style="color:var(--ink);font-weight:600">유료 장비</b> — ' + esc(parts)
                     + ' (대관 1회당 · 이용 시간과 무관)</p>')
    fabric_line = (
        '<p style="margin:18px 0 0;font-size:13px;color:var(--dim)">'
        '원단 14색 — 오간자 7 · 쉬폰 4 · 공단 2 · 수묵 프린트 1 · 전부 무료</p>'
    ) if slug == "a" else ""

    return (
        '<section class="sec" id="props-teaser"><div class="inner">'
        '<div style="display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:16px">'
        '<div><div style="font-size:clamp(20px,2.4vw,28px);letter-spacing:-.02em;color:var(--ink)">'
        + esc(room["label"]) + " 비치 소품</div>"
        '<p class="desc" style="margin:8px 0 0;font-size:14px;color:var(--dim)">장비 ' + str(len(eq) + eq_paid)
        + ' · 소품 ' + str(len(items)) + ' — 이 룸에 있는 것만 적었습니다. 유료 장비는 금액으로 적었습니다.</p></div>' + link + "</div>"
        '<div style="font-family:var(--label-font);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:14px 0 9px">장비</div>'
        '<ul style="list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px">' + chips(eq) + "</ul>"
        '<div style="font-family:var(--label-font);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);margin:20px 0 9px">소품</div>'
        '<ul style="list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px">' + chips(items) + "</ul>"
        + fabric_line + paid_line +
        '<p style="margin:18px 0 0;font-size:12.5px;color:var(--faint)">비치 품목과 수량은 촬영·세팅 상황에 따라 달라질 수 있어요.</p>' + "</div>"
        "</section>"
    )


def render_paid_cards(room: dict) -> str:
    """요금·예약 카드 안 «유료 장비» — 사진 56px + 이름 + 금액, 총액 상한 1줄.
    (내부작업 판정: 버튼 금지 · 예약 화면의 추가 대여 안내만 · 총액 사전 공개)"""
    import json as _json
    path = ROOT / "props.json"
    if not path.exists():
        return ""
    doc = _json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("paid", {}).get(room["slug"], [])
    if not rows:
        return ""
    total = int(room["pricing"].get("equipmentTotalMax") or
                sum(int(r["price"].replace(",", "").replace("원", "")) for r in rows))
    photo_dir = ROOT / "img" / "props"
    items = []
    for r in rows:
        pid = r.get("photo")
        src = None
        if pid:
            for ext in ("jpg", "jpeg", "png", "webp"):
                p = photo_dir / (pid + "." + ext)
                if p.exists():
                    src = "/img/props/%s.%s" % (pid, ext)
                    break
        thumb = ('<span class="pc-ph"><img src="%s" alt="" loading="lazy" width="112" height="84"></span>' % src) if src else '<span class="pc-ph"></span>'
        items.append('<li>%s<span class="pc-b"><b>%s</b><span class="pc-p">%s</span></span></li>'
                     % (thumb, esc(r["name"]), esc(r["price"])))
    label = ("%d종 모두 " % len(rows)) if len(rows) > 1 else ""
    allmax = ('<p class="pc-all">' + label + '추가 시 최대 +%s원 (대관료 별도)</p>'
              % format(total, ","))
    return ('<div class="paidcards"><div class="pc-head"><span>유료 장비</span>'
            '<span>대관 1회당 · 이용 시간과 무관</span></div>'
            + allmax
            + '<ul>' + "".join(items) + '</ul>'
            '<p class="pc-note">예약 화면의 «추가 대여»에서 함께 결제할 수 있어요.</p></div>')

def build_page(room: dict, other: dict, catalog: dict, business: dict, reviews_doc: dict, template: str) -> str:
    p = room["pricing"]
    price_line = (
        '<div class="p-price">'
        f'<div class="p-amount"><span class="p-k">평일</span><b>{won(p["weekday"])}</b>'
        f'<span class="p-div">/</span><span class="p-k">주말</span><b>{won(p["weekend"])}</b></div>'
        f'<div class="p-meta">시간당 · 최소 {p["minHours"]}시간 · {p["baseGuests"]}인 기준 · '
        f'{"부가세 포함" if p["taxIncluded"] else "부가세 별도"}</div>'
        "</div>"
    )
    # 추가요금 고지 — 룸 페이지엔 FAQ 가 없어 조건이 통째로 빠져 있었다(2026-08-04 검수).
    # CTA 를 태우는 페이지에서 조건을 숨기면 기대 불일치 = 보이스 1층(정직) 위반이다.
    # 10-01 대표(9a 중계): 문장 두 개를 잇는 « · » 는 줄바꿈으로 바꾼다(짧은 항목 목록인 가격 줄은 « · » 그대로).
    # 11-20 대표: 무료/유료 장비는 세 면(메인·/a·/b)이 같은 문형으로 적는다.
    #   무료 = rooms.json freeEquipment 목록, 유료 = equipmentFees(품목별 금액).
    # 2026-11-25 대표: 한 문단에 몰아넣어 읽기 어렵다 → 라벨 줄로 나눈다(가격·인원·조명·예약 기준).
    # 카드 안에서는 «무료»가 라벨로 이미 말해지므로 중복 표기를 덜어 문장을 짧게 유지한다.
    free_list = " · ".join(p["freeEquipment"]).replace("(무료)", "").replace("동조기 포함", "동조기") if p.get("freeEquipment") else ""
    price_conditions = (
        '<dl class="p-cond">'
        f'<div><dt>인원 추가</dt><dd>{p["baseGuests"] + 1}인째부터 시간당 {won(p["extraGuestPerHour"])}</dd></div>'
        f'<div><dt>무료 장비</dt><dd>무료 — {free_list}</dd></div>'
        f'<div><dt>유료 장비</dt><dd>대관 1회당 · 품목별 금액은 아래 참고</dd></div>'
        f'<div><dt>예약 기준</dt><dd>주말은 {p["weekendDefinition"]} · 최종 금액은 아워플레이스 예약 화면에서 확인</dd></div>'
        "</dl>"
    )
    # ⚠️ 룸 간 가격 비교 금지(대표 2026-07-26): 이 페이지엔 이 룸 값만 적는다.
    #    다른 룸 카드(OTHER_*)에 가격을 넣지 않는 것도 같은 이유다.
    price_line = _glue_inner(price_line)   # 10-01 가격 줄은 문단(<p>) 밖이라 따로 다듬는다(«주말 / 45,000원»·«최소 / 2시간» 끊김)
    booking_note = (
        "예약·결제는 아워플레이스에서 진행돼요.<br>예약한 룸은 그 팀만 단독으로 사용해요."
        if catalog["fulfillment"]["mode"] == "external"
        else "예약·결제를 이 페이지에서 바로 진행하실 수 있어요."
    )
    hero = room["hero"]
    phone_display = format_business_phone(business["tel"])
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

    # 11-24: 세팅을 공간보다 위로 → 01 소개, (02 세팅), 공간, 이후 순서대로.
    counter = 2
    setups_no = gallery_no = prep_no = reviews_no = notice_no = None
    if room.get("setups"):
        setups_no = f"{counter:02d}"
        counter += 1
    gallery_no = f"{counter:02d}"
    counter += 1
    if (room.get("prep") or {}).get("items"):
        prep_no = f"{counter:02d}"
        counter += 1
    if (room.get("notice") or {}).get("items"):
        notice_no = f"{counter:02d}"
        counter += 1
    reviews_no = f"{counter:02d}"
    rv_rating = reviews_doc.get("rating")
    rv_count = reviews_doc.get("count", len(reviews_doc.get("reviews", [])))
    repl = {
        "FONT_HEAD": font_head(room["slug"]),
        "THEME": room.get("theme", "light"),   # 11-24 대표: 룸별 기본 모드(A=다크, B=라이트)
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
        "HERO_EYEBROW": (f'<div data-reveal style="font-family:var(--label-font);font-size:11.5px;letter-spacing:.34em;text-transform:uppercase;color:rgba(255,255,255,.72)">{esc(hero["kicker"])}</div>') if not room.get("hideKickers") else "",
        "ABOUT_KICKER": kick(room, esc(hero["kicker"])),
        "GALLERY_KICKER": kick(room, "Gallery"),
        "BOOKING_KICKER": ('<div class="skick" style="margin-bottom:10px">Booking</div>') if not room.get("hideKickers") else "",
        "H1_1": esc(hero["h1"][0]),
        "H1_2": esc(hero["h1"][1]),
        "SUB": hero["sub"],  # <br> 허용 필드
        "SEASON_NOTE": render_season_note(room),
        "HERO_IMG": esc(hero["image"]),
        "HERO_TONE": ' data-hero-tone="light"' if hero.get("tone") == "light" else "",   # 10-01 밝은 사진 첫 화면
        # 11-24: 밝은 히어로는 대체 배경도 밝게 → 사진 로딩 전 검게 번쩍이는 «플리커» 방지
        "HERO_FALLBACK": ("linear-gradient(135deg,#F7F7F8,#EFEFF1)" if hero.get("tone") == "light"
                          else "linear-gradient(135deg,#0B0B0C,#1C1C1F)"),
        "HERO_SRCSET": hero_srcset(hero["image"])[0],
        "HERO_PRELOAD": hero_srcset(hero["image"])[1],
        "HERO_ALT": esc(hero["alt"]),
        "HERO_TAGS": render_hero_tags(room),
        "INFO_CELLS": render_info_cells(room),
        "BLOCKS": render_blocks(room),
        "GALLERY_NO": gallery_no,
        "GALLERY": render_gallery(room),
        "GALLERY_DESC": esc(room.get("galleryDesc") or f"{room['label']}에서 찍힌 장면들이에요."),
        "ABOUT_LEAD": (f'<p class="desc" data-reveal style="margin:0 0 26px">{esc(room["aboutLead"])}</p>' if room.get("aboutLead") else ""),
        "SETUPS": render_setups(room, no=setups_no) if setups_no else "",
        "PROPS_TEASER": render_props_teaser(room),
        "PREP": render_prep(room, no=prep_no) if prep_no else "",
        "REVIEWS": render_reviews(room, reviews_doc, no=reviews_no),
        "NOTICE": render_notice(room, no=notice_no) if notice_no else "",
        "PRICE_LINE": price_line,
        "PRICE_CONDITIONS": price_conditions,
        "PAID_CARDS": render_paid_cards(room),
        "BOOK_RATING": (f'<div style="display:flex;align-items:center;gap:6px;margin:0 0 14px;color:var(--dim);font-size:12.5px"><span style="color:var(--accent)">★</span> {esc(str(rv_rating))} · 후기 {esc(str(rv_count))}건</div>' if room.get("bookRating") and rv_rating and rv_count else ""),
        "BOOKING_HREF": booking_href(room, catalog),
        "BOOKING_NOTE": booking_note,
        "FAQ_LINKS": render_faq_links(room),
        "OTHER_LABEL": esc(other["label"]),
        "OTHER_NAME": esc(other["name"]),
        "OTHER_SLUG": other["slug"],
        "INQUIRY_LINE": esc(room["inquiryLine"]),
        "FOOTER_LINES": render_footer_lines(room, phone_display),
    }
    out = template
    for k, v in repl.items():
        out = out.replace("{{" + k + "}}", str(v))
    if "{{" in out:
        leftover = out[out.index("{{") : out.index("{{") + 40]
        raise SystemExit(f"[build_rooms] 치환 안 된 자리표시자: {leftover}")
    out = glue_html(out)   # 10-01 한국어 줄바꿈 다듬기(ko_glue.py · 글자 불변)
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
    # 2026-11-25: 비치 소품 — 룸 탭 전환형 단일 페이지(/props)
    if (ROOT / "props.html").exists():
        urls.append(("/props", "monthly", "0.6", _source_lastmod(ROOT / "props.html")))
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

    catalog, rooms, business = spec["catalog"], spec["rooms"], spec["business"]

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
        out[f"{room['slug']}.html"] = build_page(room, other, catalog, business, reviews_doc, template)
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
