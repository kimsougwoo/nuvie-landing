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

  // Clarity custom tags are aggregate labels only: never pass email, phone,
  // booking IDs, or query-string values.  Internal QA traffic is already
  // stubbed by the page loader, so this remains fail-safe when Clarity is off.
  function clarityTag(key, value) {
    try {
      var safe = clip(value, 80);
      if (window.clarity && safe) window.clarity("set", key, safe);
    } catch (e) {}
  }

  window.NUVIE_ATTRIBUTION = { get: snapshot, event: event, tag: clarityTag };
  event('landing_view', {
    first_source: clip(state.first_touch && state.first_touch.utm_source, 60) || 'direct',
    last_source: clip(state.last_touch && state.last_touch.utm_source, 60) || 'direct',
    page: clip(window.location.pathname, 80),
    transport_type: 'beacon'
  });
  clarityTag('page', window.location.pathname);
  clarityTag('utm_source', state.last_touch && state.last_touch.utm_source || 'direct');
  clarityTag('utm_medium', state.last_touch && state.last_touch.utm_medium || 'none');

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
      clarityTag('event', 'booking_intent');
      clarityTag('room', roomFor(target) || 'unknown');
      clarityTag('placement', target.id || 'booking_cta');
      return;
    }
  });
})();
