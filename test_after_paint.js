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

function makeEnv(room, ua) {
  const rafQ = [];
  const timers = [];
  let now = 0;
  const docListeners = {};
  const winListeners = {};   // { type: [{fn, capture}] }
  const window = {
    localStorage: { getItem: () => null, setItem: () => {} },
    location: { origin: 'https://nuvie.example', pathname: '/', search: '' },
    navigator: { userAgent: ua || 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1' },
    requestAnimationFrame: (fn) => rafQ.push(fn),
    setTimeout: (fn, ms) => timers.push({ fn, at: now + (ms || 0) }),
    addEventListener: (t, fn, cap) => { (winListeners[t] = winListeners[t] || []).push({ fn, capture: cap === true || !!(cap && cap.capture) }); },
    removeEventListener: (t, fn) => { winListeners[t] = (winListeners[t] || []).filter((l) => l.fn !== fn); },
  };
  window.window = window;
  const document = {
    referrer: '',
    body: { getAttribute: (k) => (k === 'data-room' ? room : null) },
    addEventListener: (t, fn) => { (docListeners[t] = docListeners[t] || []).push(fn); },
    removeEventListener: (t, fn) => { docListeners[t] = (docListeners[t] || []).filter((f) => f !== fn); },
  };
  const ctx = { window, document, navigator: window.navigator, URL, URLSearchParams, Date, Math, JSON, Object, String, Array,
    requestAnimationFrame: window.requestAnimationFrame, setTimeout: window.setTimeout };
  vm.runInNewContext(fs.readFileSync('attribution.js', 'utf8'), ctx, { filename: 'attribution.js' });
  return {
    A: window.NUVIE_ATTRIBUTION,
    window,
    docListeners,
    winListeners,
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
    fire(type) {
      (winListeners[type] || []).slice().forEach((l) => l.fn({ type }));
      (docListeners[type] || []).slice().forEach((f) => f({ type }));
    },
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
  assert.strictEqual((E.winListeners.visibilitychange || []).length, 0, '실행 뒤 숨김 리스너를 걷어야 한다');
  assert.strictEqual((E.winListeners.pagehide || []).length, 0, '실행 뒤 pagehide 리스너를 걷어야 한다');
}

// ② 페이지를 떠날 때(pagehide) — visibilitychange 없이 pagehide 만 오는 엔진에서도 즉시 나간다
{
  const E = makeEnv(null); const log = [];
  E.A.afterPaint(blank, () => log.push('a'));
  E.fire('pagehide');
  assert.deepStrictEqual(log, ['a'], 'pagehide 에서 바로 나가야 한다');
}

// ② 숨김·떠남 리스너는 window «캡처» 단계 — gtag·픽셀·Clarity 가 로드 때 건 숨김 처리보다 먼저 돈다(새 눈 검수 09-30)
{
  const E = makeEnv(null);
  E.A.afterPaint(blank, () => {});
  for (const t of ['visibilitychange', 'pagehide']) {
    const ls = E.winListeners[t] || [];
    assert.strictEqual(ls.length, 1, t + ' 리스너 1개');
    assert.ok(ls[0].capture, t + ' 는 캡처 단계여야 한다');
  }
}

// 앱 안 브라우저(인스타·페북·카톡·안드로이드 웹뷰)는 새 탭 링크도 같은 화면에서 열 수 있다 → 종전처럼 바로 실행
{
  const inApp = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 350.0.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/480.0]',
    'Mozilla/5.0 (Linux; Android 14; SM-S921N Build/UP1A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Mobile Safari/537.36 KAKAOTALK 10.8.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 NAVER(inapp; search; 2000; 12.8.0)',
  ];
  for (const ua of inApp) {
    const E = makeEnv(null, ua); const log = [];
    E.A.afterPaint(blank, () => log.push('x'));
    assert.deepStrictEqual(log, ['x'], '앱 안 브라우저는 바로 실행: ' + ua.slice(-40));
  }
  const C = makeEnv(null, 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Mobile Safari/537.36');
  const l2 = []; C.A.afterPaint(blank, () => l2.push('y'));
  assert.deepStrictEqual(l2, [], '일반 크롬은 미룬다');
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

// ⑤ 10/1 /b 1안(대표): /b 도 A와 같다 — 새 탭이면 화면을 그린 뒤
{
  const E = makeEnv('b'); const log = [];
  E.A.afterPaint(blank, () => log.push('b'));
  assert.deepStrictEqual(log, [], '/b 도 새 탭 예약 클릭은 바로 실행하지 않는다');
  E.frame(); E.advance(0);
  assert.deepStrictEqual(log, ['b'], '그린 뒤에는 한 번 나간다');
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
