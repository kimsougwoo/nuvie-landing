# -*- coding: utf-8 -*-
"""
아워플레이스 iCal → availability.json (free/busy, 이름 비노출)
- iCal URL은 F:\무인 렌탈스튜디오 인수\.env 에서만 읽음(공개레포에 URL·이름 안 나감).
- A룸·B룸 iCal에서 예약 '날짜·시각·룸'만 추출(이름·UID·SUMMARY 전부 버림).
- 출력: events[{date,start,end,room}] (시간슬롯 "예약됨" 표시용) + busyDates(날짜만, 호환).
- 갱신: 이 스크립트 재실행 후 git push. 30분 스케줄=NUVIE_CS_Watch(run_cs_watch.bat 1번째 줄).
사용:  python build_availability.py            # 생성만
       python build_availability.py --push     # 변경 시에만 git commit+push (30분 스케줄용)
"""
import os, re, json, datetime, urllib.request, subprocess, sys

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

def _to_dt(s):
    s = s.strip()
    if "T" in s:
        base = datetime.datetime.strptime(s[:15], "%Y%m%dT%H%M%S")
        if s.endswith("Z"):
            base += datetime.timedelta(hours=9)  # UTC → KST
        return base
    return datetime.datetime.strptime(s[:8], "%Y%m%d")

def parse_events(ics, room):
    """VEVENT → [{date,start,end,room}] (KST, 시각 hour 소수). 이름/UID/SUMMARY 무시."""
    out = []
    ics = ics.replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "")
    for ev in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S):
        ds = re.search(r"DTSTART[^:]*:([0-9T]+Z?)", ev)
        de = re.search(r"DTEND[^:]*:([0-9T]+Z?)", ev)
        if not ds:
            continue
        try:
            start = _to_dt(ds.group(1))
            end = _to_dt(de.group(1)) if de else start
        except Exception:
            continue
        timed = "T" in ds.group(1)
        if timed:
            # 같은 날 시간슬롯 (자정 넘기는 예약은 드묾 → 시작일 기준 클립)
            sh = start.hour + start.minute / 60.0
            if end.date() == start.date():
                eh = end.hour + end.minute / 60.0
            else:
                eh = 24.0
            out.append({"date": start.date().isoformat(), "start": round(sh, 2),
                        "end": round(eh, 2), "room": room})
        else:
            # 종일(날짜만) 예약 — 시각 없는 차단. start~end-1 각 날을 0~24 블록으로.
            d = start.date()
            last = end.date()
            # ⚠️ 2026-07-07(P2): DTEND 부재(de=None) 시 de.group()이 NoneType 크래시 → parse_events 전체 정지
            #   (availability.json 무음 미갱신). end=start 방어와 정합하도록 de None 가드. 종일 exclusive-end만 -1일.
            if de and "T" not in de.group(1) and last > d:
                last -= datetime.timedelta(days=1)
            while d <= last:
                out.append({"date": d.isoformat(), "start": 0, "end": 24, "room": room})
                d += datetime.timedelta(days=1)
    return out

MIN_BOOK_H = 2.0  # 최소 대여 2시간(운영정책). 2h 미만 블록 = 실예약 불가 → 무료연장/호의시간.

