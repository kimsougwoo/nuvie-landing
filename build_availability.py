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
    """iCal 본문 문자열, 실패 시 None(=구분가능 실패신호).

    ⚠️ 2026-07-17(3R 🔴HIGH): 예전엔 타임아웃/5xx/순단에도 ""를 반환 → parse_events("")=[]
       로 흘러 '진짜 페치 실패'와 '예약 0건'을 구분 못 했다. A룸만 순단해도 꽉 찬 날짜가
       사라져 changed=True→push→Vercel 재배포로 예약된 날이 '가능'으로 공개됐다(둘 다 실패면
       120일 전체 '가능'). 형제 booking_watch.fetch_ical의 None-신호(P0-1)와 정합하도록,
       실패는 None으로 올려 호출부(compute_events)가 그 룸을 이번 런에서 제외하게 한다.
       (성공한 빈 캘린더는 여전히 "" 등 문자열 → 정상 '예약 0건'으로 진행.)"""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nuvie-availability/1.0"})
        return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        print("  fetch 실패:", e)
        return None

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


def _load_old_events(dst):
    """직전 availability.json의 events 리스트(없거나 손상이면 None)."""
    if os.path.exists(dst):
        try:
            return json.load(open(dst, encoding="utf-8")).get("events")
        except Exception:
            pass
    return None


def compute_events(env, today, old_events):
    """iCal 페치 → 최종 events + (fetched_ok, fetch_failed) 카운트.

    ⚠️ 2026-07-17(3R 🔴HIGH): fetch()가 실패하면 None을 준다. **페치 실패 룸은 빈 []로
       덮지 않고 직전 availability.json의 그 룸 값을 그대로 유지**한다 — 안 그러면 A룸 순단만으로
       예약된 날이 사라져 공개 사이트가 '가능'으로 뒤집힌다(둘 다 실패면 120일 전체 '가능').
       두 룸 모두 실패(fetched_ok==0)면 호출부가 push를 스킵한다. 성공한 룸은 신선 반영.
       (성공한 '빈 캘린더'=진짜 예약0은 정상 반영 → 예약 해제가 공개에 반영됨.)"""
    horizon = today + datetime.timedelta(days=120)
    old_events = old_events or []
    events = []
    fetched_ok = fetch_failed = 0
    for key, room in (("ICAL_URL_HOURPLACE", "A"), ("ICAL_URL_HOURPLACE_B", "B")):
        url = env.get(key)
        prev = [e for e in old_events if e.get("room") == room]  # 그 룸 직전값(실패 시 유지)
        if not url:
            print(f"{key} ({room}룸): 없음 — 미설정(직전 {len(prev)}건 유지)")
            events += prev
            continue
        ics = fetch(url)
        if ics is None:
            fetch_failed += 1
            print(f"{key} ({room}룸): 있음 — ❌ FETCH FAIL, 직전 {len(prev)}건 유지(빈값 덮어쓰기 금지)")
            events += prev
        else:
            fetched_ok += 1
            print(f"{key} ({room}룸): 있음 — OK")
            events += parse_events(ics, room)
    # 오늘~120일(미래)만 + 무료연장(2h 미만) 흡수 + 정렬
    events = [e for e in events if today.isoformat() <= e["date"] <= horizon.isoformat()]
    events = merge_events(events)
    events.sort(key=lambda e: (e["date"], e["start"], e["room"]))
    return events, fetched_ok, fetch_failed


def _alert_fetch_fail(msg):
    """두 iCal 모두 실패(예약현황 갱신 불능) 경보 — silent-failure 방지.
    nuvie_morning.report.alert_throttled로 #이상감지 1회(6h 쿨다운). import 불가(단독 실행)·
    웹훅 미설정이면 stdout(=refresh_log.txt)에 남은 FETCH FAIL 로그만으로 폴백(graceful)."""
    try:
        try:
            import nuvie_morning.report as R
        except Exception:
            # 단독 실행(cwd=Projects\nuvie-landing) 시엔 홈(C:\Users\kgr96)이 path에 없음 → 보강 후 재시도
            home = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if home not in sys.path:
                sys.path.insert(0, home)
            import nuvie_morning.report as R
        R.alert_throttled("availability_fetch_down", msg, hours=6)
    except Exception as e:
        print(f"  (경보 전송 스킵 — refresh_log 폴백: {str(e)[:80]})")


