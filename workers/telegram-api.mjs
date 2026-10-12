// Narrow Telegram Bot API relay for MarketPulse. ROUTE_KEY is a Cloudflare secret.
const botMethod = /^\/bot\d+:[A-Za-z0-9_-]+\/[A-Za-z][A-Za-z0-9_]*$/;
const botFile = /^\/file\/bot\d+:[A-Za-z0-9_-]+\/[A-Za-z0-9_./-]+$/;

export default {
  async fetch(request, env) {
    if (typeof env.ROUTE_KEY !== 'string' || env.ROUTE_KEY.length < 32) {
      return new Response('Worker route key is not configured', { status: 503 });
    }

    const incoming = new URL(request.url);
    const prefix = `/${env.ROUTE_KEY}`;
    if (!incoming.pathname.startsWith(`${prefix}/`)) {
      return new Response('Not found', { status: 404 });
    }
    if (request.method !== 'GET' && request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    const telegramPath = incoming.pathname.slice(prefix.length);
    if (!botMethod.test(telegramPath) && !botFile.test(telegramPath)) {
      return new Response('Not found', { status: 404 });
    }

    // The upstream host is fixed; callers cannot use this Worker as an open proxy.
    const upstreamUrl = new URL(`https://api.telegram.org${telegramPath}${incoming.search}`);
    const upstreamRequest = new Request(upstreamUrl, request);
    upstreamRequest.headers.delete('host');
    try {
      const upstreamResponse = await fetch(upstreamRequest);
      const response = new Response(upstreamResponse.body, upstreamResponse);
      response.headers.set('Cache-Control', 'no-store');
      return response;
    } catch {
      return new Response('Telegram API is unavailable', { status: 502 });
    }
  },
};
