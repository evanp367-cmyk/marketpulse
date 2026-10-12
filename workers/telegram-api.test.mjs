import assert from 'node:assert/strict';
import test from 'node:test';
import worker from './telegram-api.mjs';

const key = 'a'.repeat(64);
const env = { ROUTE_KEY: key };

test('forwards only authenticated Telegram Bot API methods', async () => {
  const originalFetch = globalThis.fetch;
  let forwarded;
  globalThis.fetch = async (request) => {
    forwarded = request;
    return new Response('{"ok":true}', {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  try {
    const request = new Request(
      `https://worker.example/${key}/bot123456:secret/getMe`,
      { method: 'POST', body: '{}', headers: { 'Content-Type': 'application/json' } },
    );
    const response = await worker.fetch(request, env);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.equal(forwarded.url, 'https://api.telegram.org/bot123456:secret/getMe');
    assert.equal(forwarded.method, 'POST');
    assert.equal(await forwarded.text(), '{}');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('rejects requests without the route key and unrelated paths', async () => {
  for (const path of [
    '/bot123456:secret/getMe',
    `/${key}/https://other.example/`,
    `/${key}/bot123456:secret/../../admin`,
  ]) {
    const response = await worker.fetch(new Request(`https://worker.example${path}`), env);
    assert.equal(response.status, 404);
  }
});

test('does not expose upstream failures or run without a route key', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('private upstream detail'); };
  try {
    const url = `https://worker.example/${key}/bot123456:secret/getMe`;
    assert.equal((await worker.fetch(new Request(url), {})).status, 503);
    const response = await worker.fetch(new Request(url), env);
    assert.equal(response.status, 502);
    assert.equal(await response.text(), 'Telegram API is unavailable');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
