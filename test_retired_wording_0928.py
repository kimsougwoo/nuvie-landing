# -*- coding: utf-8 -*-
"""09-28 대표 결정으로 은퇴한 표현이 저장소에 남지 않게 잠근다.

1) 옛 허브 h1 문구 — 09-28 «내 의도대로 찍는 / 코스프레 스튜디오»로 교체(결정 10).
   index.html 주석도 공개 소스라 «현행 표기»처럼 남아 있으면 안 된다.
2) «휴무» — 결정 3 «휴무는 없습니다. 24시간 365일 운영». 공개 파일 availability.json 의 note 가
   build_availability.py 문자열에서 나오므로 그 문자열을 잠근다.
"""
import os

import build_availability as BA

HERE = os.path.dirname(os.path.abspath(__file__))
OLD_H1 = "남과 " + "겹치지 않는"   # 이 파일 자신이 걸리지 않게 나눠 적는다
TEXT_EXT = (".html", ".py", ".js", ".json", ".txt", ".md", ".css", ".xml")


def _text_files():
    for dirpath, dirnames, filenames in os.walk(HERE):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".vercel", "__pycache__", "node_modules")]
        for f in filenames:
            if f.endswith(TEXT_EXT):
                yield os.path.join(dirpath, f)


def test_old_hub_h1_wording_is_gone():
    hits = []
    for p in _text_files():
        try:
            if OLD_H1 in open(p, encoding="utf-8").read():
                hits.append(os.path.relpath(p, HERE))
        except UnicodeDecodeError:
            continue
    assert not hits, f"옛 h1 문구가 남아 있다: {hits}"


def test_availability_note_has_no_holiday_word():
    src = open(os.path.join(HERE, "build_availability.py"), encoding="utf-8").read()
    start = src.index('"note": (')
    note_src = src[start:src.index('"events": events', start)]
    assert "휴무" not in note_src, note_src
    assert "(청소·점검·답사·본인 사용)" in note_src
