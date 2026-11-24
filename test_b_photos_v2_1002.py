# -*- coding: utf-8 -*-
"""/b 사진을 B룸 재보정 v2 로 교체(2026-10-02 대표 결정, 총괄 중계 · 마케팅팀 요청).

대표 확인: 11/11 /b 동결의 예외로 «측정이 섞여도 괜찮음». 밝기는 다시 손대지 않는다(대표 확인판) ⇒ 자르기·크기 조정만.
  · 순서 = 대표가 직접 바꾼 아워 B 리스팅(62341) 최종 순서(10-02 10:1x «/b도 맞춰 주세요», 마케팅팀이 공개 페이지·편집폼에서 읽음).
  · 첫 화면(room-b)·og-b = 리스팅 커버 broom_20261001_01 (카운터·커피머신). 가로 4:3 그대로 1600/1200/800.
  · 갤러리 = 11-24 대표: B룸 원본(리뉴얼 후)에서 진단 기준 큐레이션 — 가로 10장 + 세로 2장(원본 비율 유지, 크롭 없음). 끝 영상은 제거.
  · 쓰지 않는 사진: 14(대표가 리스팅에서 뺌 — 첫 화면·og 포함 /b 에서도 안 씀)·09(08과 거의 같음)·10(11과 거의 같음). 평면도는 리스팅에만.
  · 11-24 대표: 가로(4:3) 원본을 3:4로 자르던 크롭을 풀고 원본 비율(1000x750)로 다시 뽑았다. ax 자르기 위치는 더 이상 쓰지 않는다.
  · 새 파일 이름(-1002) — 캐시된 옛 사진이 새 alt 와 짝지어지지 않게(10-01 교체와 같은 이유).
"""
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).parent
V2 = Path(r"F:\무인 렌탈스튜디오 인수\source\촬영_2026-09-29\보정_v2")
V1 = Path(r"F:\무인 렌탈스튜디오 인수\source\촬영_2026-09-29\보정")
V3 = Path(r"F:\무인 렌탈스튜디오 인수\아워플레이스\B룸 사진\리뉴얼 후 사진")  # 11-24: 진단 기준 큐레이션 원본
V4 = V3 / "11월"  # 11-24: B 공간 갤러리 교체 원본(DJI 드론, 16:9)

HERO_SRC = V2 / "broom_20261001_01.jpg"
HERO_ALT = "B룸 화이트 티타임 카페 — 커피머신 카운터와 레이스 티테이블"
# (소스, ax, alt) — 순서 = 갤러리 1~11칸 = 리스팅 2~12번
GALLERY = [
    (V4 / "DJI_20261124143900_0042_D.JPG", 0.50, "B룸 전경 — 티테이블과 통창"),
    (V4 / "DJI_20261124144013_0046_D.JPG", 0.50, "B룸 전경 — 앤티크 서랍장과 주방"),
    (V4 / "DJI_20261124144155_0052_D.JPG", 0.50, "B룸 디저트 테이블 — 케이크와 티세트"),
    (V4 / "DJI_20261124144233_0055_D.JPG", 0.50, "B룸 주방과 통창"),
    (V4 / "DJI_20261124144437_0058_D.JPG", 0.50, "B룸 파우더룸 — 화장대와 의자"),
    (V4 / "DJI_20261124144533_0061_D.JPG", 0.50, "B룸 밀크셰이크 디저트"),
]
OLD = ("galB-1001-", "room-b-1001", "og-b-1001")
SURFACES = ("rooms.json", "b.html", "index.html", "build_og.py", "test_b_copy_fixture.json")


def _room_b():
    rooms = json.loads((ROOT / "rooms.json").read_text(encoding="utf-8"))
    return next(r for r in rooms["rooms"] if r["slug"] == "b")


def _crop34(src: Path, ax: float, size):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    cw = h * 3 // 4
    x0 = int((w - cw) * ax)
    return im.crop((x0, 0, x0 + cw, h)).resize(size, Image.LANCZOS)


def _diff(a: Image.Image, b: Image.Image) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


