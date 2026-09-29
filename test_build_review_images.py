# -*- coding: utf-8 -*-
"""후기 사진 자체 호스팅 사본(2026-09-29) — build_review_images.py 와 index.html 소비 계약.

왜: 홈 후기 사진 15장이 아워플레이스 원본(합계 약 75MB, 최대 29MP)을 그대로 썸네일·확대에 써서
    모바일에서 확대까지 2.5~3초 화면이 멈췄다. 축소 WebP 사본(640/1600)을 저장소에 두고 쓴다.
    네트워크는 전부 가짜(fetch 주입)로 돌린다.
"""
import hashlib
import io
import json
import re
from pathlib import Path

import pytest
from PIL import Image

HERE = Path(__file__).resolve().parent
INDEX = (HERE / "index.html").read_text(encoding="utf-8")

import build_review_images as B  # noqa: E402


def _jpeg(w, h, exif_orientation=None, color=(200, 30, 30)):
    im = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    if exif_orientation:
        ex = Image.Exif()
        ex[0x0112] = exif_orientation
        im.save(buf, "JPEG", exif=ex)
    else:
        im.save(buf, "JPEG")
    return buf.getvalue()


URL = "https://img.hourplace.co.kr/feedback/user/1/2026/09/12/abc"


def test_filename_is_sha1_12_and_sizes():
    key = hashlib.sha1(URL.encode("utf-8")).hexdigest()[:12]
    assert B.file_key(URL) == key


def test_build_makes_two_webp_copies_with_long_side_caps(tmp_path):
    m, failed = B.build([URL], tmp_path, fetch=lambda u: _jpeg(3000, 2000))
    assert failed == []
    e = m[URL]
    key = B.file_key(URL)
    assert e["thumb"] == f"reviews/img/{key}-640.webp"
    assert e["full"] == f"reviews/img/{key}-1600.webp"
    t = Image.open(tmp_path / f"{key}-640.webp")
    f = Image.open(tmp_path / f"{key}-1600.webp")
    assert t.format == "WEBP" and f.format == "WEBP"
    assert max(t.size) == 640 and max(f.size) == 1600
    assert (e["w"], e["h"]) == f.size == (1600, 1067)
    saved = json.loads((tmp_path / "map.json").read_text(encoding="utf-8"))
    assert saved == m


def test_small_original_is_not_upscaled(tmp_path):
    m, _ = B.build([URL], tmp_path, fetch=lambda u: _jpeg(500, 300))
    key = B.file_key(URL)
    assert Image.open(tmp_path / f"{key}-1600.webp").size == (500, 300)
    assert Image.open(tmp_path / f"{key}-640.webp").size == (500, 300)


def test_exif_rotation_is_applied(tmp_path):
    # 저장된 픽셀은 가로(400x200)인데 EXIF 6 = 시계방향 90도 → 세로(200x400)로 세워야 한다.
    m, _ = B.build([URL], tmp_path, fetch=lambda u: _jpeg(400, 200, exif_orientation=6))
    key = B.file_key(URL)
    w, h = Image.open(tmp_path / f"{key}-1600.webp").size
    assert (w, h) == (200, 400)
    assert (m[URL]["w"], m[URL]["h"]) == (200, 400)


def test_idempotent_skips_download_when_files_exist(tmp_path):
    calls = []

    def fetch(u):
        calls.append(u)
        return _jpeg(1000, 800)

    m1, _ = B.build([URL], tmp_path, fetch=fetch)
    m2, _ = B.build([URL], tmp_path, fetch=fetch)
    assert len(calls) == 1
    assert m1 == m2


def test_failed_download_is_left_out_of_map_and_reported(tmp_path):
    bad = URL + "-bad"

    def fetch(u):
        if u == bad:
            raise OSError("boom")
        return _jpeg(800, 800)

    m, failed = B.build([URL, bad], tmp_path, fetch=fetch)
    assert URL in m and bad not in m
    assert failed == [bad]
    assert not list(tmp_path.glob(f"{B.file_key(bad)}*"))


