// Baidu site verification for insightbridge.global.
// Served via a Pages Function so the exact URL (/codeva-rsK0YwIlUP.html)
// returns 200 directly — CF Pages' built-in pretty-URL behavior would
// otherwise 308-redirect "/foo.html" to "/foo", and Baidu's site
// verifier requires an exact-URL 200 response.
export async function onRequest(context) {
  return new Response("2152fa17e2869bec0dd9f32e113b5292", {
    status: 200,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}
