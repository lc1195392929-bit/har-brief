"""Bounded local I/O. No overwrite, upload, telemetry or raw-data logging."""
import argparse
import json
import os
import stat
import sys
from . import __version__
from .core import HarError, MAX_BYTES, build_report, parse, render_markdown


def _top(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 100") from None
    if not 1 <= number <= 100:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 100")
    return number


def _read(path):
    if path == "-":
        return sys.stdin.buffer.read(MAX_BYTES + 1)
    # O_NONBLOCK prevents an unexpected FIFO from blocking before fstat.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise HarError("Input must be a regular file, or use - for stdin.")
        return stream.read(MAX_BYTES + 1)


def _write(path, content):
    if path is None:
        sys.stdout.write(content)
        return
    # Exclusive creation also rejects existing symlinks and input == output.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build an offline, data-minimized HAR diagnostic brief. Not a sanitized HAR or anonymity guarantee.")
    parser.add_argument("input", help="HAR file, or - for stdin")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("-o", "--output", help="Create a NEW output file; existing paths are never overwritten")
    parser.add_argument("--top", type=_top, default=10, help="Markdown table row limit (1-100, default 10)")
    parser.add_argument("--fail-on-http-error", action="store_true", help="Exit 1 after writing if any recorded HTTP status is 4xx/5xx")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        report = build_report(parse(_read(args.input)))
        result = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n" if args.format == "json" else render_markdown(report, args.top)
        _write(args.output, result)
    except HarError as exc:
        print("har-brief: " + str(exc), file=sys.stderr)
        return 2
    except FileExistsError:
        print("har-brief: output already exists; nothing was overwritten.", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 2
    except (OSError, UnicodeError, RecursionError):
        print("har-brief: could not read input or write output; check paths, permissions and available space.", file=sys.stderr)
        return 2
    return int(args.fail_on_http_error and report["summary"]["http_errors"] > 0)
