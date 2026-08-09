(function () {
  'use strict';

  var STORAGE_KEY = 'nv_attribution_v1';
  var MAX = 120;
  var TOUCH_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'gclid', 'fbclid'];

  function clip(value, limit) {
    return String(value || '').trim().slice(0, limit || MAX);
  }

  function readState() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function writeState(state) {
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
  }

  function currentTouch() {
    var q = new URLSearchParams(window.location.search);
    var touch = {};
    var hasCampaign = false;
    TOUCH_KEYS.forEach(function (key) {
      var value = clip(q.get(key));
      if (value) {
        touch[key] = value;
        hasCampaign = true;
      }
    });
    if (!hasCampaign) return null;

    touch.landing_path = clip(window.location.pathname, MAX);
    touch.captured_at = new Date().toISOString();
    return touch;
  }

  function referrerOrigin() {
    try {
      if (!document.referrer) return '';
      var ref = new URL(document.referrer);
      if (ref.origin === window.location.origin) return '';
      return clip(ref.origin, MAX);
    } catch (e) {
      return '';
    }
  }

  var state = readState();
  var incoming = currentTouch();
  var now = new Date().toISOString();
  if (!state.first_visit_at) state.first_visit_at = now;
  state.last_visit_at = now;
  if (incoming) {
    if (!state.first_touch) state.first_touch = incoming;
    state.last_touch = incoming;
  }
  var ref = referrerOrigin();
  if (ref) state.last_referrer_origin = ref;
  writeState(state);

  function snapshot() {
    return {
      first_touch: state.first_touch || null,
      last_touch: state.last_touch || null,
      first_visit_at: clip(state.first_visit_at, 40),
      last_visit_at: clip(state.last_visit_at, 40),
      last_referrer_origin: clip(state.last_referrer_origin, MAX)
    };
  }

  function event(name, params) {
    try {
      if (window.gtag) window.gtag('event', name, params || {});
    } catch (e) {}
  }

  window.NUVIE_ATTRIBUTION = { get: snapshot, event: event };
  event('landing_view', {
    first_source: clip(state.first_touch && state.first_touch.utm_source, 60) || 'direct',
    last_source: clip(state.last_touch && state.last_touch.utm_source, 60) || 'direct',
    page: clip(window.location.pathname, 80),
    transport_type: 'beacon'
  });

  function roomFor(el) {
    var room = el.getAttribute('data-room') || el.getAttribute('data-book');
    if (room === 'a' || room === 'b') return room;
    var id = el.id || '';
    if (/A$/.test(id) || /-a$/.test(id)) return 'a';
    if (/B$/.test(id) || /-b$/.test(id)) return 'b';
    return '';
  }

  document.addEventListener('click', function (e) {
    var target = e.target && e.target.closest ? e.target.closest('[data-book],#availBookA,#availBookB,#dayDetailBookA,#dayDetailBookB') : null;
    if (target) {
      event('booking_intent', {
        room: roomFor(target),
        placement: clip(target.id || 'booking_cta', 60),
        transport_type: 'beacon'
      });
      return;
    }
    var interest = e.target && e.target.closest ? e.target.closest('a[href="#interest"]') : null;
    if (interest) event('interest_form_open', { placement: clip(interest.id || 'interest_link', 60), transport_type: 'beacon' });
  });

  var form = document.getElementById('interestForm');
  if (!form) return;
  var status = document.getElementById('interestStatus');
  var submit = form.querySelector('[type="submit"]');

  function setStatus(message, isError) {
    if (!status) return;
    status.textContent = message;
    status.dataset.state = isError ? 'error' : 'ok';
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (form.dataset.pending === '1') return;
    var privacy = form.querySelector('[name="privacy_consent"]');
    var email = clip((form.querySelector('[name="email"]') || {}).value, 254);
    var phone = clip((form.querySelector('[name="phone"]') || {}).value, 40);
    var room = clip((form.querySelector('[name="room"]') || {}).value, 20);
    if (!privacy || !privacy.checked) {
      setStatus('개인정보 수집·이용 동의가 필요합니다.', true);
      if (privacy) privacy.focus();
      return;
    }
    if (!email && !phone) {
      setStatus('이메일 또는 전화번호 중 하나를 입력해 주세요.', true);
      (form.querySelector('[name="email"]') || form.querySelector('[name="phone"]')).focus();
      return;
    }

    var payload = {
      room: room,
      email: email,
      phone: phone,
      inquiry: clip((form.querySelector('[name="inquiry"]') || {}).value, 1000),
      privacy_consent: true,
      marketing_consent: !!(form.querySelector('[name="marketing_consent"]') || {}).checked,
      website: clip((form.querySelector('[name="website"]') || {}).value, 40),
      attribution: snapshot()
    };

    form.dataset.pending = '1';
    if (submit) submit.disabled = true;
    setStatus('접수 중입니다…', false);
    event('interest_form_submit_attempt', { room: room, transport_type: 'beacon' });

    fetch(form.getAttribute('action') || '/api/interest', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok || !data.ok) throw new Error('interest submission failed');
        return data;
      });
    }).then(function () {
      setStatus('접수되었습니다. 확인 후 안내드리겠습니다.', false);
      event('interest_form_submitted', { room: room, transport_type: 'beacon' });
      form.reset();
    }).catch(function () {
      setStatus('접수에 실패했습니다. 잠시 후 다시 시도해 주세요.', true);
    }).finally(function () {
      delete form.dataset.pending;
      if (submit) submit.disabled = false;
    });
  });
})();
