export default {
  async fetch(request, env) {
    if (request.method !== 'GET') {
      return jsonResponse({ error: 'method_not_allowed' }, 405);
    }

    const authHeader = request.headers.get('authorization');
    if (authHeader !== `Bearer ${env.FOOTBALL_PROXY_TOKEN}`) {
      return jsonResponse({ error: 'unauthorized' }, 401);
    }

    const incomingUrl = new URL(request.url);
    const upstreamUrl = new URL(`https://api.football-data.org/v4${incomingUrl.pathname}`);
    upstreamUrl.search = incomingUrl.search;

    const upstreamResponse = await fetch(upstreamUrl, {
      method: 'GET',
      headers: {
        'X-Auth-Token': env.FOOTBALL_DATA_API_KEY,
      },
    });

    const responseHeaders = new Headers();
    responseHeaders.set(
      'content-type',
      upstreamResponse.headers.get('content-type') || 'application/json; charset=utf-8'
    );
    responseHeaders.set('cache-control', 'public, max-age=60');

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    });
  },
};

function jsonResponse(payload, status) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
    },
  });
}