def merge_events(events):
    """무료 추가시간(2h 미만) 블록을 '바로 앞' 유료 블록에 흡수해 하나의 예약 블록으로 합친다.

    규칙(대표 확정 2026-07-15):
    - 최소 대여가 2시간이므로 **2h 미만 블록은 실예약일 수 없다 = 무료연장/호의시간**.
    - 무료 1h는 항상 **≥2h 블록 '뒤'에만** 붙는다 → 그 1h는 바로 앞 예약의 게스트 것.
    - 따라서 <2h 블록은 직전(맞닿은) 구간에 뒤로 흡수한다.
    - **≥2h 블록끼리는 절대 병합하지 않는다**(다른 게스트가 등을 맞대도 각자 분리 유지 —
      게스트가 홈페이지 예약현황을 '내 예약 리마인드'로 봐도 옆 예약과 안 섞이게).

    이렇게 하면 무료연장이 별도 "(1H) 예약됨"으로 뜨지 않아 "1시간만 예약되나요?" 오해가 사라지고,
    게스트는 자기 전체 이용시간(유료+무료)을 한 블록으로 확인한다. iCal에 이름이 없어도
    '2h 미만 = 무료연장'이 게스트 신원 프록시가 되어 이름 없이 정확히 동작한다.
    """
    from collections import defaultdict
    EPS = 1e-6
    groups = defaultdict(list)
    for e in events:
        groups[(e["date"], e["room"])].append(e)
    out = []
    for (date, room), evs in groups.items():
        evs.sort(key=lambda e: (e["start"], e["end"]))
        cur = None
        for e in evs:
            dur = e["end"] - e["start"]
            if cur is not None and e["start"] <= cur["end"] + EPS and dur < MIN_BOOK_H - EPS:
                # <2h(무료연장) + 앞 구간과 맞닿음 → 뒤로 흡수(직전 예약 확장)
                cur["end"] = max(cur["end"], e["end"])
                continue
            # 그 외(≥2h 블록, 또는 앞과 떨어진 블록)는 새 구간으로 — ≥2h끼리는 병합 안 함
            cur = {"date": date, "start": e["start"], "end": round(e["end"], 2), "room": room}
            out.append(cur)
    out.sort(key=lambda e: (e["date"], e["start"], e["room"]))
    return out


def main():
    env = load_env(ENV)
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=120)
    events = []
    for key, room in (("ICAL_URL_HOURPLACE", "A"), ("ICAL_URL_HOURPLACE_B", "B")):
        url = env.get(key)
        print(f"{key} ({room}룸): {'있음' if url else '없음'}")
        if url:
            events += parse_events(fetch(url), room)
    # 오늘~120일(미래)만 + 정렬
    events = [e for e in events if today.isoformat() <= e["date"] <= horizon.isoformat()]
    events = merge_events(events)  # 무료연장(2h 미만) 흡수 — "(1H) 예약됨" 오해 제거
    events.sort(key=lambda e: (e["date"], e["start"], e["room"]))
    busy = sorted({e["date"] for e in events})
    out = {
        "updated": datetime.datetime.now().isoformat(timespec="minutes"),
        "note": "free/busy (아워플레이스 iCal · 이름 비노출, 시간·룸만). 참고용 — 확정은 아워플레이스.",
        "events": events,
        "busyDates": busy,
    }
    repo = os.path.dirname(os.path.abspath(__file__))
    dst = os.path.join(repo, "availability.json")
    # 변경 비교: events가 다를 때만 의미있는 갱신
    old_events = None
    if os.path.exists(dst):
        try:
            old_events = json.load(open(dst, encoding="utf-8")).get("events")
        except Exception:
            pass
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    changed = (old_events != events)
    print(f"availability.json 작성: 예약 {len(events)}건 / {len(busy)}일 (이름 0개 노출) · 변경={changed}")
    print("  샘플:", events[:4])

    if "--push" in sys.argv:
        if not changed:
            print("  변경 없음 → push 생략")
            return
        try:
            subprocess.run(["git", "-C", repo, "add", "availability.json"], check=True)
            subprocess.run(["git", "-C", repo,
                            "-c", "user.name=kimsougwoo",
                            "-c", "user.email=143887564+kimsougwoo@users.noreply.github.com",
                            "commit", "-q", "-m", f"예약현황 갱신(자동 30분): 예약 {len(events)}건"], check=True)
            # ⚠️ 2026-07-03: push 전 rebase — 외부(수동 히어로 편집·GitHub 웹)로 origin이 앞서도
            # 강제덮어쓰기 없이 availability 커밋을 그 위에 리베이스(split-brain·수동수정 유실 방지).
            # availability.json은 봇 전용이라 index.html 등 수동파일과 충돌 사실상 없음.
            pr = subprocess.run(["git", "-C", repo, "pull", "--rebase", "origin", "main"],
                                capture_output=True, text=True)
            if pr.returncode != 0:
                subprocess.run(["git", "-C", repo, "rebase", "--abort"], capture_output=True)
                print("  rebase 충돌 → push 보류(수동 확인 필요):", (pr.stderr or "")[:200])
                return
            subprocess.run(["git", "-C", repo, "push", "origin", "main"], check=True)
            print("  변경 감지 → rebase+push 완료 (Vercel 자동 재배포)")
        except Exception as e:
            print("  push 실패:", e)

if __name__ == "__main__":
    main()
