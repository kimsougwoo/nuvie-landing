# nuvie-landing

누비 스튜디오(NUVIE STUDIO) 랜딩 페이지 — 코스프레 컨셉 렌탈 스튜디오.

- 정적 1페이지(빌드 불필요). 예약은 아워플레이스로 외부 링크.
- AEO: llms.txt + JSON-LD(LocalBusiness·FAQPage) + OG/Twitter meta.
- 예약현황 캘린더: `/availability.json`(free/busy, 이름 비노출) — Windows Task Scheduler `NUVIE_CS_Watch`가 30분마다 `아워플레이스 iCal → build_availability.py → GitHub → Vercel`로 갱신.
- 배포: Vercel (도메인 nuviestudio.com).

## 확인/교체 필요
- index.html `HOURPLACE_URL` (현재 place 61823 추정 — 실제 예약 URL 확인)
- og.jpg (대표 OG 이미지), 갤러리 사진
- Instagram 핸들(@nuvie_studio 가정)
