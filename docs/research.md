# Why this exists, and why it is deliberately narrow

Research date: 2026-11-14. This is desk research, not customer interviews, market
sizing, a security assessment of competitors, or evidence of willingness to pay.

## Evidence of the problem

- [Cloudflare's March 25, 2026 changelog](https://developers.cloudflare.com/changelog/post/2026-03-25-har-file-detection-and-sanitization/)
  introduced an Unsanitized HAR DLP profile for the engineering/support sharing
  workflow. This shows current vendor attention to traffic-capture disclosure.
- [Okta's April 28, 2026 support guidance](https://support.okta.com/help/s/article/how-to-sanitize-a-http-trace-file-automatically)
  states that customers remain responsible for identifying and removing sensitive
  content; email attachments do not trigger its automatic cleaning.
- [Chrome DevTools documentation](https://developer.chrome.com/docs/devtools/network/reference#save-as-har)
  describes the default sanitized export in terms of omitted Cookie, Set-Cookie
  and Authorization headers. This is not a documented promise that all business
  data in a capture has been removed. We did not audit Chrome's exporter.
- [Cloudflare har-sanitizer issue 44](https://github.com/cloudflare/har-sanitizer/issues/44),
  opened July 11, 2024, reports a signed query parameter missed inside JSON body
  content. It is an older public report, not a new vulnerability we discovered or
  reproduced. It illustrates the complexity of retaining and pattern-cleaning text.

These support a real *problem*. They do not validate whether people will prefer
this tool's reduced diagnostic context to a conventional sanitizer.

## Alternatives already exist

| Alternative | Publicly documented overlap | License checked | Tradeoff relative to this project |
|---|---|---|---|
| [kubakozub/har-sanitizer](https://github.com/kubakozub/har-sanitizer) | Offline Python, no runtime dependencies, HAR/curl/raw redaction, strict mode | MIT | Retains useful text and detects known patterns; a different workflow |
| [sen-ltd/har-analyze](https://github.com/sen-ltd/har-analyze) | Local slow/error/size analysis and Markdown/JSON outputs | MIT | Its examples include full URLs, useful when sharing those is acceptable |
| [Toolvore HAR Viewer](https://toolvore.com/tools/har-viewer) | Browser-local inspection and fresh limited summary exports | Open-source license not established | Summary documentation includes host/path, start time and MIME/method text |
| [Google har-sanitizer](https://github.com/google/har-sanitizer) | Configurable sanitization | Apache-2.0 | Broader content-preserving redaction; repository is archived |
| [Cloudflare har-sanitizer](https://github.com/cloudflare/har-sanitizer) | Configurable client-side sanitization | Apache-2.0 | Broader content-preserving redaction; repository is archived |

Repository archival does not mean a hosted service is unavailable. The table is a
README/documentation comparison, not an exhaustive functional test. No claim is
made that competing tools are unsafe or that this idea is unprecedented.

## Decision

Build a small first-round diagnostic report that contains **no captured free text**,
including host/path and absolute timestamps. Preserve endpoint equality and request
ordinals so the capture owner can investigate follow-up questions locally. Do not
provide a hidden mapping sidecar. The deliberate loss of text is useful only when
status/timing triage is enough; otherwise use your organization's approved process.

All application code and synthetic examples in this repository were independently
written. Research involved public descriptions and documentation, not importing
competitor source. This is not an automated code-similarity clearance or a legal
opinion on originality. No third-party implementation or sample traffic is bundled.