def test_rooms_json_hero_og_and_gallery_order():
    b = _room_b()
    assert b["hero"]["image"] == "/img/room-b-1002.jpg" and b["hero"]["alt"] == HERO_ALT
    assert b["seo"]["ogImage"] == "/img/og-b-1002.jpg"
    gal = b["gallery"]
    assert [g["src"] for g in gal] == ["/img/galB-1003-%d.jpg" % i for i in (1, 2, 5, 6, 7, 8)]
    assert [g["alt"] for g in gal] == [alt for _, _, alt in GALLERY]
    assert len(gal) == 6, "B 공간 갤러리 = 11월 16:9 6장(플리커 3·4 제거)"


def test_no_old_b_photo_reference_left():
    for name in SURFACES:
        text = (ROOT / name).read_text(encoding="utf-8")
        for old in OLD:
            assert old not in text, f"{name} 에 옛 참조 {old} 가 남아 있다"


def test_b_html_and_hub_point_at_new_files():
    B = (ROOT / "b.html").read_text(encoding="utf-8")
    HUB = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'content="https://www.nuviestudio.com/img/og-b-1002.jpg"' in B
    assert 'src="/img/room-b-1002.jpg"' in B and "/img/room-b-1002-800.jpg 800w" in B
    assert HERO_ALT in B
    for i in (1, 2, 5, 6, 7, 8):
        assert f"/img/galB-1003-{i}.jpg" in B, i
    assert "/img/b-table-1001.mp4" not in B, "B 상세 영상 제거됨(11-24)"
    assert "/img/room-b-1002.jpg" in HUB
    assert "light:{src:'/img/room-b-1002.jpg'" in HUB, "허브 라이트 테마 = 새 B룸 첫 화면"
    slides = re.findall(r'class="mgal-slide"><img[^>]*src="(/img/galB-1002-\d+)\.jpg"', HUB)
    assert slides == ["/img/galB-1002-3", "/img/galB-1002-6"], "허브 모바일 갤러리 B 2·3번째 = 곰인형 창가·디저트 스탠드"
    for alt in re.findall(r'<img[^>]*room-b-1002[^>]*alt="([^"]*)"', B + HUB):
        assert "전경" not in alt, f"첫 화면 사진(01 카운터)은 전경이 아니다: {alt}"


def test_image_files_sizes():
    b = _room_b()
    for i, g in enumerate(b["gallery"], 1):
        assert Image.open(ROOT / g["src"].lstrip("/")).size == (g["w"], g["h"]), i
    for suf, size in (("", (1600, 1200)), ("-1200", (1200, 900)), ("-800", (800, 600))):
        assert Image.open(ROOT / f"img/room-b-1002{suf}.jpg").size == size, suf
    assert Image.open(ROOT / "img/og-b-1002.jpg").size == (1200, 630)


def test_gallery_pixels_are_source_resized_without_crop():
    """11-24 대표: B 갤러리 가로 원본 크롭 해제 — 3:4 자르기 없이 4:3 원본을 그대로 축소(밝기 무보정)."""
    for (src, _ax, _), g in zip(GALLERY, _room_b()["gallery"]):
        assert src.exists(), f"원본 없음: {src}"
        out = Image.open(ROOT / g["src"].lstrip("/"))
        assert _diff(out, Image.open(src).convert("RGB").resize(out.size, Image.LANCZOS)) < 4, g["src"]


def test_hero_is_source_01_resized_without_retouch():
    assert HERO_SRC.exists()
    src = Image.open(HERO_SRC).convert("RGB")
    for suf, size in (("", (1600, 1200)), ("-1200", (1200, 900)), ("-800", (800, 600))):
        out = Image.open(ROOT / f"img/room-b-1002{suf}.jpg")
        assert _diff(out, src.resize(size, Image.LANCZOS)) < 4, suf


def test_freeze_fixture_follows_the_exception():
    fx = json.loads((ROOT / "test_b_copy_fixture.json").read_text(encoding="utf-8"))
    assert fx["hero_img"] == "/img/room-b-1002.jpg"
    assert fx["og_image"] == "https://www.nuviestudio.com/img/og-b-1002.jpg"
    assert [g[0] for g in fx["gallery"]] == [g["src"] for g in _room_b()["gallery"]]
    assert [g[1] for g in fx["gallery"]] == [alt for _, _, alt in GALLERY]
