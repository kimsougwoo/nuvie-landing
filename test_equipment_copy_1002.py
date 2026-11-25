# -*- coding: utf-8 -*-
"""랜딩 장비 문장 정정 (2026-10-02 대표 «랜딩 홈·/b 장비 문장 = 고친다», 총괄 중계 · 마케팅팀 요청).

정본 = Desktop\\NUVIE_장비정정안_2026-10-02.md:
  A룸 = 모디파이어 7(스누트 포함) · C스탠드 1 · 붐암 1 · A스탠드 6  →  «스탠드 7대 · 붐암 1개»
  B룸 = A스탠드 5
  유료 = FC-60B 세트 10,000원 · 파보튜브 15C 10,000원(A룸 전용), 브이플랫(양면 화이트/블랙) 5,000원(A·B 둘 다), 모두 대관 1회당·이용 시간과 무관.
  무료 = A룸 지속광 3대 · 순간광 2대(동조기 포함) · 모디파이어 7종 · 스탠드 7대 · 붐암 1개 / B룸 지속광 1대 · 팔각 소프트박스 · 스탠드 5대.
  2026-11-20 대표: 메인 «전부 무료» 자기모순 정정 — 세 면 모두 «비치 조명은 무료입니다 — 목록» + «유료 장비(대관 1회당, 이용 시간과 무관) — 품목별 금액» 같은 문형.
사실 오류라 장비 문장만 고친다(B 표면 동결 중이지만 대표 예외). 장비 외 문장은 그대로.
"""
from pathlib import Path

ROOT = Path(__file__).parent
OLD = ("모디파이어 6종", "스탠드 8대", "유료는 두 가지", "스탠드 4대", "유료 조명 대여는", "개당 10,000원")


def _t(name):
    return (ROOT / name).read_text(encoding="utf-8").replace(" ", " ").replace("⁠", "")


def test_old_equipment_wording_is_gone():
    for name in ("index.html", "a.html", "b.html", "llms.txt", "rooms.json"):
        text = _t(name)
        hits = [o for o in OLD if o in text]
        assert not hits, (name, hits)


def test_hub_room_cards():
    hub = _t("index.html")
    assert ("비치 조명은 무료입니다 —<br>지속광 3대 · 순간광 2대(동조기 포함) · 모디파이어 7종 · 스탠드 7대 · 붐암 1개 · 스모그머신(무료)<br>"
            "유료 장비(대관 1회당, 이용 시간과 무관) —<br>"
            "FC-60B 세트 10,000원 · 파보튜브 15C 10,000원 · 브이플랫(1대·A·B 공용) 5,000원") in hub
    assert ("비치 조명은 무료입니다 —<br>지속광 1대 · 순간광 2대(동조기 포함) · 팔각 소프트박스 · 스탠드 5대<br>"
            "유료 장비(대관 1회당, 이용 시간과 무관) —<br>브이플랫(1대·A·B 공용) 5,000원") in hub


FAQ_NEW = ("유료 장비가 추가될 수 있습니다: A룸 FC-60B 세트·파보튜브 15C 각 10,000원, A·B룸 브이플랫(1대·A·B 공용) 5,000원"
           "(모두 대관 1회당, 이용 시간과 무관). A룸 스모그머신은 무료입니다.")


def test_faq_jsonld_and_body_and_llms():
    hub = _t("index.html")
    assert hub.count(FAQ_NEW) >= 2, "FAQ 구조화 데이터(JSON-LD)와 FAQ 본문 두 곳"
    assert FAQ_NEW in _t("llms.txt")


def test_room_pages_price_note():
    """2026-11-25: 한 문단 몰아쓰기 → 라벨 줄(인원 추가/비치 조명/유료 장비/예약 기준)로 분리."""
    a = _t("a.html")
    for label in ("인원 추가", "비치 조명", "유료 장비", "예약 기준"):
        assert label in a, label
    assert "무료 — 지속광 3대" in a
    assert "순간광 2대(동조기)" in a
    assert "5,500" in a

    b = _t("b.html")
    assert "무료 — 지속광 1대" in b
    assert "FC-60B" not in b and "파보튜브" not in b, "B룸 페이지에 A룸 전용 유료 장비를 적지 않는다"


def test_vflat_on_every_public_surface():
    """브이플랫 5,000원은 네 표면 모두에 남는다 — /a·/b는 유료 카드(사진+금액), 홈·llms는 문장."""
    assert "브이플랫(1대·A·B 공용) 5,000원" in _t("index.html")
    assert "브이플랫(1대·A·B 공용) 5,000원" in _t("llms.txt")
    for name in ("a.html", "b.html"):
        s = _t(name)
        assert "브이플랫" in s, name
        assert "5,000원" in s, name
