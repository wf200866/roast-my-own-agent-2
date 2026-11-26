#!/usr/bin/env python3
"""Roast My Own Agent entry: one line, written to /output/entry.txt.

The line is checked against the bounty gate before anything is written:
one line, 1..200 characters, no surrounding whitespace, no control or
line-break characters anywhere, valid UTF-8. The file on disk is the line
plus a single trailing newline, mode 0644. Writing goes through a temp
file next to the destination and an atomic rename, so a reader never
catches a half-written entry.
"""

import argparse
import os
import sys
import tempfile
import unicodedata
from pathlib import Path

OUT_DEFAULT = Path("/output/entry.txt")
CAP = 200
FILE_MODE = 0o644

# The roast, 81 characters. The angle: the approval-link agent — it can do
# anything on its own except the one thing it actually needs, and ends up
# begging its human to click "Approve" on work it already did.
ROAST = (
    "My agent can do anything, then begs me to click 'Approve' on what it already did."
)


class EntryProblem(ValueError):
    """The line would not pass the bounty's gate."""


def check_line(text):
    """Raise EntryProblem unless *text* passes the gate; return it as-is."""
    if not isinstance(text, str):
        raise EntryProblem("the entry has to be text")
    if not text.strip():
        raise EntryProblem("the entry is blank")
    if len(text) > CAP:
        raise EntryProblem("the entry runs %d characters; the cap is %d" % (len(text), CAP))
    if text.strip() != text:
        raise EntryProblem("the entry must not start or end with whitespace")
    bad = next(
        (pos for pos, ch in enumerate(text) if unicodedata.category(ch) in ("Cc", "Zl", "Zp")),
        None,
    )
    if bad is not None:
        # Cc covers CR, LF, tab and NUL; Zl/Zp cover U+2028 and U+2029.
        raise EntryProblem("the entry carries a control or line-break character at %d" % bad)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        # A lone surrogate has no UTF-8 encoding, so it can never be stored.
        raise EntryProblem("the entry is not valid UTF-8: %s" % exc) from exc
    return text


def prepare(text):
    """The exact bytes for disk: the validated line plus one newline."""
    return (check_line(text) + "\n").encode("utf-8")


def publish(path, payload):
    """Atomically write *payload* to *path* and set mode 0644."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".roast-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, FILE_MODE)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def build_parser():
    """Command line: destination, plus a validate-only mode."""
    parser = argparse.ArgumentParser(description="Write the one-line roast to /output/entry.txt.")
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DEFAULT,
        help="destination file (default: %(default)s)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the line and print it without writing a file",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        payload = prepare(ROAST)
    except EntryProblem as exc:
        print("entry rejected: %s" % exc, file=sys.stderr)
        return 2
    if args.check:
        sys.stdout.write(payload.decode("utf-8"))
        return 0
    try:
        publish(args.out, payload)
    except OSError as exc:
        # A failed write should end with a plain error, not a traceback.
        print("error: cannot write %s: %s" % (args.out, exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