def push_changes(repo, n_events):
    """availability.json git add+commit+rebase+push (Vercel 자동 재배포). 반환 pushed:bool."""
    try:
        subprocess.run(["git", "-C", repo, "add", "availability.json"], check=True)
        subprocess.run(["git", "-C", repo,
                        "-c", "user.name=kimsougwoo",
                        "-c", "user.email=143887564+kimsougwoo@users.noreply.github.com",
                        "commit", "-q", "-m", f"예약현황 갱신(자동 30분): 예약 {n_events}건"], check=True)
        # ⚠️ 2026-07-03: push 전 rebase — 외부(수동 히어로 편집·GitHub 웹)로 origin이 앞서도
        # 강제덮어쓰기 없이 availability 커밋을 그 위에 리베이스(split-brain·수동수정 유실 방지).
        # availability.json은 봇 전용이라 index.html 등 수동파일과 충돌 사실상 없음.
        pr = subprocess.run(["git", "-C", repo, "pull", "--rebase", "origin", "main"],
                            capture_output=True, text=True)
        if pr.returncode != 0:
            subprocess.run(["git", "-C", repo, "rebase", "--abort"], capture_output=True)
            # 🔧 2026-07-23: 충돌 자가치유. availability.json은 봇 전용이라, 스톨된 로컬 커밋이
            #   이 파일만 건드렸다면 origin에 맞추고(스냅샷 폐기) 신선본은 다음 30분 런이 재생성한다.
            #   과거엔 abort 후 그냥 return False → 커밋이 영구 적체(ahead 누적)돼 스톨했다.
            #   ⚠️ 다른 파일이 섞였으면 자동 폐기 위험 → 종전대로 보류(수동 확인).
            diff = subprocess.run(["git", "-C", repo, "diff", "--name-only", "origin/main..HEAD"],
                                  capture_output=True, text=True)
            touched = {f.strip() for f in (diff.stdout or "").splitlines() if f.strip()}
            if touched and touched <= {"availability.json"}:
                subprocess.run(["git", "-C", repo, "reset", "--hard", "origin/main"], check=True)
                print("  rebase 충돌 → availability 전용 로컬커밋이라 origin에 맞춤(다음 런 재생성). 스톨 자가치유.")
            else:
                print(f"  rebase 충돌 → push 보류(availability 외 변경 {sorted(touched)} 有, 수동 확인):",
                      (pr.stderr or "")[:150])
            return False
        subprocess.run(["git", "-C", repo, "push", "origin", "main"], check=True)
        print("  변경 감지 → rebase+push 완료 (Vercel 자동 재배포)")
        return True
    except Exception as e:
        print("  push 실패:", e)
        return False


def main(argv=None, repo=None):
    argv = sys.argv if argv is None else argv
    env = load_env(ENV)
    today = datetime.date.today()
    repo = repo or os.path.dirname(os.path.abspath(__file__))
    dst = os.path.join(repo, "availability.json")
    old_events = _load_old_events(dst)

    events, fetched_ok, fetch_failed = compute_events(env, today, old_events)

    if fetched_ok == 0:
        # 신선 페치 0건 → 직전 availability.json을 **그대로 둔다**(빈값 덮어쓰기 = 예약된 날이
        # '가능'으로 공개 배포되는 사고). 파일 미접촉·push 스킵. 페치 실패가 원인이면 #이상감지 경보.
        print(f"  ❌ FETCH FAIL — availability.json 미갱신·push 스킵(직전값 유지, 실패 {fetch_failed})")
        if fetch_failed:
            _alert_fetch_fail(
                f"🔴 예약현황 iCal {fetch_failed}개 전부 페치 실패 — availability.json 갱신 중단"
                "(직전값 유지·공개 사이트 안전). 피드 URL·아워플레이스 점검 필요.")
        return

    busy = sorted({e["date"] for e in events})
    changed = ((old_events or []) != events)
    # 🔧 2026-07-23: 변경이 있을 때만 파일을 쓴다. 종전엔 매 런 `updated` 타임스탬프를 무조건
    #   재기록 → 이벤트 변화가 없어도 워킹트리가 dirty → 다음 런의 `git pull --rebase`가 dirty로
    #   막혀 크론이 스톨했다(라이브 예약현황 8일 고착 사고, 2026-07-23). 변경 시에만 기록.
    if changed:
        out = {
            "updated": datetime.datetime.now().isoformat(timespec="minutes"),
            "note": "free/busy (아워플레이스 iCal · 이름 비노출, 시간·룸만). 참고용 — 확정은 아워플레이스.",
            "events": events,
            "busyDates": busy,
        }
        json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"availability.json {'작성' if changed else '변화없음(미기록)'}: 예약 {len(events)}건 / "
          f"{len(busy)}일 (이름 0개 노출) · 변경={changed} · 페치성공 {fetched_ok}/실패 {fetch_failed}")
    print("  샘플:", events[:4])

    if "--push" in argv:
        if not changed:
            print("  변경 없음 → push 생략")
            # dirty-잔류 방지(멱등): 과거 버그로 남았을 수 있는 타임스탬프-only 오염을 되돌려
            #   다음 런의 pull --rebase가 막히지 않게 한다. 변경 없으니 되돌려도 무손실.
            subprocess.run(["git", "-C", repo, "checkout", "--", "availability.json"],
                           capture_output=True)
            return
        push_changes(repo, len(events))


if __name__ == "__main__":
    main()
