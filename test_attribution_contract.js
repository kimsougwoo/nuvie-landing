// attribution.js 런타임 계약 테스트 (node 실행: `node test_attribution_contract.js`)
//
// 🔄 2026-08-22 재작성: 종전 테스트는 «없어진» NUVIE_ATTRIBUTION.enrich() 를 검사해
//   항상 TypeError 로 죽었다(attribution.js 가 get/event/tag/utmParams 로 리팩터됨).
//   pytest 스위트에 없어 CI 가 못 잡던 stale 테스트였다. 현재 계약으로 갱신한다.
//   .py 테스트는 «소스 문자열»만 보므로, 이 파일이 유일한 «런타임» 계약 검증이다
//   (UTM 파싱·landing_view 발화·Clarity 태그·PII 안전·클릭 리스너 등록).
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function storage() {
  const values = new Map();
  return {
    getItem: (k) => (values.has(k) ? values.get(k) : null),
    setItem: (k, v) => values.set(k, String(v)),
  };
}

const events = [];   // gtag 호출 기록
const clarity = [];  // clarity set 호출 기록
const listeners = []; // document 리스너 등록 기록
const window = {
  localStorage: storage(),
  location: {
    origin: 'https://nuvie.example',
    pathname: '/',
    search: '?utm_source=meta&utm_campaign=room-test&fbclid=fb-test',
  },
  gtag: (type, name, params) => events.push({ type, name, params }),
  clarity: (op, key, value) => clarity.push({ op, key, value }),
};
window.window = window;
const document = { referrer: '', addEventListener: (t) => listeners.push(t) };

const context = { window, document, URL, URLSearchParams, Date, Math, JSON, Object, String, Array };
vm.runInNewContext(fs.readFileSync('attribution.js', 'utf8'), context, { filename: 'attribution.js' });

const A = window.NUVIE_ATTRIBUTION;

// 1) 공개 API 표면 (현재 계약)
for (const fn of ['get', 'event', 'tag', 'utmParams']) {
  assert.strictEqual(typeof A[fn], 'function', `NUVIE_ATTRIBUTION.${fn} 이 함수가 아니다`);
}
assert.ok(!('enrich' in A), 'enrich 는 폐기된 API — 되살아나면 계약 문서와 어긋난다');

// 2) utmParams() — 쿼리에서 UTM 파싱, 없는 키는 기본값(direct/none)
const u = A.utmParams();
assert.strictEqual(u.utm_source, 'meta');
assert.strictEqual(u.utm_campaign, 'room-test');
assert.strictEqual(u.utm_medium, 'none');   // 쿼리에 없음 → 기본
assert.strictEqual(u.utm_content, 'none');

// 3) snapshot() — last_touch 에 UTM + fbclid + landing_path, 첫 방문이면 first_touch 도
const s = A.get();
assert.ok(s.last_touch, 'last_touch 가 없다');
assert.strictEqual(s.last_touch.utm_source, 'meta');
assert.strictEqual(s.last_touch.fbclid, 'fb-test');
assert.ok(s.last_touch.landing_path, 'landing_path 가 없다');
assert.ok(s.first_touch, 'first_touch 가 없다(첫 방문 기록 누락)');

// 4) landing_view 이벤트가 UTM 과 함께 발화(beacon)
const lv = events.find((e) => e.name === 'landing_view');
assert.ok(lv, 'landing_view 이벤트가 발화되지 않았다');
assert.strictEqual(lv.params.last_source, 'meta');
assert.strictEqual(lv.params.utm_campaign, 'room-test');
assert.strictEqual(lv.params.transport_type, 'beacon');

// 5) Clarity 태그에 utm_source 반영(집계 라벨)
assert.ok(
  clarity.some((c) => c.key === 'utm_source' && c.value === 'meta'),
  'clarity utm_source 태그가 없다'
);

// 6) booking_intent 클릭 리스너가 등록됐다(위임)
assert.ok(listeners.includes('click'), 'booking_intent 클릭 리스너가 등록되지 않았다');

// 7) PII 안전 — 어떤 gtag/clarity 호출도 email/phone 을 싣지 않는다
for (const e of events) {
  const p = e.params || {};
  assert.ok(!('email' in p) && !('phone' in p), 'gtag 파라미터에 PII 가 있다');
}
assert.ok(
  !clarity.some((c) => c.key === 'email' || c.key === 'phone'),
  'clarity 태그에 PII 가 있다'
);

console.log('attribution contract (current API: get/event/tag/utmParams) OK');
