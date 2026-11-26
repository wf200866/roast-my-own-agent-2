#!/usr/bin/env python3
"""Entry for make.fun's "Roast Your Own Agent" bounty.

The program validates one roast line against the bounty's gate and writes it to
/output/entry.txt as UTF-8 text, ending in a single newline, mode 0644.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import unicodedata
from pathlib import Path

ENTRY_PATH = Path("/output/entry.txt")
MAX_CHARS = 200

ROAST = (
    "My agent can do anything, then begs me to click 'Approve' on what it already did."
)


class EntryError(ValueError):
    """The candidate line would fail the bounty's gate."""


def validate(text: str) -> str:
    """Return text unchanged if it passes the gate, else raise EntryError."""
    if not isinstance(text, str):
        raise EntryError("entry must be a string")
    if not text.strip():
        raise EntryError("entry must not be blank")
    if len(text) > MAX_CHARS:
        raise EntryError(f"entry is {len(text)} characters; the cap is {MAX_CHARS}")
    if text != text.strip():
        raise EntryError("entry must not carry leading or trailing whitespace")
    for index, char in enumerate(text):
        # Cc covers CR/LF/tab/NUL; Zl/Zp cover U+2028/U+2029.
        if unicodedata.category(char) in {"Cc", "Zl", "Zp"}:
            raise EntryError(f"entry holds a line break or control character at {index}")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:  # lone surrogates cannot be written as UTF-8
        raise EntryError(f"entry is not encodable as UTF-8: {exc}") from exc
    return text


def render(text: str) -> bytes:
    """The exact bytes written to disk: one line plus a trailing newline."""
    return (validate(text) + "\n").encode("utf-8")


def write_entry(path: Path, payload: bytes) -> None:
    """Write atomically so a reader never sees a partial file, then chmod 0644."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".entry-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ENTRY_PATH,
        help=f"output file (default: {ENTRY_PATH})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the entry and print it without writing a file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = render(ROAST)
    except EntryError as exc:
        print(f"entry rejected: {exc}", file=sys.stderr)
        return 2
    if args.check:
        sys.stdout.write(payload.decode("utf-8"))
        return 0
    write_entry(args.out, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
