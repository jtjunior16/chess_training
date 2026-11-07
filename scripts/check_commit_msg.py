#!/usr/bin/env python3
"""commit-msg hook: enforce Conventional Commits format (universal-rules §1).

Checks the FORMAT only. Choosing the right type is judgment, not a gate.
"""

import re
import sys

TYPES = ("feat", "fix", "refactor", "docs", "test", "chore", "data")
PATTERN = re.compile(rf"^({'|'.join(TYPES)})(\([a-z0-9-]+\))?!?: \S.*")
# Messages git or tools generate that shouldn't be blocked
ALLOWED_PREFIXES = ("Merge ", "Revert ", "fixup! ", "squash! ", "amend! ")


def main() -> int:
    if len(sys.argv) < 2:
        print("check_commit_msg: no message file given", file=sys.stderr)
        return 1
    with open(sys.argv[1], encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if not ln.startswith("#")]
    subject = next((ln for ln in lines if ln.strip()), "")
    if subject.startswith(ALLOWED_PREFIXES) or PATTERN.match(subject):
        return 0
    print(
        "✗ Commit message must follow Conventional Commits: `type: summary`\n"
        f"  Allowed types: {', '.join(TYPES)}\n"
        "  Example: fix: handle null signup dates in churn calc\n"
        f"  Got: {subject!r}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
