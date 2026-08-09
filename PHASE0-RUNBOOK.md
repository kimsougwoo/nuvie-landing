# 자사몰 전환 Phase 0 실행 기록

## 이번 단계의 완료 조건

- 자사몰 유입의 first-touch/last-touch UTM이 브라우저별로 보존된다.
- 기존 `book_click`, `ad_capture`, Meta `Lead` 정의를 변경하지 않고 예약 의도를 별도 이벤트로 측정한다.
- 관심 접수는 개인정보처리방침 동의를 요구하고, 연락처를 GA4·Clarity·Meta 이벤트로 보내지 않는다.
- 동의한 접수만 Notion `자사몰 관심·동의 CRM` 데이터 소스에 기록할 수 있다.
- Notion/Vercel 환경변수가 없으면 접수 API가 성공으로 가장하지 않고 `503`을 반환한다.

## Vercel 환경변수

Vercel Production과 Preview에 아래 값을 별도로 설정한다.

| 변수 | 값 | 비고 |
|---|---|---|
| `NOTION_TOKEN` | Notion internal integration secret | 저장소·HTML·로그에 기록하지 않는다 |
| `NOTION_CRM_DATA_SOURCE_ID` | `126a6be4-db22-4e2f-9f9a-7019cc035154` | `자사몰 관심·동의 CRM` 데이터 소스 |
| `NUVIE_SITE_ORIGIN` | `https://www.nuviestudio.com` | CORS 허용 원본 |
| `NOTION_VERSION` | `2025-09-03` | data source parent 사용 |

Notion integration에는 `자사몰 관심·동의 CRM` 데이터베이스에 대한 페이지 생성 권한을 부여한다. 토큰을 채팅·원장·코드·콘솔 출력에 남기지 않는다.

## 실행 순서

1. Preview 환경변수만 설정한다.
2. Preview에서 UTM 유입 → 관심 접수 → Notion 한 행 생성 여부를 확인한다.
3. 같은 접수에서 GA4 이벤트에 이메일·전화번호가 없는지 확인한다.
4. 동의 미체크, 연락처 누락, 외부 Origin, honeypot 입력을 각각 거부한다.
5. 중복 제출·Notion 오류 시 성공 안내가 나오지 않는지 확인한다.
6. 대표가 Preview 표면과 CRM 행을 확인한 뒤 Production 환경변수를 설정한다.

## Phase 1 진입 게이트

PortOne V2 결제와 자사몰 예약을 활성화하기 전까지 `rooms.json`의 `fulfillment.mode`는 `external`로 유지한다. iCal을 재고 잠금의 정본으로 사용하지 않는다. Phase 1에는 별도 저장소 기반의 시간대 잠금, PortOne 서버 검증, 웹훅 멱등 처리, 환불 경계, 아워플레이스·네이버예약과의 충돌 확인이 모두 필요하다.
