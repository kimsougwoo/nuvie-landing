# -*- coding: utf-8 -*-
"""
아워플레이스 iCal → availability.json (free/busy, 이름 비노출)
- iCal URL은 F:\무인 렌탈스튜디오 인수\.env 에서만 읽음(공개레포에 URL·이름 안 나감).
- A룸·B룸 iCal의 예약 '날짜'만 추출(이름·시각·UID 전부 버림) → busyDates.
- 갱신: 이 스크립트 재실행 후 git push (또는 야간 엔진에 hook).
사용:  python build_availability.py
"""
import os, re, json, datetime, urllib.request

ENV = r"F:\무인 렌탈스튜디오 인수\.env"

def load_env(path):
    d = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d

def fetch(url):
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nuvie-availability/1.0"})
        return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        print("  fetch 실패:", e)
        return ""

def parse_dates(ics):
    """VEVENT의 DTSTART~DTEND 사이 모든 날짜(KST 기준)를 set으로. 이름/시각/UID 무시."""
    busy = set()
    # 라인 폴딩 해제
    ics = ics.replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "")
    for ev in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S):
        ds = re.search(r"DTSTART[^:]*:([0-9T]+Z?)", ev)
        de = re.search(r"DTEND[^:]*:([0-9T]+Z?)", ev)
        if not ds:
            continue
        def to_dt(s):
            s = s.strip()
            if "T" in s:
                base = datetime.datetime.strptime(s[:15], "%Y%m%dT%H%M%S")
                if s.endswith("Z"):
                    base += datetime.timedelta(hours=9)  # UTC → KST
                return base
            return datetime.datetime.strptime(s[:8], "%Y%m%d")
        try:
            start = to_dt(ds.group(1))
            end = to_dt(de.group(1)) if de else start
        except Exception:
            continue
        d = start.date()
        last = end.date()
        # DTEND가 exclusive(자정)면 하루 빼기
        if de and "T" not in de.group(1) and last > d:
            last -= datetime.timedelta(days=1)
        while d <= last:
            busy.add(d.isoformat())
            d += datetime.timedelta(days=1)
    return busy

def main():
    env = load_env(ENV)
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=120)
    busy = set()
    for key in ("ICAL_URL_HOURPLACE", "ICAL_URL_HOURPLACE_B"):
        url = env.get(key)
        print(f"{key}: {'있음' if url else '없음'}")
        if url:
            busy |= parse_dates(fetch(url))
    # 오늘~120일만(미래)
    busy = sorted(d for d in busy if today.isoformat() <= d <= horizon.isoformat())
    out = {
        "updated": datetime.datetime.now().isoformat(timespec="minutes"),
        "note": "free/busy (아워플레이스 iCal, 이름 비노출). 참고용 — 확정은 아워플레이스.",
        "busyDates": busy,
    }
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "availability.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"availability.json 작성: 예약일 {len(busy)}건 (이름 0개 노출)")
    print("  샘플:", busy[:8])

if __name__ == "__main__":
    main()
