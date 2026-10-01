# -*- coding: utf-8 -*-
"""예약 달력 시각 문구가 사실과 맞아야 한다 (2026-09-27 캡처 확인 → 2026-10-02 개정).

09-27: 달력은 availability.json 이 «바뀐» 시각을 보여 줬는데 문구가 «최종 확인» 이라, 예약이 안 바뀌면 손님 눈엔
18시간 동안 확인을 안 한 것처럼 보였다 → 그때는 문구를 «마지막 변경» 으로 바로잡았다.
10-02(총괄 결정, 폴백 점검 우선순위 1-8): 확인 시각을 따로 둔다(availability_checked.json, 예약이 안 바뀌어도 3시간마다
갱신). 이제 달력이 보여 주는 값이 «확인 시각» 이므로 문구는 «마지막 확인» 이 사실이다. «마지막 변경» 은 더 이상
보여 주는 값과 맞지 않는다.
"""
import pathlib

HTML = (pathlib.Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8")


def test_label_says_last_check_and_reads_the_checked_file():
    assert "'최종 확인 '" not in HTML
    assert "'마지막 변경 '" not in HTML
    assert "마지막 확인" in HTML
    assert "availability_checked.json" in HTML
