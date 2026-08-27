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

function restoreEnv(name, value) {
  if (value === undefined) delete process.env[name];
  else process.env[name] = value;
}

test('retries a failed Notion write three times, then sends a PII-free lead failure alert', async () => {
  const previousFetch = global.fetch;
  const previousSetTimeout = global.setTimeout;
  const previousToken = process.env.NOTION_TOKEN;
  const previousDataSource = process.env.NOTION_CRM_DATA_SOURCE_ID;
  const previousWebhook = process.env.DISCORD_WEBHOOK_LEADS;
  const calls = [];
  const lead = {
    ...valid,
    name: '홍길동',
    email: 'lead.owner@example.com',
    phone: '010-1234-5678'
  };

  global.setTimeout = (callback) => { callback(); return 0; };
  global.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url === 'https://api.notion.com/v1/pages') return { ok: false, status: 500 };
    return { ok: true, status: 204 };
  };
  process.env.NOTION_TOKEN = 'test-token';
  process.env.NOTION_CRM_DATA_SOURCE_ID = 'test-source';
  process.env.DISCORD_WEBHOOK_LEADS = 'https://discord.example/webhook/leads';

  try {
    const res = await call(lead);
    const notionCalls = calls.filter(({ url }) => url === 'https://api.notion.com/v1/pages');
    const alertCalls = calls.filter(({ url }) => url === process.env.DISCORD_WEBHOOK_LEADS);

    assert.equal(res.statusCode, 502);
    assert.deepEqual(res.body, { ok: false, error: 'submission failed' });
    assert.equal(notionCalls.length, 3);
    assert.equal(alertCalls.length, 1);
    const alertPayload = JSON.stringify(JSON.parse(alertCalls[0].options.body));
    for (const pii of ['홍길동', 'lead.owner@example.com', '01012345678', '010-1234-5678']) {
      assert.doesNotMatch(alertPayload, new RegExp(pii.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    }
  } finally {
    global.fetch = previousFetch;
    global.setTimeout = previousSetTimeout;
    restoreEnv('NOTION_TOKEN', previousToken);
    restoreEnv('NOTION_CRM_DATA_SOURCE_ID', previousDataSource);
    restoreEnv('DISCORD_WEBHOOK_LEADS', previousWebhook);
  }
});

test('does not retry or alert when the first Notion write succeeds', async () => {
  const previousFetch = global.fetch;
  const previousToken = process.env.NOTION_TOKEN;
  const previousDataSource = process.env.NOTION_CRM_DATA_SOURCE_ID;
  const previousWebhook = process.env.DISCORD_WEBHOOK_LEADS;
  const calls = [];
  global.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 200 };
  };
  process.env.NOTION_TOKEN = 'test-token';
  process.env.NOTION_CRM_DATA_SOURCE_ID = 'test-source';
  process.env.DISCORD_WEBHOOK_LEADS = 'https://discord.example/webhook/leads';

  try {
    const res = await call(valid);
    assert.equal(res.statusCode, 200);
    assert.equal(calls.filter(({ url }) => url === 'https://api.notion.com/v1/pages').length, 1);
    assert.equal(calls.filter(({ url }) => url === process.env.DISCORD_WEBHOOK_LEADS).length, 0);
  } finally {
    global.fetch = previousFetch;
    restoreEnv('NOTION_TOKEN', previousToken);
    restoreEnv('NOTION_CRM_DATA_SOURCE_ID', previousDataSource);
    restoreEnv('DISCORD_WEBHOOK_LEADS', previousWebhook);
  }
});

test('does not crash or attempt an alert when the lead webhook is not configured', async () => {
  const previousFetch = global.fetch;
  const previousSetTimeout = global.setTimeout;
  const previousToken = process.env.NOTION_TOKEN;
  const previousDataSource = process.env.NOTION_CRM_DATA_SOURCE_ID;
  const previousWebhook = process.env.DISCORD_WEBHOOK_LEADS;
  let calls = 0;
  global.setTimeout = (callback) => { callback(); return 0; };
  global.fetch = async () => {
    calls += 1;
    throw new Error('temporary Notion failure');
  };
  process.env.NOTION_TOKEN = 'test-token';
  process.env.NOTION_CRM_DATA_SOURCE_ID = 'test-source';
  delete process.env.DISCORD_WEBHOOK_LEADS;

  try {
    const res = await call(valid);
    assert.equal(res.statusCode, 502);
    assert.equal(calls, 3);
  } finally {
    global.fetch = previousFetch;
    global.setTimeout = previousSetTimeout;
    restoreEnv('NOTION_TOKEN', previousToken);
    restoreEnv('NOTION_CRM_DATA_SOURCE_ID', previousDataSource);
    restoreEnv('DISCORD_WEBHOOK_LEADS', previousWebhook);
  }
});

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

test('allows the current Vercel preview origin while keeping persistence fail-closed', async () => {
  const previousFetch = global.fetch;
  const previousToken = process.env.NOTION_TOKEN;
  const previousDataSource = process.env.NOTION_CRM_DATA_SOURCE_ID;
  const previousVercelUrl = process.env.VERCEL_URL;
  let called = false;
  global.fetch = async () => { called = true; return { ok: true }; };
  delete process.env.NOTION_TOKEN;
  delete process.env.NOTION_CRM_DATA_SOURCE_ID;
  process.env.VERCEL_URL = 'nuvie-landing-preview.vercel.app';
  const res = await call(valid, { headers: { origin: 'https://nuvie-landing-preview.vercel.app' } });
  global.fetch = previousFetch;
  if (previousToken === undefined) delete process.env.NOTION_TOKEN;
  else process.env.NOTION_TOKEN = previousToken;
  if (previousDataSource === undefined) delete process.env.NOTION_CRM_DATA_SOURCE_ID;
  else process.env.NOTION_CRM_DATA_SOURCE_ID = previousDataSource;
  if (previousVercelUrl === undefined) delete process.env.VERCEL_URL;
  else process.env.VERCEL_URL = previousVercelUrl;
  assert.equal(res.statusCode, 503);
  assert.equal(called, false);
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

test('accepts a JSON string body as sent by a raw HTTP client', async () => {
  const previousToken = process.env.NOTION_TOKEN;
  const previousDataSource = process.env.NOTION_CRM_DATA_SOURCE_ID;
  delete process.env.NOTION_TOKEN;
  delete process.env.NOTION_CRM_DATA_SOURCE_ID;
  const res = await call(JSON.stringify(valid));
  if (previousToken === undefined) delete process.env.NOTION_TOKEN;
  else process.env.NOTION_TOKEN = previousToken;
  if (previousDataSource === undefined) delete process.env.NOTION_CRM_DATA_SOURCE_ID;
  else process.env.NOTION_CRM_DATA_SOURCE_ID = previousDataSource;
  assert.equal(res.statusCode, 503);
  assert.deepEqual(res.body, { ok: false, error: 'submission unavailable' });
});

test('rejects unsupported methods', async () => {
  const res = await call(null, { method: 'GET' });
  assert.equal(res.statusCode, 405);
});

test('rejects a foreign origin', async () => {
  const res = await call(valid, { headers: { origin: 'https://attacker.example' } });
  assert.equal(res.statusCode, 403);
});
