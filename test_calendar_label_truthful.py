# -*- coding: utf-8 -*-
"""예약 달력 시각 문구가 사실과 맞아야 한다 (2026-09-27 캡처 확인).

달력은 availability.json 이 «바뀐» 시각을 보여 준다. 30분 확인은 계속 돌지만 예약이 안 바뀌면 파일을 새로 쓰지 않는다
(push·배포를 매번 만들지 않으려고 — build_availability.py «변경 없음 → push 생략»). 그런데 문구가 «최종 확인 HH:MM» 이라
손님 눈엔 18시간 동안 확인을 안 한 것처럼 보였다(09-27 00:15 표시, 실제 확인은 17:45). 문구를 «마지막 변경» 으로 바로잡는다.
"""
import pathlib

HTML = (pathlib.Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8")


def test_label_says_last_change_not_last_check():
    assert "'최종 확인 '" not in HTML
    assert "'마지막 변경 '" in HTML
