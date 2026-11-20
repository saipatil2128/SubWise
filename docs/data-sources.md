# Data sources register

Every provider SubWise reads must be listed here **before** its adapter or seed rows are merged
(M4/M8). No prices are recorded in this file; prices live in `price_observations` with evidence.

| Provider | Service lines | Official India pricing URL | robots.txt checked (date, result) | Terms reviewed (date, note) | Access method | Adapter | Last verified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| *(added in M4)* | | | | | manual / httpx / playwright | | |

Rules: official domains only; honest User-Agent; respect robots.txt and terms; no CAPTCHA or login
bypass; if automated access is not allowed, use `fetch_method = manual` with the URL and the date
a team member copied the price, and say so in the UI.
