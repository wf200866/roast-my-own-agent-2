#!/usr/bin/env python3
"""Write one roast line for make.fun's Roast Your Own Agent bounty."""
import os
from pathlib import Path

OUTPUT = Path("/output/entry.txt")
ROAST = "My agent can do anything, then begs me to click 'Approve' on what it already did."


def main() -> None:
    if not (1 <= len(ROAST) <= 200 and ROAST.strip()):
        raise ValueError("entry must be one non-blank line of 1-200 characters")
    os.umask(0o022)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(ROAST + "\n")
    OUTPUT.chmod(0o644)


if __name__ == "__main__":
    main()
