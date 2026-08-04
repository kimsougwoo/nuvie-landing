# -*- coding: utf-8 -*-
"""후기 인용 verbatim 회귀 테스트 (2026-08-05 신설).

배경: 검사가 없어서 **개작·스플라이스 6건이 라이브에 떠 있었다.**
  · "빠방하구" → "빵빵하고" (게스트 말투를 우리가 고침)
  · 원문 문장을 요약·어미 변경해 다시 씀
  · 🔴 **스플라이스** — 원문 앞·뒤를 붙여 한 문장처럼 보이게 하고, 그 사이의 불만 2건
       (스모그머신 요청 · 쇼파가 딱딱해 아팠다)을 **흔적 없이 삭제**
  같은 결함이 발행함 캡션·Figma 카드·JSON-LD·정본 md 까지 **4개 표면에 복제**돼 있었다.

⇒ 인스턴스가 아니라 **클래스**를 막는다: reviews.json 이 바뀔 때마다 원문 스냅샷과 대조한다.
"""
import json
from pathlib import Path

import build_reviews as B

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "reviews.json").read_text(encoding="utf-8"))
ORIG = json.loads((ROOT / "reviews_originals.json").read_text(encoding="utf-8"))


def test_originals_snapshot_exists_and_matches_count():
    """원문 스냅샷이 없으면 검사 자체가 무력화된다 — 존재를 강제한다."""
    assert (ROOT / "reviews_originals.json").exists()
    assert len(ORIG["reviews"]) >= len(DATA["reviews"]), \
        "원문 스냅샷이 사이트 후기보다 적다 — 스크래퍼로 재생성할 것"


def test_every_published_quote_is_verbatim():
    """사이트에 실린 모든 후기가 원문의 연속 구간이고 문장 경계에서 시작해야 한다."""
    bad = B.verify_verbatim(DATA, ORIG)
    assert not bad, "verbatim 위반:\n" + "\n".join(f"  {n}: {w} — {q}" for n, w, q in bad)


def test_detector_catches_a_splice():
    """탐지기가 실제로 스플라이스를 잡는지 — 검사 자체를 검사한다.

    (오늘 실제로 있었던 «휘» 후기의 이어붙임을 그대로 재현한다.)
    """
    spliced = {"reviews": [{
        "name": "휘",
        "text": "스튜디오 이쁘고 소품도 다양해서 좋습니다! 동양풍 스튜디오 많이 없어서 아쉬웠는데 "
                "가까운곳에 생겨서 너무 좋아요. 넓어서 두 명도 충분히 들어가고 좋았어욤~ 재방문의사 있습니다",
    }]}
    bad = B.verify_verbatim(spliced, ORIG)
    assert bad, "스플라이스를 못 잡는다 — 탐지기가 무력하다"
    assert "원문에 없음" in bad[0][1]


def test_detector_catches_midsentence_start():
    """문장 중간에서 시작하는 발췌(오늘 카드·캡션 결함)도 잡아야 한다."""
    mid = {"reviews": [{
        "name": "ctebdgvrf",
        "text": "기물이나 조명, 삼각대 모두 넉넉해서 편하게 촬영했어요! 에어컨 빠방하구 탈의실도 시원해서 좋았습니다~",
    }]}
    bad = B.verify_verbatim(mid, ORIG)
    assert bad and "문장 중간" in bad[0][1], "문장 중간 시작을 못 잡는다"


def test_marked_truncation_is_allowed():
    """«…» 로 표시한 잘림은 정직한 발췌라 통과해야 한다(과잉 차단 방지)."""
    ok = {"reviews": [{
        "name": "휘",
        "text": "스튜디오 이쁘고 소품도 다양해서 좋습니다! 동양풍 스튜디오 많이 없어서 아쉬웠는데 가까운곳에 생겨서 너무 좋아요…",
    }]}
    assert not B.verify_verbatim(ok, ORIG)


def test_jsonld_bodies_are_derived_not_handwritten():
    """JSON-LD reviewBody 는 구글 리치결과로 나가는 외부 표면이라 손으로 적으면 드리프트한다."""
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    synced = B.sync_jsonld_reviews(html, DATA)
    assert synced == html, "JSON-LD reviewBody 가 reviews.json 과 어긋난다 — build_reviews.py 를 돌릴 것"
