const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

function storage() {
  const values = new Map();
  return {
    getItem: (key) => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
  };
}

const events = [];
const clarity = [];
const window = {
  localStorage: storage(),
  sessionStorage: storage(),
  crypto: { randomUUID: () => 'fixed-id' },
  location: {
    origin: 'https://nuvie.example',
    pathname: '/',
    search: '?utm_source=meta&utm_campaign=room-test&fbclid=fb-test',
  },
  gtag: (type, name, params) => events.push({ type, name, params }),
  clarity: (type, key, value) => clarity.push({ type, key, value }),
};
const document = { referrer: '', addEventListener: () => {} };
window.window = window;

const context = {
  window,
  document,
  URL,
  URLSearchParams,
  Date,
  Math,
  JSON,
  Object,
  String,
  Array,
};
vm.runInNewContext(fs.readFileSync('attribution.js', 'utf8'), context, { filename: 'attribution.js' });

const payload = window.NUVIE_ATTRIBUTION.enrich({ room: 'a', placement: 'hero' }, 'book_click');
for (const key of ['nuvie_event_id', 'nuvie_session_id', 'nuvie_visit_id', 'utm_source', 'utm_campaign', 'fbclid', 'landing_path', 'booking_channel']) {
  assert.ok(payload[key], `missing ${key}`);
}
assert.strictEqual(payload.booking_channel, 'hourplace');
assert.strictEqual(payload.room, 'a');
assert.ok(events.some((event) => event.name === 'landing_view'));
assert.ok(clarity.some((tag) => tag.key === 'nuvie_session_id'));
assert.ok(!Object.prototype.hasOwnProperty.call(payload, 'email'));
assert.ok(!Object.prototype.hasOwnProperty.call(payload, 'phone'));
console.log('attribution contract: anonymous context / PortOne-ready nullable fields OK');
