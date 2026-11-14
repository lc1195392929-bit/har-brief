import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_core import entry, har

ROOT = Path(__file__).resolve().parents[1]


def run(*args, data=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, "-m", "har_brief", *args], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)


class CliTests(unittest.TestCase):
    def test_stdin_json(self):
        p = run("-", "--format", "json", data=json.dumps(har(entry())).encode())
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["schema"], "har-brief/v1")
        self.assertEqual(p.stderr, b"")

    def test_http_exit_code(self):
        for status, expected in [(200, 0), (0, 0), (404, 1), (500, 1)]:
            p = run("-", "--fail-on-http-error", data=json.dumps(har(entry(status=status))).encode())
            self.assertEqual(p.returncode, expected)
            self.assertIn(b"# HAR brief", p.stdout)

    def test_input_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "input.har"
            original = json.dumps(har(entry()))
            f.write_text(original)
            p = run(str(f), "-o", str(f))
            self.assertEqual(p.returncode, 2)
            self.assertEqual(f.read_text(), original)
            self.assertEqual(p.stdout, b"")

    def test_output_and_mode(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "report.md"
            p = run("-", "-o", str(f), data=json.dumps(har(entry())).encode())
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("# HAR brief", f.read_text())
            if os.name == "posix":
                self.assertEqual(f.stat().st_mode & 0o777, 0o600)
            p = run("-", "-o", str(f), data=json.dumps(har(entry())).encode())
            self.assertEqual(p.returncode, 2)

    @unittest.skipUnless(os.name == "posix", "POSIX symlinks")
    def test_output_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "target"
            target.write_text("do not change")
            link = Path(d) / "link"
            link.symlink_to(target)
            p = run("-", "-o", str(link), data=json.dumps(har(entry())).encode())
            self.assertEqual(p.returncode, 2)
            self.assertEqual(target.read_text(), "do not change")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO")
    def test_fifo_does_not_hang(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "fifo"
            os.mkfifo(f)
            p = run(str(f))
            self.assertEqual(p.returncode, 2)
            self.assertIn(b"regular file", p.stderr)

    def test_errors_do_not_echo_data(self):
        secret = b"SYNTHETIC_PRIVATE_CANARY"
        p = run("-", data=b'{"bad": "' + secret)
        self.assertEqual(p.returncode, 2)
        self.assertNotIn(secret, p.stderr + p.stdout)
        self.assertNotIn(b"Traceback", p.stderr)
        p = run("/does/not/exist/" + secret.decode())
        self.assertEqual(p.returncode, 2)
        self.assertNotIn(secret, p.stderr + p.stdout)

    def test_invalid_input_creates_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "report.md"
            p = run("-", "-o", str(f), data=b"invalid")
            self.assertEqual(p.returncode, 2)
            self.assertFalse(f.exists())

    def test_invalid_top(self):
        for value in ["0", "101", "nope"]:
            p = run("-", "--top", value, data=b"{}")
            self.assertEqual(p.returncode, 2)

    def test_version(self):
        p = run("--version")
        self.assertEqual(p.stdout, b"0.1.0\n")


if __name__ == "__main__":
    unittest.main()
