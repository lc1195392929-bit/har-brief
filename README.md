# har-brief

**A local HAR diagnostic brief without captured URLs, headers or bodies.**

For frontend developers and support engineers who need a first-round answer to
“which requests are slow or failing?” without attaching the original traffic capture.
Python 3.10+, standard library only at runtime, no account or network access needed.

[中文说明](README.zh-CN.md) · [Example report](examples/demo.md) · [Privacy contract](docs/privacy.md) · [Research and alternatives](docs/research.md)

## What it does

- Builds a **new Markdown or JSON report**, not a cleaned HAR.
- Groups requests into encounter-order aliases such as `E001`, preserving repetition
  without publishing hosts or paths. Request numbers point back to the original file.
- Reports HTTP errors, status-zero requests, slowest requests, duration quantiles,
  cumulative timings and known response body bytes.
- Drops all captured free text rather than trying to recognize secret names.
  Only fixed HTTP method enums and bounded numeric measurements are retained.
- Never uploads, replays requests, writes a private URL map, or overwrites files.

**This is not an anonymity guarantee.** Counts, sizes, status codes, timing and
request patterns can still be sensitive. Review the report and your sharing policy.
It does not diagnose root causes or replace a full HAR for header/payload debugging.

## Try it without installing anything

From a downloaded checkout, on macOS/Linux:

```sh
PYTHONPATH=src python -m har_brief examples/demo.har
PYTHONPATH=src python -m unittest discover -s tests -v
```

Or install into a virtual environment (build-time tooling may need Internet):

```sh
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install .
har-brief examples/demo.har
```

The package is not published to PyPI. `pip install har-brief` is not the supported
installation route for this repository.

## Typical support workflow

```sh
har-brief capture.har -o brief.md
har-brief capture.har --format json -o brief.json
har-brief capture.har --top 20 --fail-on-http-error -o checks.md
```

1. Keep the original HAR private. Run the tool locally.
2. Review the resulting brief before sharing it, not the original HAR.
3. If a colleague asks about request 37, inspect `log.entries[36]` in your private
   original. Array order can differ from a browser's sorted display.
4. Share only additional details you are authorized to disclose.

Output files must not already exist. POSIX output mode is `0600` (subject to umask);
Windows ACLs are inherited. For stdout, shell redirection controls file permissions
and **may overwrite a file before this program runs**, so prefer `-o`.

Stdin is supported: `har-brief - --format json < capture.har`.
Exit codes: `0` report written; `1` report written and `--fail-on-http-error` found
HTTP 4xx/5xx; `2` input, argument or I/O error. Status 0 alone does not trigger code 1.

## Interpret the numbers carefully

- Duration comes from `entry.time`; phases are not added together. SSL can already
  be included in connect. Wait is a recorded phase, **not proven server CPU time**.
- Cumulative request duration is **not page-load time** because requests overlap.
- Quantiles use nearest rank over known durations only. Small samples are not
  reliable performance benchmarks.
- Missing, negative, wrong-type or out-of-range measurements are `null` / `n/a`,
  not zero. The report includes known-value counts.
- Response `bodySize` is reported as supplied, excluding headers. Its sum is not
  total network transfer. No content-size or compression inference is made.
- Aliases group HTTP(S) scheme, hostname, effective port, exact path and allowlisted
  method. Query/fragment and userinfo are ignored. Different query operations may
  therefore merge; dynamic paths do not become route templates. Unsupported URLs
  get distinct aliases. Alias numbers cannot be compared between captures.

## Scope and limits

UTF-8 JSON, optional BOM; 32 MiB input and 100,000 entries maximum. Parsing is
in-memory and can use much more RAM than the input. Stdin waits for EOF. Duplicate
JSON keys and nesting beyond 128 levels are rejected. A malformed entry container rejects the whole file.
This is a tolerant extractor, **not a full HAR schema validator**. Durations over
seven days and body sizes above `2^53-1` become unknown.

No CORS, authentication, cache, payload, WebSocket-frame, initiator, waterfall or
page-load analysis. No persistent storage, telemetry, server or third-party runtime
dependencies. There is no security certification or claim of resistance to malicious
numeric covert channels. Do not use the tool to bypass organizational DLP controls.

## Project status

Small, early-stage open-source utility. Public evidence supports the HAR-sharing
problem, but this specific product has no user-adoption, willingness-to-pay or market
validation claim. All included captures and tests use synthetic data, never user
traffic. See [validation](docs/validation.md) for checks and untested platforms.

MIT licensed. Implementation is independently written; research links are not code
imports. Contributions should include synthetic regression tests and must not attach
real HARs, credentials or customer data. See [SECURITY.md](SECURITY.md).