def test_undecodable_bytes_count_as_failure(tmp_path):
    m, failed = B.build([URL], tmp_path, fetch=lambda u: b"not an image")
    assert m == {} and failed == [URL]


def test_reviews_json_files_are_not_touched_by_builder():
    src = (HERE / "build_review_images.py").read_text(encoding="utf-8")
    # 읽기만: reviews_all.json 에 쓰는 코드가 없어야 한다(후기 원문 verbatim).
    assert not re.search(r"reviews(_all)?\.json[^\n]*(write|dump)", src)
    assert "open(" not in src or "'w'" not in src.split("reviews_all")[0]


# ── index.html 소비 계약 ──────────────────────────────────────────────
def test_index_loads_map_and_never_blocks_render_on_it():
    assert "reviews/img/map.json" in INDEX
    # map 실패해도 렌더 계속: map fetch 에 catch 가 있어야 한다
    m = re.search(r"fetch\('reviews/img/map\.json'[^;]*?\.catch\(", INDEX, re.S)
    assert m, "map.json fetch 는 실패해도 후기 렌더가 계속돼야 한다(.catch)"


def test_index_thumb_uses_map_thumb_and_lightbox_uses_full_with_fallback():
    assert re.search(r"\.thumb", INDEX) and re.search(r"\.full", INDEX)
    # 폴백: map 에 없으면 원본 src 그대로
    assert re.search(r"(\|\|\s*src|:\s*src)\b", INDEX)
    # 썸네일 img 는 lazy/async 유지 + 치수 속성
    assert "im.loading='lazy'" in INDEX
    assert "im.decoding='async'" in INDEX
    assert re.search(r"im\.width\s*=|setAttribute\('width'", INDEX)


def test_index_still_renders_photos_slice_two_and_original_order():
    assert "v.photos.slice(0,2)" in INDEX


# ── 라이트박스 체감 계약 ──────────────────────────────────────────────
def test_lightbox_has_loading_indicator_element():
    assert 'id="reviewLightboxLoading"' in INDEX


def test_openlb_shows_loading_then_swaps_on_load_and_decode():
    m = re.search(r"function openLb\(.*?\n\s*function closeLb", INDEX, re.S)
    assert m
    body = m.group(0)
    assert "reviewLightboxLoading" in body or "lbLoading" in body
    assert "decode" in INDEX and "onload" in INDEX.replace(" ", "")
    # 클릭 즉시 연다(display flex 가 이미지 로드 대기보다 먼저 온다)
    assert body.index("display='flex'") < body.index("decode") if "decode" in body else True


def test_backdrop_click_ignored_right_after_open():
    m = re.search(r"lb\.addEventListener\('click',function\(e\)\{(.*?)\}\);", INDEX, re.S)
    assert m
    handler = m.group(1)
    assert "lbOpenedAt" in handler and "300" in handler


def test_close_button_and_escape_are_immediate():
    assert re.search(r"reviewLightboxClose'\)\.addEventListener\('click',closeLb\)", INDEX)
    assert re.search(r"e\.key==='Escape'&&lb\.style\.display==='flex'\)\s*closeLb\(\)", INDEX)


def test_a11y_and_scroll_lock_kept():
    assert "reviewLightboxClose').focus()" in INDEX
    assert "document.body.style.overflow=lbPrevOverflow" in INDEX
    assert "lbTrigger.focus()" in INDEX


def test_vercelignore_ships_reviews_dir_but_not_scripts():
    vi = (HERE / ".vercelignore").read_text(encoding="utf-8").splitlines()
    active = [l.strip() for l in vi if l.strip() and not l.startswith("#")]
    assert "*.py" in active
    assert not any(l.rstrip("/") == "reviews" or l.startswith("reviews/") for l in active)
