# -*- coding: utf-8 -*-
"""🔒 이 레포는 «공개»다 — 캘린더 주소·ID 가 커밋되면 안 된다 (2026-08-16 신설).

## 왜 (실측 배경)
2026-08-16 에 「휴무·차단」 구글캘린더 2개를 `build_availability` 가 읽도록 배선했다.
그 캘린더는 **공개(public) 설정**이라 주소만 알면 누구나 열 수 있고,
**제목·설명에 고객명·핸들·금액·내부 메모가 들어 있다**(실측: 「단골 추가이용권 1h — OOO(@…) 뒷타임」).
⇒ 주소를 이 레포에 적는 순간 그게 곧 유출 경로가 된다. 그래서 `.env` 에서만 읽는다.

같은 날 전수 확인 결과 **현재 공개 노출은 없다**(이 레포 추적파일 매치 0 · 나머지 두 레포는 비공개).
이 테스트는 그 상태를 **고정**한다 — 나중에 누가 "그냥 URL 박아넣지 뭐" 하는 순간 빨간불이 뜬다.
인스턴스가 아니라 클래스를 막는다(아워플레이스 iCal 주소도 같은 이유로 함께 막는다).

## 함정 (2026-08-12 교훈)
소스를 문자열로 검사하는 테스트는 **자기 자신에 걸린다.** 그래서 ①패턴을 조각으로 만들어 쓰고
②스캔 대상에서 이 파일을 제외한다.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
SELF = Path(__file__).name

# 조각 결합 — 이 파일 안에 완성형 문자열이 남지 않게 한다(자기 매치 방지).
_GCAL = "calendar" + ".google.com/calendar/ical/"
_GROUP = "@" + "group.calendar.google.com"
_IMPORT = "@" + "import.calendar.google.com"
_HEX64 = re.compile(r"\b[0-9a-f]{64}\b")

# 텍스트로 볼 확장자만(이미지·폰트 제외). 확장자 없는 파일도 본다.
_BINARY_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".woff", ".woff2",
               ".ttf", ".otf", ".pdf", ".zip", ".mp4", ".mov"}


def _tracked_files():
    """git 이 «실제로 추적하는» 파일만 본다 — 로컬 산출물·gitignore 대상은 공개되지 않는다."""
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert out.returncode == 0, f"git ls-files 실패: {out.stderr[:200]}"
    for line in out.stdout.splitlines():
        name = line.strip()
        if not name or name == SELF:
            continue
        p = ROOT / name
        if p.suffix.lower() in _BINARY_EXT or not p.is_file():
            continue
        yield name, p


def _read(p):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def test_no_google_calendar_url_committed():
    """구글 캘린더 iCal 주소가 커밋되면 안 된다 — 주소 = 그 캘린더 전문 열람권."""
    bad = [n for n, p in _tracked_files() if _GCAL in _read(p)]
    assert not bad, f"공개 레포에 구글캘린더 iCal 주소가 있다: {bad}"


def test_no_calendar_id_committed():
    """주소 형태가 아니어도 캘린더 ID 만으로 열 수 있다 — ID 자체를 막는다."""
    bad = [n for n, p in _tracked_files()
           if _GROUP in (t := _read(p)) or _IMPORT in t]
    assert not bad, f"공개 레포에 캘린더 ID 가 있다: {bad}"


def test_no_bare_64hex_secret_committed():
    """캘린더 ID 는 64자 hex 다 — 도메인 없이 값만 적어도 새는 건 같다."""
    bad = []
    for n, p in _tracked_files():
        if _HEX64.search(_read(p)):
            bad.append(n)
    assert not bad, f"공개 레포에 64자 hex 비밀값으로 보이는 문자열이 있다: {bad}"


def test_block_feed_urls_come_from_env_only():
    """배선이 «env 경유»인 것을 고정 — 나중에 상수로 바꾸면 위 검사만으론 늦다."""
    src = (ROOT / "build_availability.py").read_text(encoding="utf-8")
    for key in ("ICAL_URL_BLOCK_A", "ICAL_URL_BLOCK_B"):
        assert key in src, f"{key} 배선이 사라졌다"
    assert _GCAL not in src, "build_availability.py 에 캘린더 주소가 하드코딩됐다"


def test_availability_json_has_no_text_fields():
    """🔒 산출물 계약 — 시각·룸·종류만. 필드가 늘면 개인정보가 실릴 자리가 생긴다."""
    import json
    data = json.loads((ROOT / "availability.json").read_text(encoding="utf-8"))
    allowed = {"date", "start", "end", "room", "kind"}
    for e in data.get("events") or []:
        assert set(e) <= allowed, f"허용되지 않은 필드: {set(e) - allowed}"
