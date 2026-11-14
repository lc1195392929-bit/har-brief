# Privacy and threat model

The supported CLI constructs a new report. It does not mutate and reserialize the
original HAR. Input objects and keys are never inserted into report objects.

## Output allowlist

- Constant schema identifier and privacy notice.
- Generated integer request numbers and `E` + integer endpoint aliases.
- Methods: GET, HEAD, POST, PUT, DELETE, CONNECT, OPTIONS, TRACE, PATCH; otherwise OTHER.
- Integer status 0 or 100–599; otherwise null.
- Numeric duration and blocked/dns/connect/ssl/send/wait/receive phases, 0 through
  604800000 ms, rounded to three decimals; otherwise null. Booleans are rejected.
- Integer response bodySize, 0 through 9007199254740991; otherwise null.
- Counts, sums, maxima and nearest-rank quantiles derived from those fields.

No arbitrary field name or value is copied. Even method, status text, MIME type,
comments and unknown extension text cannot enter the report. Numbers can still
encode information; this is data minimization, not mathematical anonymization.

## What is discarded

All URLs (including host/path/userinfo/query/fragment), headers, cookies, bodies,
body encodings, page metadata, timestamps, browser/creator strings, IP addresses,
connection IDs, WebSocket frames, cache entries and unknown/vendor extensions.
URLs are used **only in memory** to establish equality for endpoint grouping.
There is no persistent mapping, hashing or secret detection score.

## Local handling

The application has no network clients, subprocesses, telemetry or dependency
services. It never opens URLs from a capture. File input is read-only and bounded;
output uses exclusive creation, never replacement, including symlink targets.
New POSIX output files are requested as 0600. The caller's stdout destination and
Windows ACLs are outside this guarantee. Input/output paths are not printed in
application I/O errors. JSON parsing errors do not echo input excerpts.

Reports still disclose request sequence and repetition, numerical details and
HTTP outcomes. Alias labels are sequential, not cryptographic pseudonyms. Files
with corresponding order may be linked across captures. User review is required.
The Python process holds the original HAR in memory and does not securely erase it;
OS swap, crash dumps, backups and the local host's security are outside scope.

## Untrusted input limits

32 MiB bytes, 100,000 entries, UTF-8 JSON; duplicate keys are rejected. Deeply nested
input is caught at the interpreter recursion boundary. These limits reduce, but do
not eliminate, resource exhaustion: JSON expansion can require substantially more
RAM, and there is no CPU timeout or sandbox. Do not run on an untrusted host or treat
it as a hardened network-facing service. Stdin can wait indefinitely for EOF.

Only `build_report` with JSON-derived input and the CLI are intended for untrusted
HAR data. `render_markdown` expects a report produced by `build_report`, not an
arbitrary user-supplied report object. The package is not a general escaping library.

## Sharing policy

Never label an output “safe”, “anonymous”, “fully redacted” or “DLP approved”. Obtain
whatever authorization your organization requires. This tool does not create a
Cloudflare sanitizer marker or replace vendor support upload requirements.
