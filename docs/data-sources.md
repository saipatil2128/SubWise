# Data sources register

SubWise reads only these official pages. No prices are stored in this file or anywhere in the
code; prices exist only as `price_observations` created by live retrieval, each with its source
URL, retrieval time and the evidence text from the page.

robots.txt is checked automatically before **every** fetch (a disallowed page is never fetched and
is reported as `disallowed`). The terms-of-use review is a human task and is still open.

| Provider | Official domains | India pricing URL | Needs JavaScript | robots.txt | Terms of use reviewed |
| --- | --- | --- | --- | --- | --- |
| Netflix | netflix.com | https://help.netflix.com/en/node/24926/in | no | checked at runtime | ☐ pending |
| Amazon Prime Video | amazon.in | https://www.amazon.in/amazonprime | no | checked at runtime | ☐ pending |
| Sony LIV | sonyliv.com | https://www.sonyliv.com/subscription | yes | checked at runtime | ☐ pending |
| Spotify | spotify.com | https://www.spotify.com/in-en/premium/ | no | checked at runtime | ☐ pending |
| YouTube Premium | youtube.com | https://www.youtube.com/premium?gl=IN&hl=en-IN | yes | checked at runtime | ☐ pending |
| Apple Music | apple.com | https://www.apple.com/in/apple-music/ | no | checked at runtime | ☐ pending |

Rules: official domains only; honest User-Agent; respect robots.txt and terms; no CAPTCHA, login or
rate-limit bypass; private-IP targets are blocked. If a provider's terms do not allow automated
access, remove it from `research/registry.py` rather than working around it.

## Removed providers

| Provider | Removed | Reason |
| --- | --- | --- |
| JioHotstar | 2026-11-21 | `jiohotstar.com/subscribe` sends automated clients, including a real headless browser, into a redirect loop |
| ZEE5 | 2026-11-21 | `zee5.com/myaccount/subscription` returns HTTP 403 to automated clients, including a real headless browser |

SubWise does not bypass blocks, so these providers were removed rather than worked around. Users who
pay for them can add them as subscriptions with their own price; the optimizer treats them as fixed
costs.
