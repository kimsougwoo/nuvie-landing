// NUVIE_ATTRIBUTION.afterPaint 런타임 계약 (node 실행: `node test_after_paint.js`) — 2026-09-30
//
// 왜: 예약 버튼(새 탭으로 아워에 나감)을 누르면 계측 호출(gtag·fbq·clarity 약 10번)이 클릭 처리 안에서 돌아
//   다음 화면이 늦게 그려졌다(모바일 CPU 4배 + 추적 켬 실측 344ms, nuvie_ux_lab). 새 탭 클릭은 계측을
//   «화면을 그린 뒤»로 미룬다. 지키는 선:
//   ① 같은 탭 이동(target 없음)은 미루지 않는다 — 미루면 페이지가 떠나며 계측이 사라진다
//   ② 새 탭이 앞으로 오면 원래 탭은 숨겨져 requestAnimationFrame 이 멈춘다 → 숨김 전환·200ms 시계로도 반드시 한 번 나간다
//   ③ 두 번 나가지 않는다 ④ 순서가 바뀌지 않는다 ⑤ /b 는 11/11 동결 — 종전처럼 바로 실행
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function makeEnv(room) {
  const rafQ = [];
  const timers = [];
  let now = 0;
  const docListeners = {};
  const window = {
    localStorage: { getItem: () => null, setItem: () => {} },
    location: { origin: 'https://nuvie.example', pathname: '/', search: '' },
    requestAnimationFrame: (fn) => rafQ.push(fn),
    setTimeout: (fn, ms) => timers.push({ fn, at: now + (ms || 0) }),
  };
  window.window = window;
  const document = {
    referrer: '',
    body: { getAttribute: (k) => (k === 'data-room' ? room : null) },
    addEventListener: (t, fn) => { (docListeners[t] = docListeners[t] || []).push(fn); },
    removeEventListener: (t, fn) => { docListeners[t] = (docListeners[t] || []).filter((f) => f !== fn); },
  };
  const ctx = { window, document, URL, URLSearchParams, Date, Math, JSON, Object, String, Array,
    requestAnimationFrame: window.requestAnimationFrame, setTimeout: window.setTimeout };
  vm.runInNewContext(fs.readFileSync('attribution.js', 'utf8'), ctx, { filename: 'attribution.js' });
  return {
    A: window.NUVIE_ATTRIBUTION,
    window,
    docListeners,
    frame() { rafQ.splice(0).forEach((f) => f()); },
    advance(ms) {
      now += ms;
      let ran = true;
      while (ran) {
        ran = false;
        timers.sort((a, b) => a.at - b.at);
        const i = timers.findIndex((t) => t.at <= now);
        if (i >= 0) { const t = timers.splice(i, 1)[0]; t.fn(); ran = true; }
      }
    },
    fire(type) { (docListeners[type] || []).slice().forEach((f) => f({ type })); },
  };
}

const blank = { target: '_blank' };
const sameTab = { target: '' };

// ① 같은 탭 → 바로 실행
{
  const E = makeEnv(null); const log = [];
  assert.strictEqual(typeof E.A.afterPaint, 'function', 'afterPaint 가 없다');
  E.A.afterPaint(sameTab, () => log.push('x'));
  assert.deepStrictEqual(log, ['x'], '같은 탭 이동은 미루면 안 된다');
  E.A.afterPaint(null, () => log.push('y'));
  assert.deepStrictEqual(log, ['x', 'y'], '요소가 없으면 바로 실행');
}

// 새 탭 → 클릭 처리 중엔 안 돌고, 다음 프레임 뒤 타이머에서 한 번
{
  const E = makeEnv(null); const log = [];
  E.A.afterPaint(blank, () => log.push('a'));
  assert.deepStrictEqual(log, [], '새 탭 클릭은 클릭 처리 안에서 돌면 안 된다');
  E.frame(); E.advance(0);
  assert.deepStrictEqual(log, ['a']);
  E.advance(1000); E.fire('visibilitychange');
  assert.deepStrictEqual(log, ['a'], '③ 두 번 나가면 안 된다');
}

// ② 숨은 탭(프레임이 안 옴) → 200ms 시계로 나간다
{
  const E = makeEnv(null); const log = [];
  E.A.afterPaint(blank, () => log.push('a'));
  E.advance(199); assert.deepStrictEqual(log, []);
  E.advance(1); assert.deepStrictEqual(log, ['a'], '프레임이 멈춰도 200ms 에 나가야 한다');
  E.frame(); E.advance(0); assert.deepStrictEqual(log, ['a']);
}

// ② 숨김 전환 → 즉시 나간다
{
  const E = makeEnv(null); const log = [];
  E.A.afterPaint(blank, () => log.push('a'));
  E.fire('visibilitychange');
  assert.deepStrictEqual(log, ['a'], '탭이 숨겨지는 순간 바로 나가야 한다');
  E.frame(); E.advance(500); assert.deepStrictEqual(log, ['a']);
  assert.strictEqual((E.docListeners.visibilitychange || []).length, 0, '실행 뒤 숨김 리스너를 걷어야 한다');
}

// ④ 순서 유지 — 같은 클릭에 걸린 여러 계측이 등록 순서대로
{
  const E = makeEnv(null); const log = [];
  E.A.afterPaint(blank, () => log.push(1));
  E.A.afterPaint(blank, () => log.push(2));
  E.A.afterPaint(blank, () => log.push(3));
  E.fire('visibilitychange');
  assert.deepStrictEqual(log, [1, 2, 3], '숨김 전환 때도 순서 유지');
  const F = makeEnv(null); const l2 = [];
  F.A.afterPaint(blank, () => l2.push(1)); F.A.afterPaint(blank, () => l2.push(2));
  F.frame(); F.advance(0);
  assert.deepStrictEqual(l2, [1, 2], '프레임 경로도 순서 유지');
}

// 한 계측이 죽어도 다음 계측은 나간다
{
  const E = makeEnv(null); const log = [];
  E.A.afterPaint(blank, () => { throw new Error('boom'); });
  E.A.afterPaint(blank, () => log.push('ok'));
  E.frame(); E.advance(0);
  assert.deepStrictEqual(log, ['ok']);
}

// ⑤ /b 동결 — 새 탭이어도 바로 실행
{
  const E = makeEnv('b'); const log = [];
  E.A.afterPaint(blank, () => log.push('b'));
  assert.deepStrictEqual(log, ['b'], '/b 는 11/11 까지 종전 동작(바로 실행)');
}

// booking_intent 위임도 새 탭이면 미룬다(/a)
{
  const E = makeEnv('a'); const sent = [];
  E.window.gtag = (t, n, p) => sent.push(n);
  const el = { target: '_blank', id: '', getAttribute: (k) => (k === 'data-book' ? 'a' : null) };
  el.closest = () => el;
  E.docListeners.click.forEach((f) => f({ target: el }));
  assert.deepStrictEqual(sent, [], 'booking_intent 는 클릭 처리 안에서 돌면 안 된다');
  E.frame(); E.advance(0);
  assert.deepStrictEqual(sent, ['booking_intent']);
}

console.log('after_paint contract OK');
