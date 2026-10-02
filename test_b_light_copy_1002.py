# -*- coding: utf-8 -*-
"""B룸 빛 문구 — 고정 시각을 빼고 «조명으로 언제든 밝게 + 오후엔 서향 햇빛»으로 (2026-10-02 대표 결정 안 2, 마케팅팀 요청).

원칙(대표 10-02): 대외 문구에 고정 시각(오후 5시·3시)을 박지 않는다. 햇빛이 드는 시각은 계절마다 달라지고,
그 전 시간은 상시등·비치 조명으로 찍는다. 근거 = Desktop\\NUVIE_마케팅_업무체계_2026-10-01\\B룸_서향문구_선택지_1002.md(안 2).
11/11 /b 동결의 예외(대표 결정) ⇒ 동결 픽스처의 description·about 도 새 문구로 다시 뽑는다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SURFACES = ("b.html", "index.html", "llms.txt", "rooms.json")
# 빛 시간대 표현만 잡는다. 도어락 안내 «0시~8시 59분에 시작하는 예약» 같은 예약 시각 안내는 대상이 아니다(10-02 첫 판이 넓어
# Codex 가 손님 안내 문구를 바꿨다 → 되돌리고 좁힘).
FIXED_TIME = re.compile(r"오후\s*\d+\s*시|\d+\s*시\s*부터|\d+\s*시\s*~\s*노을|골든")

HERO_NEW = ("상시등과 비치 조명으로 시간과 상관없이 밝게 찍을 수 있습니다. 오후에는 서향 통창으로 햇빛이 들어와 "
            "노을까지 따뜻한 빛을 더합니다. 햇빛이 드는 시각은 계절마다 달라집니다.")
BLOCK_NEW = "오후에는 서향 통창으로 햇빛이 깊게 들어옵니다. 그 전에는 상시등과 비치 조명으로 밝게 찍을 수 있어요."
META_NEW = "조명으로 언제든 밝게, 오후엔 서향 햇빛까지 드는 화이트 톤 공간. 티세트·앤티크 소품, 파우더룸."
HUB_NEW = "조명으로 언제든 밝게, 오후엔 서향 햇빛까지 드는 화이트 톤 공간."
LLMS_NEW = "자연광 공간(서향, 오후 햇빛 · 그 전은 상시등·조명)"


def _read(name):
    return (ROOT / name).read_text(encoding="utf-8").replace(" ", " ").replace("⁠", "")


def test_no_fixed_time_on_public_surfaces():
    for name in SURFACES:
        hits = FIXED_TIME.findall(_read(name))
        assert not hits, f"{name}: {hits}"


def test_b_page_has_new_copy_everywhere():
    B = _read("b.html")
    assert HERO_NEW in B
    assert BLOCK_NEW in B
    assert B.count(META_NEW) >= 4, "meta description · og · twitter · JSON-LD 네 곳"


def test_rooms_json_is_the_source():
    rooms = json.loads((ROOT / "rooms.json").read_text(encoding="utf-8"))
    b = next(r for r in rooms["rooms"] if r["slug"] == "b")
    assert b["seo"]["description"].startswith(META_NEW)
    assert b["hero"]["sub"].startswith(HERO_NEW + "<br>")
    light = next(x for x in b["blocks"] if x["head"] == "자연광")
    assert light["body"].startswith(BLOCK_NEW + "<br>")


def test_hub_and_llms():
    assert HUB_NEW in _read("index.html")
    assert LLMS_NEW in _read("llms.txt")


def test_freeze_fixture_follows_the_exception():
    fx = json.loads((ROOT / "test_b_copy_fixture.json").read_text(encoding="utf-8"))
    assert fx["description"].startswith(META_NEW)
    assert BLOCK_NEW in fx["about"] and not FIXED_TIME.search(fx["about"])


def test_font_subset_covers_new_copy():
    chars = (ROOT / "fonts" / "chars.txt").read_text(encoding="utf-8")
    missing = sorted({c for c in HERO_NEW + BLOCK_NEW + HUB_NEW if c.strip() and c not in chars})
    assert not missing, missing
