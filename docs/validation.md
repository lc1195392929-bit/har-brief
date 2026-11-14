# Validation record

Checked on 2026-11-14. This is an early-stage source release, not a security audit
certification or a claim of real customer adoption.

## Passed locally

Environment: Linux, Python 3.12.14.

- **43 unittest tests passed**, including 17 independently written adversarial
  tests. An independent review found explicit port 0 incorrectly merged with a
  default port; this was fixed and the full suite rerun successfully.
- Synthetic canaries in URLs, headers, cookies, payloads, status/MIME/method text,
  pages and unknown extensions do not occur in JSON/Markdown output.
- Malformed JSON, duplicate keys, non-finite constants, deep nesting, unsupported
  container shapes and resource limits tested; parsing errors omit source excerpts.
- Unknown values, zero values, status handling, nearest-rank quantiles, alias
  equality, scheme/method separation and source-array ordinals tested.
- CLI stdin, exit codes, no source overwrite, exclusive output creation, symlink
  rejection, POSIX 0600 output and FIFO rejection tested.
- README's source-tree example run; Markdown output matches `examples/demo.md`.
- Wheel built without build isolation, installed into a fresh virtual environment
  without index or dependency downloads; installed CLI JSON output matches
  `examples/demo.json` exactly.
- All bundled captures are synthetic. No user traffic or private work files used.

## Resource observation, not a benchmark promise

A separate synthetic 100,000-request / 13.4 MB input test took about 2.36 seconds
for parse + report + JSON serialization and peaked near 337 MB RSS in this container.
Output was approximately 34.2 MB. This is in-memory processing, not streaming;
32 MiB input does not imply a 32 MiB memory budget. Other machines may differ.

## Not verified locally

- Windows, macOS and Python versions other than 3.12.
- Real customer captures, customer workflows, demand, adoption or willingness to pay.
- Browser-generated HAR integration: a localhost-only synthetic Chromium capture
  check was attempted, but Chromium could not launch because the environment denied
  its process-singleton socket (`Operation not permitted`). This stage did not pass;
  it is not counted among the 43 tests.
- Exhaustive HAR exporter compatibility, formal privacy guarantees, numeric covert
  channels, hostile-host protection or third-party security certification.

A GitHub Actions workflow is provided for Linux/Python 3.10, 3.12 and 3.14 plus
package installation. Its presence is not evidence of a successful run; check the
Actions status for the exact commit you use.

## Reproduce

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m har_brief examples/demo.har
```

## CI-found compatibility fix

The first CI run on Python 3.14 exposed that the interpreter can accept nesting
deeper than older Python versions. The initial implementation relied on the parser's
recursion limit, which was not consistent. A byte-level preflight now enforces a fixed
128-level limit while respecting JSON strings and escapes. Two regression tests were
added. See the workflow for verification of the corrected commit.
