'use strict';

const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const registered = {};
const target = {
  focus() {},
  scrollIntoView() {},
  setAttribute() {},
  removeAttribute() {}
};
const document = {
  modelContext: {
    registerTool(tool) { registered[tool.name] = tool; }
  },
  querySelector() { return target; }
};
const context = {
  console,
  document,
  Date,
  JSON,
  URL,
  setTimeout,
  clearTimeout,
  fetch: async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      updated: '2026-08-10T05:10',
      events: [{ date: '2026-08-20', start: 0, end: 6, room: 'A' }]
    })
  })
};
context.window = context;
context.NUVIE = {
  rooms: {
    a: { label: 'A룸', name: '동양풍 & 블랙 호리존', placeId: 61823, status: 'open', pricing: { weekday: 40000, weekend: 45000, minHours: 2, unit: 'hour', currency: 'KRW', baseGuests: 4, taxIncluded: true }, capacity: { min: 1, max: 4 } },
    b: { label: 'B룸', name: '화이트 티타임 카페', placeId: 62341, status: 'open', pricing: { weekday: 40000, weekend: 45000, minHours: 2, unit: 'hour', currency: 'KRW', baseGuests: 4, taxIncluded: true }, capacity: { min: 1, max: 4 } }
  },
  fulfillment: { mode: 'external', provider: 'hourplace' }
};

vm.runInNewContext(fs.readFileSync('webmcp.js', 'utf8'), context, { filename: 'webmcp.js' });

assert.deepStrictEqual(Object.keys(registered).sort(), [
  'nuvie_get_availability',
  'nuvie_list_rooms',
  'nuvie_prepare_booking'
]);
assert.strictEqual(context.NUVIE_WEBMCP.supported, true);

(async () => {
  const rooms = await registered.nuvie_list_rooms.execute({});
  assert.strictEqual(rooms.structuredContent.rooms.length, 2);

  const availability = await registered.nuvie_get_availability.execute({ room: 'a', date: '2026-08-20' });
  assert.strictEqual(availability.structuredContent.status, 'busy_blocks_only');
  assert.strictEqual(availability.structuredContent.busy_blocks.length, 1);

  const prepared = await registered.nuvie_prepare_booking.execute({ room: 'b' });
  assert.strictEqual(prepared.structuredContent.requires_human_click, true);
  assert.strictEqual(prepared.structuredContent.payment_started, false);
  assert.strictEqual(prepared.structuredContent.reservation_confirmed, false);
  console.log('webmcp tests: 3 tools / read-only availability / human-click booking guard OK');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
