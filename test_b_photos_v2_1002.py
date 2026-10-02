# -*- coding: utf-8 -*-
"""/b 사진을 B룸 재보정 v2 로 교체(2026-10-02 대표 결정, 총괄 중계 · 마케팅팀 요청).

대표 확인: 11/11 /b 동결의 예외로 «측정이 섞여도 괜찮음». 밝기는 다시 손대지 않는다(대표 확인판) ⇒ 자르기·크기 조정만.
  · 순서 = 대표가 직접 바꾼 아워 B 리스팅(62341) 최종 순서(10-02 10:1x «/b도 맞춰 주세요», 마케팅팀이 공개 페이지·편집폼에서 읽음).
  · 첫 화면(room-b)·og-b = 리스팅 커버 broom_20261001_01 (카운터·커피머신). 가로 4:3 그대로 1600/1200/800.
  · 갤러리 = 리스팅 2~12번 11장(아래 GALLERY 순서). 01 을 갤러리에 한 번 더 넣지 않고 11칸으로 줄인다. 끝 영상(b-table-1001.mp4)은 그대로.
  · 쓰지 않는 사진: 14(대표가 리스팅에서 뺌 — 첫 화면·og 포함 /b 에서도 안 씀)·09(08과 거의 같음)·10(11과 거의 같음). 평면도는 리스팅에만.
  · 가로 사진을 3:4 로 자를 때 가운데 대상이 잘리지 않게 사진마다 가로 위치(ax, 0=왼쪽 끝·1=오른쪽 끝)를 개발팀이 사진을 보고 정했다.
  · 새 파일 이름(-1002) — 캐시된 옛 사진이 새 alt 와 짝지어지지 않게(10-01 교체와 같은 이유).
"""
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).parent
V2 = Path(r"F:\무인 렌탈스튜디오 인수\source\촬영_2026-09-29\보정_v2")
V1 = Path(r"F:\무인 렌탈스튜디오 인수\source\촬영_2026-09-29\보정")

HERO_SRC = V2 / "broom_20261001_01.jpg"
HERO_ALT = "B룸 화이트 티타임 카페 — 커피머신 카운터와 레이스 티테이블"
# (소스, ax, alt) — 순서 = 갤러리 1~11칸 = 리스팅 2~12번
GALLERY = [
    (V1 / "broom_20261001_05.jpg", 0.50, "B룸 카운터 — 디저트 상자와 케이크 진열"),
    (V2 / "broom_20261001_main1.jpg", 0.50, "B룸 전경 — 카운터와 원형 티테이블"),
    (V2 / "broom_20261001_02.jpg", 0.25, "B룸 창가 — 곰인형과 원형 티테이블"),
    (V2 / "broom_20261001_03.jpg", 0.30, "B룸 창가 — 레이스 커튼과 곰인형"),
    (V2 / "broom_20261001_04.jpg", 0.50, "B룸 창가 자리 — 티테이블과 쿠션 의자"),
    (V2 / "broom_20261001_08.jpg", 0.50, "B룸 디저트 스탠드 — 3단 스탠드와 찻잔"),
    (V2 / "broom_20261001_06.jpg", 0.50, "B룸 디저트 — 조각 케이크 근접"),
    (V2 / "broom_20261001_11.jpg", 0.35, "B룸 화장대 — 조명 거울과 의자"),
    (V2 / "broom_20261001_13.jpg", 0.40, "B룸 탈의 공간 — 커튼과 스팀다리미"),
    (V2 / "broom_20261001_15.jpg", 0.50, "B룸 소품 코너 — 스탠드 조명과 화분"),
    (V2 / "broom_20261001_16.jpg", 0.30, "B룸 거울 코너 — 앤티크 거울과 촛대"),
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
    assert [g["src"] for g in gal[:11]] == [f"/img/galB-1002-{i}.jpg" for i in range(1, 12)]
    assert [g["alt"] for g in gal[:11]] == [alt for _, _, alt in GALLERY]
    assert len(gal) == 12 and gal[11].get("video") == "/img/b-table-1001.mp4", "11칸 + 끝 영상(그대로)"


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
    for i in range(1, 12):
        assert f"/img/galB-1002-{i}.jpg" in B, i
    assert "/img/galB-1002-12" not in B, "갤러리는 11칸"
    assert "/img/b-table-1001.mp4" in B
    assert "/img/room-b-1002.jpg" in HUB
    assert "light:{src:'/img/room-b-1002.jpg'" in HUB, "허브 라이트 테마 = 새 B룸 첫 화면"
    slides = re.findall(r'class="mgal-slide"><img[^>]*src="(/img/galB-1002-\d+)\.jpg"', HUB)
    assert slides == ["/img/galB-1002-3", "/img/galB-1002-6"], "허브 모바일 갤러리 B 2·3번째 = 곰인형 창가·디저트 스탠드"
    for alt in re.findall(r'<img[^>]*room-b-1002[^>]*alt="([^"]*)"', B + HUB):
        assert "전경" not in alt, f"첫 화면 사진(01 카운터)은 전경이 아니다: {alt}"


def test_image_files_sizes():
    for i in range(1, 12):
        assert Image.open(ROOT / f"img/galB-1002-{i}.jpg").size == (825, 1100), i
        assert Image.open(ROOT / f"img/galB-1002-{i}-800.jpg").size == (800, 1067), i
    for suf, size in (("", (1600, 1200)), ("-1200", (1200, 900)), ("-800", (800, 600))):
        assert Image.open(ROOT / f"img/room-b-1002{suf}.jpg").size == size, suf
    assert Image.open(ROOT / "img/og-b-1002.jpg").size == (1200, 630)


def test_gallery_pixels_are_the_v2_source_cropped_at_ax_without_retouch():
    """자르기 위치와 «밝기 무보정»을 함께 잠근다: 소스를 ax 로 자른 것과 평균 차이가 작아야 한다."""
    for i, (src, ax, _) in enumerate(GALLERY, 1):
        assert src.exists(), f"원본 없음: {src}"
        out = Image.open(ROOT / f"img/galB-1002-{i}.jpg")
        assert _diff(out, _crop34(src, ax, (825, 1100))) < 4, i
        # 다른 위치로 잘랐다면 차이가 커야 한다(이 검사가 위치를 실제로 구별하는지)
        if ax != 0.5:
            assert _diff(out, _crop34(src, 0.5, (825, 1100))) > _diff(out, _crop34(src, ax, (825, 1100))), i


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
    assert [g[0] for g in fx["gallery"][:11]] == [f"/img/galB-1002-{i}.jpg" for i in range(1, 12)]
    assert [g[1] for g in fx["gallery"][:11]] == [alt for _, _, alt in GALLERY]
