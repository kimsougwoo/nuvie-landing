# -*- coding: utf-8 -*-
"""10-01: 글꼴 서브셋이 주석 글자까지 담아 4개 글꼴이 각 ~72KB 였다(한글 708자 중 195자가 주석에만).
주석 글자는 빼고, 화면에 나오는 글자(본문·JS 문자열·JSON 값)는 그대로 남는지 잠근다."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_fonts", ROOT / "build_fonts.py")
BF = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BF)


def _chars(tmp_path, name, text):
    (tmp_path / name).write_text(text, encoding="utf-8")
    return BF.site_chars(tmp_path, [name])


def test_html_comment_only_glyph_is_dropped(tmp_path):
    got = _chars(tmp_path, "x.html", "<p>보임</p><!-- 숨김 -->")
    assert "보" in got and "임" in got
    assert "숨" not in got and "김" not in got


def test_js_comments_dropped_but_strings_and_urls_kept(tmp_path):
    js = "/* 블록 */ var a = '문자열'; // 줄주석\nvar u = 'https://x.y/z'; var b = \"따옴표\";"
    got = _chars(tmp_path, "x.js", js)
    for c in "문자열따옴표":
        assert c in got, c
    for c in "블록줄주석":
        if c not in "문자열따옴표":
            assert c not in got, c
    assert "/" in got   # 주소 문자열(ASCII 는 ALWAYS 에도 있다)


def test_inline_script_comment_dropped_in_html(tmp_path):
    html = "<p>본문</p><script>var t='스크립트 글'; // 메모\n/* 설명 */</script>"
    got = _chars(tmp_path, "x.html", html)
    for c in "본문스크립트글":
        assert c in got, c
    for c in "메모설명":
        assert c not in got, c


def test_built_subset_is_smaller_than_before():
    # 10-01 이전 서브셋은 각 72,856~73,288 바이트였다
    for w in (400, 500, 600, 700):
        assert (ROOT / "fonts" / f"nuvie-sans-{w}.woff2").stat().st_size < 70000, w
