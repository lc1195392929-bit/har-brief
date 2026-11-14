import copy
import json
import math
import unittest
from har_brief.core import HarError, MAX_BYTES, MAX_ENTRIES, build_report, parse, render_markdown


def entry(url="https://example.test/a?token=synthetic_secret", duration=100, status=200, **kwargs):
    result = {"time": duration, "request": {"method": "GET", "url": url}, "response": {"status": status, "bodySize": 20}, "timings": {"wait": 70, "connect": 20, "ssl": 10, "receive": 10}}
    result.update(kwargs)
    return result


def har(*entries):
    return {"log": {"entries": list(entries)}}


class CoreTests(unittest.TestCase):
    def test_metrics(self):
        report = build_report(har(entry(duration=100), entry(duration=200, status=404), entry(duration=-1, status=0), entry(duration=400, status=500)))
        s = report["summary"]
        self.assertEqual((s["requests"], s["http_errors"], s["status_zero"], s["known_durations"]), (4, 2, 1, 3))
        self.assertEqual((s["p50_ms"], s["p95_ms"], s["sum_duration_ms"]), (200, 400, 700))
        self.assertEqual(s["sum_body_bytes"], 80)
        self.assertEqual(report["requests"][0]["duration_ms"], 100)  # SSL not added twice.

    def test_empty(self):
        report = build_report(har())
        self.assertEqual(report["summary"]["requests"], 0)
        self.assertIsNone(report["summary"]["p95_ms"])
        self.assertIn("n/a", render_markdown(report))

    def test_aliases(self):
        entries = [entry("https://USER:PASSWORD@EXAMPLE.test:443/a?token=one#fragment"), entry("https://example.test/a?token=two"), entry("https://example.test/b"), entry("http://example.test/a"), entry("https://example.test/a")]
        entries[-1]["request"]["method"] = "POST"
        r = build_report(har(*entries))
        self.assertEqual([e["endpoint"] for e in r["requests"]], ["E001", "E001", "E002", "E003", "E004"])
        self.assertEqual(r["endpoints"][0]["first_request"], 1)
        self.assertEqual(r["endpoints"][0]["requests"], 2)

    def test_missing_bad_urls_do_not_merge(self):
        r = build_report(har(entry("data:text/plain,secret"), entry(None), entry("https://[oops"), entry("https://example.test:bad/a")))
        self.assertEqual(r["summary"]["endpoints"], 4)

    def test_missing_numeric_values(self):
        for value in [-1, None, True, False, "700", [], {}, math.inf, math.nan, 10**1000]:
            e = entry(duration=value, status=value)
            e["response"]["bodySize"] = value
            e["timings"]["wait"] = value
            row = build_report(har(e))["requests"][0]
            self.assertIsNone(row["duration_ms"])
            self.assertIsNone(row["status"])
            self.assertIsNone(row["body_bytes"])
            self.assertIsNone(row["phases_ms"]["wait"])

    def test_round_and_zero(self):
        r = build_report(har(entry(duration=.123456), entry(duration=0, status=0)))
        self.assertEqual(r["requests"][0]["duration_ms"], .123)
        self.assertEqual(r["requests"][1]["duration_ms"], 0)

    def test_no_raw_text(self):
        secret = "SYNTHETIC_PRIVATE_CANARY_789"
        e = entry("https://" + secret + ".test/" + secret + "?q=" + secret)
        for key in ["comment", "serverIPAddress", "connection", "startedDateTime", "pageref", "_webSocketMessages"]:
            e[key] = secret
        e["request"].update({"method": secret, "headers": [{"name": secret, "value": secret}], "cookies": [{"name": secret, "value": secret}], "queryString": [{"name": secret, "value": secret}], "postData": {"text": secret}})
        e["response"].update({"statusText": secret, "redirectURL": secret, "headers": [{"name": secret, "value": secret}], "cookies": [{"name": secret, "value": secret}], "content": {"text": secret, "mimeType": secret}, "_unknown": secret})
        data = har(e)
        data[secret] = secret
        data["log"].update({"comment": secret, "creator": {"name": secret}, "pages": [{"title": secret}]})
        report = build_report(data)
        self.assertNotIn(secret, json.dumps(report))
        self.assertNotIn(secret, render_markdown(report))
        self.assertEqual(report["requests"][0]["method"], "OTHER")

    def test_does_not_mutate_input(self):
        data = har(entry())
        before = copy.deepcopy(data)
        build_report(data)
        self.assertEqual(data, before)

    def test_method_not_hashable(self):
        for value in ({}, [], None, 1):
            e = entry()
            e["request"]["method"] = value
            self.assertEqual(build_report(har(e))["requests"][0]["method"], "OTHER")

    def test_status_range(self):
        for value in [99, 600, 200.0, "200", True]:
            self.assertIsNone(build_report(har(entry(status=value)))["requests"][0]["status"])

    def test_bad_shapes(self):
        for data in [[], None, {}, {"log": []}, {"log": {"entries": {}}}, har(None), har({}), har({"request": [], "response": {}})]:
            with self.assertRaises(HarError):
                build_report(data)

    def test_parse(self):
        data = har(entry())
        self.assertEqual(parse(b"\xef\xbb\xbf" + json.dumps(data).encode()), data)
        for raw in [b"NOT_VALID_SECRET", b"\xff", b'{"a":1,"a":2}', b'{"a": NaN}', b'{"a": Infinity}', b"[" * 2000]:
            with self.assertRaises(HarError) as ctx:
                parse(raw)
            self.assertNotIn("SECRET", str(ctx.exception))

    def test_limits(self):
        with self.assertRaises(HarError):
            parse(b" " * (MAX_BYTES + 1))
        with self.assertRaises(HarError):
            build_report({"log": {"entries": [None] * (MAX_ENTRIES + 1)}})

    def test_markdown_limits(self):
        r = build_report(har(*(entry(duration=i, status=404) for i in range(20))))
        text = render_markdown(r, top=3)
        self.assertIn("at most 3", text)
        self.assertIn("| 20 | E001", text)
        self.assertEqual(text.count("| E001 | GET |"), 4)


if __name__ == "__main__":
    unittest.main()
