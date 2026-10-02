"""Build the 2026-10-02 B-room photo set from the approved v2 originals.

Only cropping, LANCZOS resizing, and JPEG encoding are applied. The gallery
table is copied from test_b_photos_v2_1002.py so this build stays independent
of the test module.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
V2 = Path(r"F:\무인 렌탈스튜디오 인수\source\촬영_2026-09-29\보정_v2")
V1 = Path(r"F:\무인 렌탈스튜디오 인수\source\촬영_2026-09-29\보정")
HERO_SRC = V2 / "broom_20261001_01.jpg"
HERO_ALT = "B룸 화이트 티타임 카페 — 커피머신 카운터와 레이스 티테이블"
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


def save_jpeg(image: Image.Image, path: Path, quality: int, *, optimize: bool = False, progressive: bool = False) -> None:
    image.save(path, format="JPEG", quality=quality, optimize=optimize, progressive=progressive)


def crop_gallery(src: Path, ax: float) -> Image.Image:
    image = Image.open(src).convert("RGB")
    width, height = image.size
    crop_width = height * 3 // 4
    x0 = int((width - crop_width) * ax)
    return image.crop((x0, 0, x0 + crop_width, height))


def build() -> None:
    images = ROOT / "img"
    assert len(GALLERY) == 11
    for number, (source, ax, _alt) in enumerate(GALLERY, 1):
        cropped = crop_gallery(source, ax)
        large = cropped.resize((825, 1100), Image.LANCZOS)
        small = cropped.resize((800, 1067), Image.LANCZOS)
        large_path = images / f"galB-1002-{number}.jpg"
        quality = 84
        while True:
            save_jpeg(large, large_path, quality=quality, optimize=True, progressive=True)
            if large_path.stat().st_size <= 200_000:
                break
            quality -= 1
            if quality < 78:
                raise ValueError(f"{large_path.name} cannot meet the 200 KB target")
        save_jpeg(small, images / f"galB-1002-{number}-800.jpg", quality=82,
                  optimize=True, progressive=True)

    hero = Image.open(HERO_SRC).convert("RGB")
    for suffix, size, quality in (
        ("", (1600, 1200), 85),
        ("-1200", (1200, 900), 82),
        ("-800", (800, 600), 82),
    ):
        save_jpeg(hero.resize(size, Image.LANCZOS), images / f"room-b-1002{suffix}.jpg", quality=quality)


if __name__ == "__main__":
    build()
