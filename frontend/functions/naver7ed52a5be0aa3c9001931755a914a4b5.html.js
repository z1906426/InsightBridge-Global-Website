// Naver site verification for insightbridge.global.
// Served via a Pages Function so the exact URL
// (/naver7ed52a5be0aa3c9001931755a914a4b5.html) returns 200 directly —
// CF Pages' built-in pretty-URL behavior would otherwise 308-redirect
// "/foo.html" to "/foo", and Naver's site verifier requires an
// exact-URL 200 response. (Same pattern as the Baidu verification file.)
export async function onRequest(context) {
  return new Response(
    "naver-site-verification: naver7ed52a5be0aa3c9001931755a914a4b5.html",
    {
      status: 200,
      headers: { "content-type": "text/html; charset=utf-8" },
    }
  );
}
