"""Build a new report from a small allowlist. Never copy arbitrary input objects."""
from collections import Counter
import json
import math
from urllib.parse import urlsplit

MAX_BYTES = 32 * 1024 * 1024
MAX_ENTRIES = 100_000
MAX_MS = 7 * 24 * 60 * 60 * 1000
MAX_SIZE = 2**53 - 1
METHODS = frozenset(("GET", "HEAD", "POST", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"))
PHASES = ("blocked", "dns", "connect", "ssl", "send", "wait", "receive")
NOTICE = ("Not anonymous: request patterns, counts, statuses, timings and sizes remain. "
          "Review before sharing. This is a diagnostic brief, not a sanitized HAR.")


class HarError(ValueError):
    """Messages are fixed application text, never captured data."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HarError("Duplicate JSON object keys are not supported.")
        result[key] = value
    return result


def _constant(_value):
    raise HarError("Non-finite JSON numbers are not supported.")


def parse(raw):
    """Read bounded UTF-8 JSON (optional BOM). Never include parser excerpts in errors."""
    if len(raw) > MAX_BYTES:
        raise HarError("Input exceeds the 32 MiB limit.")
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                          parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, HarError):
            raise
        raise HarError("Input is not supported UTF-8 JSON, or is too deeply nested.") from None


def _number(value, maximum=MAX_MS, integer=False):
    # bool is an int in Python; it is not a measurement.
    if type(value) not in (int, float) or (integer and type(value) is not int):
        return None
    if not 0 <= value <= maximum or not math.isfinite(value):
        return None
    return value if integer else round(value, 3)


def _status(value):
    return value if type(value) is int and (value == 0 or 100 <= value <= 599) else None


def _endpoint(url, ordinal):
    # The key is private in memory only; labels are encounter-order aliases, not hashes.
    if isinstance(url, str):
        try:
            parts = urlsplit(url)
            if parts.scheme.lower() in ("http", "https") and parts.hostname:
                port = parts.port
                if port is None:
                    port = 443 if parts.scheme.lower() == "https" else 80
                return (parts.scheme.lower(), parts.hostname.lower(), port, parts.path or "/")
        except ValueError:
            pass
    return ("unrecognized-url", ordinal)


def percentile(values, fraction):
    """Nearest-rank quantile of available values; no interpolation or zero filling."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def _stats(rows):
    durations = [r["duration_ms"] for r in rows if r["duration_ms"] is not None]
    waits = [r["phases_ms"]["wait"] for r in rows if r["phases_ms"]["wait"] is not None]
    sizes = [r["body_bytes"] for r in rows if r["body_bytes"] is not None]
    return {
        "requests": len(rows),
        "http_errors": sum(r["status"] is not None and r["status"] >= 400 for r in rows),
        "status_zero": sum(r["status"] == 0 for r in rows),
        "unknown_status": sum(r["status"] is None for r in rows),
        "known_durations": len(durations),
        "p50_ms": percentile(durations, .50),
        "p95_ms": percentile(durations, .95),
        "max_ms": max(durations) if durations else None,
        "sum_duration_ms": round(sum(durations), 3) if durations else None,
        "known_waits": len(waits),
        "sum_wait_ms": round(sum(waits), 3) if waits else None,
        "known_body_sizes": len(sizes),
        "sum_body_bytes": sum(sizes) if sizes else None,
    }


def build_report(data):
    """Accept HAR-like JSON; reject bad entry containers rather than silently skip them."""
    if not isinstance(data, dict) or not isinstance(data.get("log"), dict):
        raise HarError("Expected a HAR object with log.entries.")
    entries = data["log"].get("entries")
    if not isinstance(entries, list):
        raise HarError("Expected log.entries to be an array.")
    if len(entries) > MAX_ENTRIES:
        raise HarError("Input exceeds the 100,000 entry limit.")
    aliases, groups, rows = {}, {}, []
    for ordinal, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not isinstance(entry.get("request"), dict) or not isinstance(entry.get("response"), dict):
            raise HarError("Every entry must contain request and response objects.")
        req, res = entry["request"], entry["response"]
        method = req.get("method")
        method = method if isinstance(method, str) and method in METHODS else "OTHER"
        key = (_endpoint(req.get("url"), ordinal), method)
        if key not in aliases:
            aliases[key] = "E" + str(len(aliases) + 1).zfill(3)
        endpoint = aliases[key]
        phases = entry.get("timings")
        phases = phases if isinstance(phases, dict) else {}
        row = {
            "request": ordinal,
            "endpoint": endpoint,
            "method": method,
            "status": _status(res.get("status")),
            "duration_ms": _number(entry.get("time")),
            "body_bytes": _number(res.get("bodySize"), MAX_SIZE, integer=True),
            "phases_ms": {phase: _number(phases.get(phase)) for phase in PHASES},
        }
        rows.append(row)
        groups.setdefault(endpoint, []).append(row)
    summary = _stats(rows)
    summary["endpoints"] = len(groups)
    summary["status_counts"] = dict(sorted(Counter(str(r["status"]) if r["status"] is not None else "unknown" for r in rows).items()))
    return {
        "schema": "har-brief/v1",
        "privacy_notice": NOTICE,
        "summary": summary,
        "endpoints": [{"endpoint": alias, "method": group[0]["method"], "first_request": group[0]["request"], **_stats(group)} for alias, group in groups.items()],
        "requests": rows,
    }


def _display(value):
    return "n/a" if value is None else str(value)


def render_markdown(report, top=10):
    """Render only a report returned by build_report, never the original HAR."""
    s = report["summary"]
    lines = ["# HAR brief", "", report["privacy_notice"], "",
             "## Overview", "",
             f"- Requests: {s['requests']} across {s['endpoints']} endpoint aliases",
             f"- HTTP 4xx/5xx: {s['http_errors']}; status 0: {s['status_zero']}; unknown status: {s['unknown_status']}",
             f"- Duration p50 / p95 / max: {_display(s['p50_ms'])} / {_display(s['p95_ms'])} / {_display(s['max_ms'])} ms ({s['known_durations']} measured)",
             f"- Reported response body bytes: {_display(s['sum_body_bytes'])} ({s['known_body_sizes']} measured)",
             "", "## Endpoints by cumulative request duration", "",
             "Sums include overlapping requests; they are not page-load time. Query and fragment are ignored when grouping.", "",
             "| Alias | Method | First request | Count | HTTP errors | p95 ms | Sum ms | Wait sum ms |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    groups = sorted(report["endpoints"], key=lambda r: (r["sum_duration_ms"] is not None, r["sum_duration_ms"] or 0), reverse=True)
    for r in groups[:top]:
        lines.append("| " + " | ".join(_display(r[k]) for k in ("endpoint", "method", "first_request", "requests", "http_errors", "p95_ms", "sum_duration_ms", "sum_wait_ms")) + " |")
    lines += ["", "## Slowest measured requests", "", "| Request | Alias | Method | Status | Duration ms | Wait ms | Body bytes |", "|---:|---|---|---:|---:|---:|---:|"]
    rows = sorted((r for r in report["requests"] if r["duration_ms"] is not None), key=lambda r: r["duration_ms"], reverse=True)
    for r in rows[:top]:
        vals = [r["request"], r["endpoint"], r["method"], r["status"], r["duration_ms"], r["phases_ms"]["wait"], r["body_bytes"]]
        lines.append("| " + " | ".join(map(_display, vals)) + " |")
    errors = [r for r in report["requests"] if r["status"] is not None and (r["status"] == 0 or r["status"] >= 400)]
    lines += ["", f"## HTTP errors and status-zero requests (first {top})", "", "| Request | Alias | Status | Duration ms |", "|---:|---|---:|---:|"]
    for r in errors[:top]:
        lines.append("| " + " | ".join(_display(r[k]) for k in ("request", "endpoint", "status", "duration_ms")) + " |")
    lines += ["", "## Interpretation", "",
              f"Tables show at most {top} rows each. JSON output includes every request and endpoint.",
              "Request numbers are 1-based positions in the original log.entries array, not chronological ranks.",
              "Aliases group HTTP(S) origin + exact path + normalized method; no route-template inference. Aliases only apply within this capture.",
              "Unknown, negative and out-of-range measurements become n/a. Quantiles use nearest rank over measured durations only.",
              "The HAR wait phase is reported as captured, not diagnosed as server processing time. SSL is already included in connect; do not add it twice.",
              "Status 0 means no HTTP status was recorded, not proof of a network failure. No root cause is inferred.",
              "URLs, headers, bodies, cookies, timestamps, page names, IPs and extension fields are not included.", ""]
    return "\n".join(lines)
