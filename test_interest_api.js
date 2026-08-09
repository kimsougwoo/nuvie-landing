const test = require('node:test');
const assert = require('node:assert/strict');
const handler = require('./api/interest.js');

function response() {
  return {
    statusCode: 200,
    headers: {},
    body: null,
    setHeader(name, value) { this.headers[name] = value; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
    end(body) { this.body = body ? JSON.parse(body) : null; return this; }
  };
}

async function call(body, options = {}) {
  const res = response();
  const req = {
    method: options.method || 'POST',
    headers: { origin: 'https://www.nuviestudio.com', ...(options.headers || {}) },
    body
  };
  await handler(req, res);
  return res;
}

const valid = {
  room: 'A룸',
  email: 'person@example.com',
  phone: '',
  inquiry: '평일 빈 시간 알림',
  privacy_consent: true,
  marketing_consent: false,
  website: '',
  attribution: {
    first_touch: { utm_source: 'instagram', utm_campaign: 'pilot', gclid: 'click-1' },
    last_touch: { utm_source: 'instagram', utm_content: 'room-a' },
    first_visit_at: '2026-08-09T00:00:00.000Z',
    last_visit_at: '2026-08-09T01:00:00.000Z'
  }
};

test('rejects a lead without required privacy consent before persistence', async () => {
  const previousFetch = global.fetch;
  let called = false;
  global.fetch = async () => { called = true; return { ok: true }; };
  process.env.NOTION_TOKEN = 'test-token';
  process.env.NOTION_CRM_DATA_SOURCE_ID = 'test-source';
  const res = await call({ ...valid, privacy_consent: false });
  global.fetch = previousFetch;
  assert.equal(res.statusCode, 400);
  assert.equal(called, false);
});

test('does not claim success when the Notion deployment environment is not configured', async () => {
  const previousFetch = global.fetch;
  const previousToken = process.env.NOTION_TOKEN;
  const previousDataSource = process.env.NOTION_CRM_DATA_SOURCE_ID;
  let called = false;
  global.fetch = async () => { called = true; return { ok: true }; };
  delete process.env.NOTION_TOKEN;
  delete process.env.NOTION_CRM_DATA_SOURCE_ID;
  const res = await call(valid);
  global.fetch = previousFetch;
  if (previousToken === undefined) delete process.env.NOTION_TOKEN;
  else process.env.NOTION_TOKEN = previousToken;
  if (previousDataSource === undefined) delete process.env.NOTION_CRM_DATA_SOURCE_ID;
  else process.env.NOTION_CRM_DATA_SOURCE_ID = previousDataSource;
  assert.equal(res.statusCode, 503);
  assert.equal(called, false);
  assert.deepEqual(res.body, { ok: false, error: 'submission unavailable' });
});

test('writes only the consented lead fields to the configured Notion data source', async () => {
  const previousFetch = global.fetch;
  let request;
  global.fetch = async (url, options) => {
    request = { url, options };
    return { ok: true };
  };
  process.env.NOTION_TOKEN = 'test-token';
  process.env.NOTION_CRM_DATA_SOURCE_ID = 'test-source';
  const res = await call(valid);
  global.fetch = previousFetch;

  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.body, { ok: true });
  assert.equal(request.url, 'https://api.notion.com/v1/pages');
  assert.equal(request.options.headers.Authorization, 'Bearer test-token');
  const payload = JSON.parse(request.options.body);
  assert.equal(payload.parent.data_source_id, 'test-source');
  assert.equal(payload.properties['이메일'].email, 'person@example.com');
  assert.equal(payload.properties['룸 관심'].select.name, 'A룸');
  assert.equal(payload.properties['개인정보처리방침 동의'].checkbox, true);
  assert.equal(payload.properties['광고성 정보 동의'].checkbox, false);
  assert.equal(payload.properties['수신 채널'].select.name, '이메일');
  assert.match(payload.properties['원본 UTM'].rich_text[0].text.content, /instagram/);
  assert.doesNotMatch(JSON.stringify(res.body), /person@example\.com/);
});

test('rejects unsupported methods', async () => {
  const res = await call(null, { method: 'GET' });
  assert.equal(res.statusCode, 405);
});

test('rejects a foreign origin', async () => {
  const res = await call(valid, { headers: { origin: 'https://attacker.example' } });
  assert.equal(res.statusCode, 403);
});
