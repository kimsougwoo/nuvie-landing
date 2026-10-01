# -*- coding: utf-8 -*-
"""비치 천의 길이·«마» 단위·수량은 공개 표면에 쓰지 않는다(2026-10-01 대표 «마 단위와 길이는 노출시키지 마세요»).

쓸 수 있는 것 = «비치 천이 있다»와 색·재질까지. 블랙 호리존(4M × 2.5M × 2.3M) 같은 «공간» 치수와 역 거리(594m)는 해당 없음.
정본 재고는 노션 «🧵 비치 천·소품 재고»(내부 전용).
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC = ["index.html", "a.html", "b.html", "404.html", "privacy.html", "llms.txt",
          "rooms.json", "rooms.data.js", "site.js", "avail-label.js", "room.template.html"]

# «3마»·«2.5 마»·«10야드»·«천 … 5m/롤/필» — 숫자 뒤 «마»(다른 한글이 바로 이어지지 않을 때)
UNIT = re.compile(r"\d+(?:\.\d+)?[  ]?마(?![가-힣])|\d+(?:\.\d+)?[  ]?(?:야드|yd)\b")
FABRIC_LEN = re.compile(r"천[^<\n]{0,15}?\d+(?:\.\d+)?[  ]?(?:m|M|미터|cm|롤|필)\b")


def _visible(text):
    return re.sub(r"(?s)<!--.*?-->", "", text)   # 주석은 배포본에서 빠진다(build_dist.mjs)


def test_no_fabric_length_or_ma_unit_on_public_surfaces():
    hits = []
    for name in PUBLIC:
        p = HERE / name
        if not p.exists():
            continue
        s = _visible(p.read_text(encoding="utf-8"))
        for rx in (UNIT, FABRIC_LEN):
            for m in rx.finditer(s):
                hits.append(f"{name}: …{s[max(0, m.start() - 20):m.end() + 10]}…")
    assert not hits, "천 길이·«마» 단위가 공개 표면에 있다(대표 10-01 금지):\n" + "\n".join(hits[:10])


def test_guard_actually_catches_examples():
    for bad in ("검정 벨벳 천 3마", "광목 2.5 마 비치", "시폰 10야드", "천은 5m 롤로"):
        assert UNIT.search(bad) or FABRIC_LEN.search(bad), bad
    for ok in ("블랙 호리존(4M × 2.5M × 2.3M)", "도보 약 10분(594m)", "소품과 천을 넉넉히 갖춰 두었어요.", "마음에 드는 천"):
        assert not (UNIT.search(ok) or FABRIC_LEN.search(ok)), ok
