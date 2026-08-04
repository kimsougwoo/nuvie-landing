# -*- coding: utf-8 -*-
"""무료연장(2h 미만) 흡수 병합 재현 테스트.

버그: 무료 추가 1시간이 별도 iCal 이벤트라 예약현황에 "(1H) 예약됨"으로 떠서
      최소 2시간 정책과 충돌 → 손님이 "1시간만 예약되나요?" 오해(2026-07-15 대표 보고, 실사례 7/17).
규칙: <2h 블록은 무조건 무료연장(실예약 불가) → 바로 앞 ≥2h 블록에 뒤로 흡수.
      ≥2h 블록끼리는 병합 안 함(다른 게스트 분리 유지 — 게스트 리마인드용).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_availability import merge_events


def ev(date, s, e, room="A"):
    return {"date": date, "start": float(s), "end": float(e), "room": room}


def spans(res):
    return [(e["room"], e["start"], e["end"]) for e in res]


def test_real_0717():
    """실사례 7/17: 유료 10-12 + 무료 12-13 + 별도 유료 15-17 → 10-13, 15-17."""
    r = merge_events([ev("2026-07-17", 10, 12), ev("2026-07-17", 12, 13), ev("2026-07-17", 15, 17)])
    assert spans(r) == [("A", 10.0, 13.0), ("A", 15.0, 17.0)], spans(r)


def test_free_between_two_guests():
    """A유료10-12 + A무료12-13 + B유료13-15: 1h는 앞 A에만 흡수, B는 분리."""
    r = merge_events([ev("2026-07-18", 10, 12), ev("2026-07-18", 12, 13), ev("2026-07-18", 13, 15)])
    assert spans(r) == [("A", 10.0, 13.0), ("A", 13.0, 15.0)], spans(r)


def test_two_paid_backtoback_not_merged():
    """다른 게스트 2h+2h 등맞댐(10-12, 12-14): 절대 병합 안 함."""
    r = merge_events([ev("2026-07-19", 10, 12), ev("2026-07-19", 12, 14)])
    assert spans(r) == [("A", 10.0, 12.0), ("A", 12.0, 14.0)], spans(r)


def test_chained_free_hours():
    """유료 10-12 + 무료 12-13 + 무료 13-14 → 10-14 체인 흡수."""
    r = merge_events([ev("2026-07-20", 10, 12), ev("2026-07-20", 12, 13), ev("2026-07-20", 13, 14)])
    assert spans(r) == [("A", 10.0, 14.0)], spans(r)


def test_isolated_short_kept():
    """앞뒤 어디에도 붙을 ≥2h가 없는 고립 <2h(예: 14-15)는 삭제하지 않고 유지(슬롯은 실제 막힘)."""
    r = merge_events([ev("2026-07-21", 10, 12), ev("2026-07-21", 14, 15)])
    assert spans(r) == [("A", 10.0, 12.0), ("A", 14.0, 15.0)], spans(r)


# ── 2026-08-04 재현: 무료 1h 가 예약 '앞'에 붙는 사례 ──────────────────
# 07-15 규칙은 "무료 1h 는 항상 ≥2h 블록 '뒤'에만 붙는다"를 전제로 뒤흡수만 구현했다.
# 대표 보고(2026-08-04) = "앞으로 한시간이 붙는 사례가 발생". 라이브 실측으로 확인:
#   2026-08-23 B룸  14-15(1h) | 15-18(3h)   ← 1h 가 앞에 붙어 흡수 안 되고 따로 떴다
# 결과적으로 없애려던 "(1H) 예약됨" 오해가 그대로 재발한다.

def test_repro_free_hour_in_front_is_absorbed():
    """🔴 재현: 무료 1h(14-15)가 유료 3h(15-18) '앞'에 붙으면 한 블록(14-18)이어야 한다."""
    r = merge_events([ev("2026-08-23", 14, 15, "B"), ev("2026-08-23", 15, 18, "B")])
    assert spans(r) == [("B", 14.0, 18.0)], spans(r)


def test_free_hour_front_chained():
    """앞 무료가 2칸(13-14,14-15) 이어져도 뒤 유료(15-18)에 통째로 흡수 → 13-18."""
    r = merge_events([ev("2026-08-24", 13, 14), ev("2026-08-24", 14, 15), ev("2026-08-24", 15, 18)])
    assert spans(r) == [("A", 13.0, 18.0)], spans(r)


def test_rear_absorption_wins_over_front():
    """앞뒤 양쪽에 ≥2h 가 맞닿은 <2h(10-12, 12-13, 13-15)는 기존대로 '앞'에 흡수(뒤흡수 우선).
    기존 test_free_between_two_guests 와 같은 판정 — 앞흡수 도입으로 뒤집히면 안 된다."""
    r = merge_events([ev("2026-08-25", 10, 12), ev("2026-08-25", 12, 13), ev("2026-08-25", 13, 15)])
    assert spans(r) == [("A", 10.0, 13.0), ("A", 13.0, 15.0)], spans(r)


def test_front_absorption_does_not_cross_rooms():
    """앞흡수도 룸 경계를 넘지 않는다(B 14-15 는 A 15-18 에 붙지 않는다)."""
    r = merge_events([ev("2026-08-26", 14, 15, "B"), ev("2026-08-26", 15, 18, "A")])
    assert spans(r) == [("B", 14.0, 15.0), ("A", 15.0, 18.0)], spans(r)  # 출력은 시작시각 순


def test_front_absorption_requires_contiguity():
    """떨어져 있으면(13-14 … 15-18) 앞흡수 안 함 — 빈 1시간은 실제로 예약 가능한 시간이다."""
    r = merge_events([ev("2026-08-27", 13, 14), ev("2026-08-27", 15, 18)])
    assert spans(r) == [("A", 13.0, 14.0), ("A", 15.0, 18.0)], spans(r)


def test_different_rooms_not_merged():
    """같은 시각이라도 A/B 다른 룸은 별개."""
    r = merge_events([ev("2026-07-22", 10, 12, "A"), ev("2026-07-22", 12, 13, "B")])
    assert spans(r) == [("A", 10.0, 12.0), ("B", 12.0, 13.0)], spans(r)


def test_fullday_block_kept():
    """종일 차단(0-24)은 ≥2h라 anchor로 유지."""
    r = merge_events([ev("2026-07-23", 0, 24)])
    assert spans(r) == [("A", 0.0, 24.0)], spans(r)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}  ->  {e}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
