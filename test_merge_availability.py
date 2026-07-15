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
    """앞에 붙을 ≥2h가 없는 고립 <2h(예: 14-15)는 삭제하지 않고 유지(슬롯은 실제 막힘). 라벨완화로 안전."""
    r = merge_events([ev("2026-07-21", 10, 12), ev("2026-07-21", 14, 15)])
    assert spans(r) == [("A", 10.0, 12.0), ("A", 14.0, 15.0)], spans(r)


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
