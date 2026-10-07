# -*- coding: utf-8 -*-
"""IndexNow 키 파일(대표 10-08 «IndexNow 로 먼저» — 빙 계정 없이 빙·IndexNow 참여 검색엔진에 주소 알리기).

규약(indexnow.org): 키 = 8~128자 [a-zA-Z0-9-], 사이트 루트 /<키>.txt 에 키 값 그대로(UTF-8).
키는 공개 파일이라 비밀이 아니지만 커밋·문서에는 파일 이름만 적는다.
"""
import pathlib
import re

from test_vercelignore_contract import _ignored, _patterns

HERE = pathlib.Path(__file__).resolve().parent
KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")


def _key_files():
    return [p for p in HERE.glob("*.txt") if KEY_RE.match(p.stem) and p.read_text(encoding="utf-8").strip() == p.stem]


def test_exactly_one_indexnow_key_file_at_root():
    files = _key_files()
    assert len(files) == 1, f"루트 IndexNow 키 파일 수 = {len(files)} (1개여야 한다)"


def test_key_file_holds_only_the_key():
    (f,) = _key_files()
    raw = f.read_bytes()
    assert raw.decode("utf-8") == f.stem, "키 파일 내용 = 키 값만(줄바꿈·BOM 없음)"


def test_key_file_ships_in_deploy():
    (f,) = _key_files()
    assert not _ignored(f.name, _patterns()), ".vercelignore 가 키 파일을 배포에서 빼면 검색엔진이 키를 확인하지 못한다"
