# -*- coding: utf-8 -*-
"""2026-08-04 감사 개선 4건 재현 테스트.

  1. book_click 에 page 출처 파라미터 추가(허브='hub' / 룸페이지='room_a'|'room_b')
     — ⚠️ 기존 파라미터(room·transport_type)·이벤트명은 절대 불변, page 는 "추가"만.
  2. 룸 페이지 히어로 "공간 보기" 에 hero_cta_click 계측 신설
  3. 허브 → 룸 상세(/a·/b) 이동에 새 이벤트 room_detail_click 신설(book_click 재사용 금지)
  4. vercel.json 에 /ig-a·/ig-b·/x-a·/x-b UTM 단축경로 신설(기존 5개는 불변)

⚠️ a.html·b.html 은 room.template.html 에서 빌드된 결과물을 그대로 읽는다(직접 고치지 않음).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def _read(name):
    return open(os.path.join(HERE, name), encoding="utf-8").read()


# ── 1. book_click page 파라미터 ─────────────────────────────────────
def test_hub_book_click_gains_page_param_without_losing_existing_ones():
    html = _read("index.html")
    m = re.search(r"gtag\('event','book_click',\{([^}]*)\}\)", html)
    assert m, "index.html 에서 book_click gtag 호출을 못 찾았다"
    params = m.group(1)
    assert "room:room" in params, "book_click 의 기존 room 파라미터가 사라졌다"
    assert "transport_type:'beacon'" in params, "book_click 의 기존 transport_type 파라미터가 사라졌다"
    assert "page:'hub'" in params, "허브 book_click 에 page:'hub' 가 추가되지 않았다"


def test_room_page_book_click_gains_page_param_without_losing_existing_ones():
    js = _read("site.js")
    m = re.search(r"gtag\('event', 'book_click', \{([^}]*)\}\)", js)
    assert m, "site.js 에서 book_click gtag 호출을 못 찾았다"
    params = m.group(1)
    assert "room: room" in params
    assert "transport_type: 'beacon'" in params
    assert "page: PAGE_ORIGIN" in params, "룸 페이지 book_click 에 page 파라미터가 추가되지 않았다"
    # PAGE_ORIGIN 은 <body data-room="{{SLUG}}"> 에서 파생돼야 한다(허브·룸페이지 구분의 유일한 근거)
    assert "data-room" in js


def test_ad_capture_and_lead_untouched():
    """book_click 주변의 다른 두 핵심 지표(ad_capture·Meta Lead)는 이번 작업이 건드리지 않아야 한다."""
    html = _read("index.html")
    js = _read("site.js")
    for text in (html, js):
        assert "fbq('track', 'Lead'" in text or "fbq('track','Lead'" in text
        assert "ad_capture" in text
    # ad_capture 파라미터는 기존 그대로(page 추가 안 됨 — 지시에서 book_click 만 명시)
    m = re.search(r"gtag\('event','ad_capture',\{([^}]*)\}\)", html)
    assert m and "page" not in m.group(1)


def test_built_room_pages_carry_page_marker_per_slug():
    """빌드된 a.html·b.html 의 <body data-room> 이 각자 슬러그로 갈려야 page:'room_a'/'room_b' 파생이 맞다."""
    a_html, b_html = _read("a.html"), _read("b.html")
    assert re.search(r'<body[^>]*data-room="a"', a_html)
    assert re.search(r'<body[^>]*data-room="b"', b_html)


# ── 2. 룸 페이지 hero_cta_click ──────────────────────────────────────
def test_room_template_hero_gallery_has_id_for_tracking():
    tpl = _read("room.template.html")
    assert re.search(r'id="hero-gallery"[^>]*>공간 보기', tpl) or re.search(
        r'href="#gallery"[^>]*id="hero-gallery"', tpl
    ), "룸 페이지 히어로 '공간 보기' 앵커에 id=hero-gallery 가 없다"


def test_site_js_wires_hero_cta_click_same_event_name_as_hub():
    js = _read("site.js")
    assert "hero_cta_click" in js, "site.js 에 hero_cta_click 이벤트가 없다"
    assert "hero-gallery" in js


def test_built_room_pages_contain_hero_gallery_id():
    for name in ("a.html", "b.html"):
        html = _read(name)
        assert 'id="hero-gallery"' in html, f"{name} 에 hero-gallery id 가 없다(빌드 누락)"


# ── 3. 허브 → 룸 상세 room_detail_click ──────────────────────────────
def test_hub_has_room_detail_click_wiring():
    html = _read("index.html")
    assert "room_detail_click" in html
    # book_click 재사용 금지 — 새 이벤트여야 한다(같은 트리거에 book_click 을 얹지 않았는지 확인)
    assert "gtag('event','room_detail_click'" in html.replace(" ", "") or re.search(
        r"gtag\('event',\s*'room_detail_click'", html
    )


def test_hub_room_detail_targets_cover_card_and_hero_badge_both_rooms():
    html = _read("index.html")
    pairs = re.findall(r'data-room-detail="([ab])"\s+data-room-detail-from="(card|hero_badge)"', html)
    assert set(pairs) == {("a", "card"), ("b", "card"), ("a", "hero_badge"), ("b", "hero_badge")}, (
        f"room_detail_click 계측 대상이 4종(A/B x 카드/히어로뱃지) 모두 갖춰지지 않았다: {pairs}"
    )


def test_room_detail_click_does_not_reuse_book_click_definition():
    """지시서 요구사항: book_click 을 재사용하지 말 것 — 정의 오염 방지."""
    html = _read("index.html")
    # data-room-detail 앵커들은 data-book 속성을 갖지 않아야 한다(별개 계측 경로)
    for m in re.finditer(r'<a\s[^>]*data-room-detail="[ab]"[^>]*>', html):
        assert "data-book" not in m.group(0)


# ── 4. vercel.json UTM 단축경로 ──────────────────────────────────────
def _redirects():
    spec = json.loads(_read("vercel.json"))
    return {r["source"]: r for r in spec["redirects"]}


def test_existing_five_redirects_untouched():
    r = _redirects()
    expected = {
        "/x": "/?utm_source=x&utm_medium=social&utm_campaign=bio",
        "/ig": "/?utm_source=instagram&utm_medium=social&utm_campaign=bio",
        "/pm": "/?utm_source=instagram&utm_medium=cpc&utm_campaign=ad-meta-pilot-2026q3",
        "/pm1": "/?utm_source=instagram&utm_medium=cpc&utm_campaign=ad-meta-pilot-2026q3&utm_content=cosplay_niche",
        "/pm2": "/?utm_source=instagram&utm_medium=cpc&utm_campaign=ad-meta-pilot-2026q3&utm_content=ab_cosplaycard",
        "/pm3": "/?utm_source=instagram&utm_medium=cpc&utm_campaign=ad-meta-pilot-2026q3&utm_content=reels",
    }
    for source, dest in expected.items():
        assert source in r, f"기존 리다이렉트 {source} 가 사라졌다"
        assert r[source]["destination"] == dest, f"{source} 목적지가 바뀌었다: {r[source]['destination']}"
        assert r[source]["permanent"] is False


def test_new_room_targeted_shortlinks_exist_and_follow_existing_utm_shape():
    r = _redirects()
    expected = {
        "/ig-a": "/a?utm_source=instagram&utm_medium=social&utm_campaign=bio",
        "/ig-b": "/b?utm_source=instagram&utm_medium=social&utm_campaign=bio",
        "/x-a": "/a?utm_source=x&utm_medium=social&utm_campaign=bio",
        "/x-b": "/b?utm_source=x&utm_medium=social&utm_campaign=bio",
    }
    for source, dest in expected.items():
        assert source in r, f"신설 리다이렉트 {source} 가 없다"
        assert r[source]["destination"] == dest
        assert r[source]["permanent"] is False


def test_redirect_count_grew_by_exactly_four():
    spec = json.loads(_read("vercel.json"))
    assert len(spec["redirects"]) == 10, "기존 6개(x/ig/pm/pm1-3) + 신설 4개(ig-a/ig-b/x-a/x-b) = 10개여야 한다"


if __name__ == "__main__":
    import sys
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))


# ── 내부 트래픽 게이트 (2026-08-04) ──────────────────────────────────
# 🔴 신설 사유(GA4 실측): 주간 (direct) 26세션 = 전체 19% 인데 81%가 재방문이고 랜딩 URL 에
#    /index.html·/?v=live 가 섞여 있었다 = 대표와 내가 라이브를 확인하며 만든 우리 트래픽.
#    그래서 (direct) 만 전환 3.4% 로 유독 낮았다. 광고 재개 조건이 「판정 계기 GA4 고정」이라
#    오염을 끊는다. ⚠️ 이벤트 정의·이름·파라미터는 불변 — 바뀐 건 「태그를 로드할지」뿐이다.
import re as _re
from pathlib import Path as _P

_ROOT = _P(__file__).parent
_PAGES = ["index.html", "a.html", "b.html", "room.template.html"]


def _gate(src):
    """게이트 블록만 정확히 잘라낸다.

    ⚠️ 「__nvInternal 주변 ±N자」로 자르면 안 된다 — 허브엔 앞에 google-site-verification
      meta 가 있어서 앞뒤 컨텍스트가 달라지고, 동일성 비교가 거짓 실패한다(2026-08-04 겪음)."""
    s = src.index("<!-- 계측 3태그")
    e = src.index("</script>", src.index("})();", s)) + len("</script>")
    return src[s:e]


def test_모든_페이지에_내부_트래픽_게이트가_있다():
    for name in _PAGES:
        src = (_ROOT / name).read_text(encoding="utf-8")
        assert "window.__nvInternal" in src, f"{name} 에 게이트가 없다"
        assert "nv_internal" in src, f"{name} 에 localStorage 키가 없다"


def test_게이트가_태그보다_먼저_온다():
    """게이트가 늦으면 태그가 이미 로드돼 의미가 없다."""
    for name in _PAGES:
        src = (_ROOT / name).read_text(encoding="utf-8")
        assert src.index("window.__nvInternal") < src.index("googletagmanager.com/gtag/js"), name


def test_내부일_때_태그를_안_붙이고_스텁만_둔다():
    for name in _PAGES:
        src = (_ROOT / name).read_text(encoding="utf-8")
        g = _gate(src)
        assert "window.gtag = function(){}" in g, f"{name}: gtag 스텁 없음"
        assert "window.fbq = function(){}" in g, f"{name}: fbq 스텁 없음"
        assert "window.clarity = function(){}" in g, f"{name}: clarity 스텁 없음"


def test_localStorage_차단시_정상계측으로_폴백():
    """사파리 프라이빗 등에서 localStorage 가 던지면 «계측 안 됨» 이 기본값이 되면 안 된다."""
    for name in _PAGES:
        src = (_ROOT / name).read_text(encoding="utf-8")
        assert "catch (e) { internal = false; }" in src, f"{name}: 예외 시 기본값이 안전하지 않다"


def test_이벤트_정의는_불변이다():
    """광고 파일럿 판독 지표 — 게이트를 넣으면서 건드리면 안 된다."""
    hub = (_ROOT / "index.html").read_text(encoding="utf-8")
    assert "'book_click',{room:room,transport_type:'beacon',page:'hub'}" in hub
    assert "fbq('track','Lead',{room:room})" in hub
    assert "fbq('init', '1062603212821765')" in hub
    assert "gtag('config', 'G-53WEQ1DGXG')" in hub


def test_허브와_룸템플릿의_게이트가_동일하다():
    """한쪽만 고치면 페이지마다 계측 정책이 갈린다."""
    a = _gate((_ROOT / "index.html").read_text(encoding="utf-8"))
    b = _gate((_ROOT / "room.template.html").read_text(encoding="utf-8"))
    norm = lambda s: _re.sub(r"\s+", " ", s)
    assert norm(a) == norm(b), "허브와 룸 템플릿의 게이트가 갈렸다"
