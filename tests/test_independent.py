"""Independent adversarial checks. All captures are generated, not user data."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from har_brief.core import HarError, MAX_BYTES, build_report, parse, render_markdown

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "PRIVATE_CANARY_4e29d0"


def entry(url="https://example.invalid/item?a=one", method="GET", status=200, duration=10):
    return {"request": {"url": url, "method": method},
            "response": {"status": status, "bodySize": 25},
            "time": duration, "timings": {"wait": 3, "connect": 5, "ssl": 2}}


def capture(*entries):
    return {"log": {"entries": list(entries)}}


class IndependentCoreTests(unittest.TestCase):
    def test_free_text_never_copied(self):
        row = entry("https://" + SENTINEL + ":password@private.invalid/" + SENTINEL + "?secret=" + SENTINEL,
                    method=SENTINEL)
        row.update({"comment": SENTINEL, "serverIPAddress": SENTINEL,
                    "startedDateTime": SENTINEL, "_webSocketMessages": [{"data": SENTINEL}]})
        row["request"].update({"cookies": [{"name": SENTINEL, "value": SENTINEL}],
                                "headers": [{"name": SENTINEL, "value": SENTINEL}],
                                "postData": {"text": SENTINEL}, "queryString": [{"value": SENTINEL}]})
        row["response"].update({"content": {"text": SENTINEL, "mimeType": SENTINEL},
                                 "statusText": SENTINEL, "headers": [{"value": SENTINEL}],
                                 "redirectURL": SENTINEL, "_failureText": SENTINEL})
        data = capture(row)
        data["log"].update({"creator": {"name": SENTINEL}, "pages": [{"title": SENTINEL}], SENTINEL: SENTINEL})
        report = build_report(parse(json.dumps(data).encode()))
        for rendered in (json.dumps(report), render_markdown(report)):
            self.assertNotIn(SENTINEL, rendered)
            self.assertNotIn("private.invalid", rendered)
        self.assertEqual(report["requests"][0]["method"], "OTHER")

    def test_malicious_types_become_unknown(self):
        for bad in (True, False, SENTINEL, [], {}, -1, float("inf"), float("nan"), 10**200):
            row = entry(status=bad, duration=bad)
            row["response"]["bodySize"] = bad
            row["timings"]["wait"] = bad
            with self.subTest(bad=repr(bad)):
                report = build_report(capture(row))
                result = report["requests"][0]
                for key in ("status", "duration_ms", "body_bytes"):
                    self.assertIsNone(result[key])
                self.assertIsNone(result["phases_ms"]["wait"])
                json.dumps(report, allow_nan=False)

    def test_known_zero_is_not_unknown(self):
        row = entry(status=0, duration=0)
        row["response"]["bodySize"] = 0
        report = build_report(capture(row))
        self.assertEqual(report["summary"]["known_durations"], 1)
        self.assertEqual(report["summary"]["status_zero"], 1)
        self.assertEqual(report["summary"]["http_errors"], 0)
        self.assertEqual(report["summary"]["sum_body_bytes"], 0)

    def test_nearest_rank_and_unknown_exclusion(self):
        rows = [entry(duration=i) for i in range(1, 21)] + [entry(duration=-1)]
        s = build_report(capture(*rows))["summary"]
        self.assertEqual((s["p50_ms"], s["p95_ms"], s["known_durations"]), (10, 19, 20))
        self.assertEqual(s["sum_duration_ms"], 210)

    def test_alias_grouping_and_method_separation(self):
        report = build_report(capture(entry("https://EXAMPLE.invalid:443/p?a=one#frag"),
                                      entry("https://example.invalid/p?a=two"),
                                      entry("https://example.invalid/p", "POST"),
                                      entry("http://example.invalid/p"),
                                      entry("https://example.invalid/q")))
        self.assertEqual([r["endpoint"] for r in report["requests"]], ["E001", "E001", "E002", "E003", "E004"])
        self.assertEqual(report["endpoints"][0]["requests"], 2)

    def test_port_zero_is_not_default_port(self):
        report = build_report(capture(entry("http://example.invalid:0/p"), entry("http://example.invalid:80/p")))
        self.assertEqual(report["summary"]["endpoints"], 2)

    def test_missing_urls_not_invented_as_same_endpoint(self):
        rows = [entry(url=None), entry(url=None), entry(url="http://[broken"), entry(url="data:private")]
        self.assertEqual(build_report(capture(*rows))["summary"]["endpoints"], 4)

    def test_invalid_json_rejected_without_echo(self):
        values = [("{\"" + SENTINEL + "\": } ").encode(), b'{"x":NaN}', b'{"x":Infinity}',
                  b'{"log":{},"log":{}}', b'\xff', b'[' * 10000 + b']' * 10000]
        for raw in values:
            with self.subTest(raw_size=len(raw)):
                with self.assertRaises(HarError) as raised:
                    parse(raw)
                self.assertNotIn(SENTINEL, str(raised.exception))

    def test_utf8_bom_and_size_limit(self):
        self.assertEqual(parse(b'\xef\xbb\xbf{"log":{"entries":[]}}'), capture())
        with self.assertRaises(HarError):
            parse(b' ' * (MAX_BYTES + 1))

    def test_bad_entry_containers_rejected(self):
        for data in ([], {}, {"log": []}, {"log": {"entries": {}}}, capture(None), capture({}), capture({"request": [], "response": {}})):
            with self.subTest(data=data):
                with self.assertRaises(HarError):
                    build_report(data)

    def test_entry_limit(self):
        with self.assertRaises(HarError):
            build_report(capture(*([entry()] * 100001)))

    def test_empty_capture(self):
        report = build_report(capture())
        self.assertEqual(report["summary"]["requests"], 0)
        self.assertIsNone(report["summary"]["p95_ms"])
        self.assertIn("n/a", render_markdown(report))


class IndependentCliTests(unittest.TestCase):
    def run_cli(self, *args, data=None):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        return subprocess.run([sys.executable, "-m", "har_brief", *args],
                              input=data, capture_output=True, env=env, timeout=5)

    def test_stdin_and_http_error_exit(self):
        raw = json.dumps(capture(entry(status=503))).encode()
        result = self.run_cli("-", "--format", "json", "--fail-on-http-error", data=raw)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["summary"]["http_errors"], 1)
        self.assertEqual(result.stderr, b"")

    def test_parse_error_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            result = self.run_cli("-", "-o", str(path), data=SENTINEL.encode())
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(SENTINEL.encode(), result.stderr)
            self.assertFalse(path.exists())
            self.assertEqual(result.stdout, b"")

    def test_never_overwrite_input_or_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.har"
            raw = json.dumps(capture(entry())).encode()
            path.write_bytes(raw)
            result = self.run_cli(str(path), "-o", str(path))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_bytes(), raw)
            link = Path(tmp) / "output.json"
            link.symlink_to(path)
            result = self.run_cli(str(path), "-o", str(link))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(path.read_bytes(), raw)

    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_output_private_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            result = self.run_cli("-", "-o", str(path), data=json.dumps(capture()).encode())
            self.assertEqual(result.returncode, 0)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires FIFO")
    def test_fifo_rejected_without_waiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / "capture.har"
            os.mkfifo(fifo)
            result = self.run_cli(str(fifo))
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"regular file", result.stderr)


if __name__ == "__main__":
    unittest.main()
