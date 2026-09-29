# -*- coding: utf-8 -*-
"""사이트 글자 서브셋 글꼴 자체 호스팅(2026-09-29) 회귀 잠금.

근거: Pretendard 동적 서브셋(CDN)은 글자 배치 뒤에 조각을 요청해 새로 열 때마다 글꼴이 늦게 바뀌고, 그때 화면의 글이
전부 줄바꿈을 다시 해 밀렸다(/a 360px 뒤로 가기 CLS 0.4~0.6). CDN CSS 는 렌더도 막았다(/a 첫 화면 3.1초).
실제 화면 판정은 nuvie_ux_lab(check_font_ready.py·하네스 S219·S240·S266)이 하고, 여기서는 파일·마크업 계약을 잠근다.
🧊 /b 는 11/11 동결 — b.html 은 옛 글꼴 두 줄 그대로(test_ux0929_1_anchor 의 바이트 동일 검사가 함께 지킨다).
"""
import re
from pathlib import Path

import build_fonts as BF

ROOT = Path(__file__).parent
WEIGHTS = (400, 500, 600, 700)
CDN = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css"


def _read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def _head(html):
    return html[: html.index("</head>")]


def test_subset_fonts_exist_and_do_not_carry_reserved_name():
    """OFL Reserved Font Name «Pretendard» — 수정본(서브셋)은 그 이름을 쓰면 안 된다. 라이선스 원문을 함께 싣는다."""
    from fontTools.ttLib import TTFont
    for w in WEIGHTS:
        f = TTFont(str(ROOT / "fonts" / f"nuvie-sans-{w}.woff2"))
        names = {str(r) for r in f["name"].names if r.nameID in (1, 4, 6, 16)}
        assert names and not any("Pretendard" in n for n in names), (w, names)
        assert "NuvieSans" in names
    lic = (ROOT / "fonts" / "LICENSE-Pretendard-OFL.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License" in lic and "Reserved Font Name Pretendard" in lic


def test_subset_covers_every_character_the_site_shows():
    from fontTools.ttLib import TTFont
    need = BF.site_chars(ROOT) - {" "}
    for w in WEIGHTS:
        cmap = TTFont(str(ROOT / "fonts" / f"nuvie-sans-{w}.woff2")).getBestCmap()
        missing = sorted(c for c in need if ord(c) not in cmap and not c.isspace())
        # 원본 Pretendard 에 없는 글자(이모지 등)는 원래도 대체 글꼴이다 — 한글·영숫자는 전부 있어야 한다
        hard = [c for c in missing if ("가" <= c <= "힣") or c.isalnum() and ord(c) < 0x250]
        assert not hard, f"{w}: 서브셋에 빠진 글자 {''.join(hard)[:40]} — build_fonts.py 를 다시 돌릴 것"


def test_fonts_css_declares_four_weights_with_swap():
    css = _read("fonts.css")
    faces = re.findall(r"@font-face\s*\{([^}]*)\}", css)
    got = {int(re.search(r"font-weight:\s*(\d+)", f).group(1)) for f in faces}
    assert got == set(WEIGHTS)
    for f in faces:
        assert "NuvieSans" in f and "font-display:swap" in f.replace(" ", "")
        assert re.search(r"url\(/fonts/nuvie-sans-\d{3}\.woff2\)", f)


def _assert_new_font_head(html, page):
    head = _head(html)
    for w in WEIGHTS:
        assert re.search(rf'<link rel="preload" href="/fonts/nuvie-sans-{w}\.woff2" as="font" type="font/woff2" crossorigin>', head), (page, w)
    assert '<link rel="stylesheet" href="/fonts.css">' in head, page
    # CDN 동적 서브셋은 드문 글자 예비로만 — 렌더를 막지 않게(media=print → onload 로 all).
    #   <noscript> 안의 줄은 JS 가 꺼진 때만 쓰이므로 판정에서 뺀다.
    live = re.sub(r"<noscript>.*?</noscript>", "", head, flags=re.S)
    blocking = re.findall(r'<link rel="stylesheet" href="' + re.escape(CDN) + r'">', live)
    assert not blocking, f"{page}: CDN 글꼴 CSS 가 아직 렌더를 막는다"
    assert re.search(r'href="' + re.escape(CDN) + r'" media="print" onload="this\.media=\'all\'"', head), page
    assert head.index("/fonts/nuvie-sans-400.woff2") < head.index("/styles.css"), f"{page}: preload 는 스타일보다 먼저"


def test_home_and_room_a_use_self_hosted_fonts():
    _assert_new_font_head(_read("index.html"), "index.html")
    _assert_new_font_head(_read("a.html"), "a.html")


def test_room_b_keeps_frozen_cdn_font_lines():
    head = _head(_read("b.html"))
    assert '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>\n<link rel="stylesheet" href="' + CDN + '">' in head
    assert "nuvie-sans" not in head and "fonts.css" not in head


def test_font_stacks_start_with_nuvie_sans_then_pretendard():
    css = _read("styles.css")
    assert "--label-font:'NuvieSans','Pretendard',sans-serif" in css.replace(" ", "")
    assert re.search(r"body\{font-family:'NuvieSans','Pretendard',system-ui", css.replace(" ", ""))


def test_vercel_caches_fonts_so_back_navigation_needs_no_revalidation():
    """기본값(max-age=0, must-revalidate)이면 뒤로 가기마다 서버 확인 왕복만큼 글꼴이 늦어 첫 화면이 대체 글꼴로 그려진다."""
    import json
    rules = json.loads(_read("vercel.json"))["headers"]
    font = [r for r in rules if r["source"] == "/fonts/(.*)"]
    assert font, "vercel.json 에 /fonts/ 캐시 규칙이 없다"
    value = next(h["value"] for h in font[0]["headers"] if h["key"].lower() == "cache-control")
    assert int(re.search(r"max-age=(\d+)", value).group(1)) >= 86400


def test_vercel_ships_fonts_dir():
    ignore = _read(".vercelignore")
    assert not re.search(r"^fonts/?$", ignore, flags=re.M) and not re.search(r"^\*\.woff2", ignore, flags=re.M)


def test_source_download_rejects_non_woff2_and_skips_existing(tmp_path):
    """원본 주소가 오류 페이지(텍스트)를 돌려주면 글꼴로 저장하지 않고 멈춘다. 이미 있으면 받지 않는다."""
    import pytest
    with pytest.raises(SystemExit):
        BF.ensure_sources(tmp_path / "a", fetch=lambda url: b"Couldn't find the requested file")
    calls = []
    good = lambda url: (calls.append(url), b"wOF2" + b"0" * 10)[1]
    BF.ensure_sources(tmp_path / "b", fetch=good)
    n = len(calls)
    BF.ensure_sources(tmp_path / "b", fetch=good)
    assert n == len(BF.SRC_FILES) and len(calls) == n, "두 번째는 받지 않아야 한다"
