#!/usr/bin/env python3
"""sync_env.py: keep .env's key list in step with .env.example (universal-rules §5).

  uv run --no-project python scripts/sync_env.py          create .env if missing,
                                                          else append missing keys (blank)
  uv run --no-project python scripts/sync_env.py --check  report status, change nothing

Works on Windows, macOS and Linux. Prints key NAMES only, never values.
"""

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE, ENV = ROOT / ".env.example", ROOT / ".env"
KEY_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def keys(path: Path) -> dict[str, bool]:
    """Map key name -> has a non-blank value. Values themselves are never kept."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = KEY_LINE.match(line)
        if m:
            out[m.group(1)] = bool(m.group(2).strip())
    return out


def main() -> int:
    if not EXAMPLE.exists():
        print("No .env.example found.", file=sys.stderr)
        return 1
    check = "--check" in sys.argv[1:]

    if not ENV.exists():
        if check:
            print("MISSING_FILE .env (run: uv run --no-project python scripts/sync_env.py)")
            return 0
        ENV.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        print("Created .env from .env.example. Fill in the blank values.")
        return 0

    wanted, have = keys(EXAMPLE), keys(ENV)
    missing = sorted(set(wanted) - set(have))

    if check:
        blank = sorted(k for k, filled in have.items() if not filled)
        if missing:
            print("MISSING_KEYS " + " ".join(missing))
        if blank:
            print("BLANK_KEYS " + " ".join(blank))
        if not missing and not blank:
            print("OK")
        return 0

    if not missing:
        print(".env already has every key in .env.example.")
        return 0
    with ENV.open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n# Added by sync_env.py on {dt.date.today().isoformat()}. Fill in values\n")
        for k in missing:
            f.write(f"{k}=\n")
    print(f"Added {len(missing)} missing key(s) to .env (fill in values):")
    for k in missing:
        print(f"  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
