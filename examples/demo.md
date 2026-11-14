# HAR brief

Not anonymous: request patterns, counts, statuses, timings and sizes remain. Review before sharing. This is a diagnostic brief, not a sanitized HAR.

## Overview

- Requests: 5 across 4 endpoint aliases
- HTTP 4xx/5xx: 2; status 0: 0; unknown status: 0
- Duration p50 / p95 / max: 220 / 1800 / 1800 ms (5 measured)
- Reported response body bytes: 34480 (4 measured)

## Endpoints by cumulative request duration

Sums include overlapping requests; they are not page-load time. Query and fragment are ignored when grouping.

| Alias | Method | First request | Count | HTTP errors | p95 ms | Sum ms | Wait sum ms |
|---|---|---:|---:|---:|---:|---:|---:|
| E002 | GET | 2 | 2 | 1 | 1800 | 2020 | 1998 |
| E003 | GET | 4 | 1 | 0 | 420 | 420 | 409 |
| E001 | GET | 1 | 1 | 0 | 80 | 80 | 69 |
| E004 | GET | 5 | 1 | 1 | 55 | 55 | 44 |

## Slowest measured requests

| Request | Alias | Method | Status | Duration ms | Wait ms | Body bytes |
|---:|---|---|---:|---:|---:|---:|
| 3 | E002 | GET | 503 | 1800 | 1789 | 80 |
| 4 | E003 | GET | 200 | 420 | 409 | 32000 |
| 2 | E002 | GET | 200 | 220 | 209 | 1800 |
| 1 | E001 | GET | 200 | 80 | 69 | 600 |
| 5 | E004 | GET | 404 | 55 | 44 | n/a |

## HTTP errors and status-zero requests (first 10)

| Request | Alias | Status | Duration ms |
|---:|---|---:|---:|
| 3 | E002 | 503 | 1800 |
| 5 | E004 | 404 | 55 |

## Interpretation

Tables show at most 10 rows each. JSON output includes every request and endpoint.
Request numbers are 1-based positions in the original log.entries array, not chronological ranks.
Aliases group HTTP(S) origin + exact path + normalized method; no route-template inference. Aliases only apply within this capture.
Unknown, negative and out-of-range measurements become n/a. Quantiles use nearest rank over measured durations only.
The HAR wait phase is reported as captured, not diagnosed as server processing time. SSL is already included in connect; do not add it twice.
Status 0 means no HTTP status was recorded, not proof of a network failure. No root cause is inferred.
URLs, headers, bodies, cookies, timestamps, page names, IPs and extension fields are not included.
