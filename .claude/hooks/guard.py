#!/usr/bin/env python3
"""PreToolUse gate for Claude's actions (universal-rules §2 and §5).

Blocks (exit 2, reason on stderr so Claude sees it):
  1. Reading, editing or grepping .env files (except .env.example)
  2. Bash commands that touch .env, except the allowed paths:
     scripts/sync_env.py, `cp .env.example .env` when .env doesn't exist,
     and `--env-file .env` (loads values into a tool without showing them)
  3. Force-pushes: plain --force anywhere; any force to main/master
  4. Creating a branch whose name breaks `type/short-kebab-description`
  5. Committing on main/master, or pushing to it (changes reach main via PRs).
     Exceptions: the first commit of an empty repo, and its first push
     (no origin/main yet), so a new project can be published.

Watches Claude only. Git hooks (.pre-commit-config.yaml) cover every commit.
"""

import json
import os
import re
import subprocess
import sys

BRANCH_TYPES = ("feat", "fix", "refactor", "docs", "test", "chore", "data")
BRANCH_RE = re.compile(rf"^({'|'.join(BRANCH_TYPES)})/[a-z0-9]+(-[a-z0-9]+)*$")
PROTECTED_BRANCHES = {"main", "master"}

# .env, .env.local, .env.production … but NOT .env.example
ENV_TOKEN = re.compile(r"(?<![\w.-])\.env(?:\.(?!example\b)[\w-]+)?(?![\w.-])")


def block(reason: str) -> None:
    print(f"Blocked by project-format-toolkit guard: {reason}", file=sys.stderr)
    sys.exit(2)


def is_protected_env_path(path: str) -> bool:
    name = re.split(r"[\\/]", path or "")[-1]  # handles Windows and Unix paths
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def current_branch(cwd: str) -> str:
    try:
        out = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],  # works before the first commit too
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def git_ok(cwd: str, *args: str) -> bool:
    try:
        r = subprocess.run(["git", *args], cwd=cwd or None, capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def segments(cmd: str) -> list:
    return re.split(r"&&|\|\||;|\|", cmd)


NO_MAIN = (
    "changes reach main only through a PR (universal-rules §2). Create a branch first: "
    "`git switch -c feat/<short-description>`, commit there, push it, then `gh pr create`."
)


def check_main_commit(cmd: str, cwd: str) -> None:
    for seg in segments(cmd):
        if not re.search(r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+commit(?![\w-])", seg):
            continue
        if current_branch(cwd) not in PROTECTED_BRANCHES:
            continue
        if not git_ok(cwd, "rev-parse", "--verify", "--quiet", "HEAD"):
            continue  # first commit of an empty repo: nothing to PR against yet
        block(f"never commit on main: {NO_MAIN}")


def check_main_push(cmd: str, cwd: str) -> None:
    for seg in segments(cmd):
        if not re.search(r"\bgit\b.*\bpush\b", seg) or "--delete" in seg:
            continue
        after = seg.split("push", 1)[1].split()
        positional = [t for t in after if not t.startswith("-")]
        remote = positional[0] if positional else "origin"
        refspecs = positional[1:]
        if refspecs:
            targets = {r.split(":")[-1].removeprefix("refs/heads/").lstrip("+") for r in refspecs}
        else:
            targets = {current_branch(cwd)}
        hit = targets & PROTECTED_BRANCHES
        if not hit:
            continue
        b = sorted(hit)[0]
        if not git_ok(cwd, "rev-parse", "--verify", "--quiet", f"refs/remotes/{remote}/{b}"):
            continue  # first publication of a new repo: the remote has no main yet
        block(f"never push to main: {NO_MAIN}")


def check_env_in_bash(cmd: str, cwd: str) -> None:
    allowed = cmd
    # Allowed path 1: the sync script (prints key names only)
    allowed = re.sub(r"(\./|\.\\)?scripts[/\\]sync_env\.py(\s+--check)?", " ", allowed)
    # Allowed path 2: loading .env into a tool without displaying it
    allowed = re.sub(r"--env-file[ =]\.env\b", " ", allowed)
    # Allowed path 3: create .env from the template, only if it doesn't exist yet
    if re.search(r"\bcp\s+(\./)?\.env\.example\s+(\./)?\.env\b", allowed):
        if os.path.exists(os.path.join(cwd or ".", ".env")):
            block(
                ".env already exists. Use scripts/sync_env.py to add missing keys "
                "instead of overwriting the user's values."
            )
        allowed = re.sub(r"\bcp\s+(\./)?\.env\.example\s+(\./)?\.env\b", " ", allowed)
    if ENV_TOKEN.search(allowed):
        block(
            "Claude never reads or edits .env (universal-rules §5). Use "
            "scripts/sync_env.py to add keys, and ask the user to fill in values."
        )


def check_force_push(cmd: str, cwd: str) -> None:
    for seg in re.split(r"&&|\|\||;|\|", cmd):
        if not re.search(r"\bgit\b.*\bpush\b", seg):
            continue
        plain_force = re.search(r"(?<![\w-])(--force(?!-with-lease)|-f)(?![\w-])", seg)
        lease = "--force-with-lease" in seg
        plus_refspec = re.search(r"\s\+\S+", seg)
        if not (plain_force or lease or plus_refspec):
            continue
        if plain_force or plus_refspec:
            block(
                "plain force-push is not allowed. On your own feature branch use "
                "--force-with-lease. Never force-push main (universal-rules §2)."
            )
        # Positional args after `push`: [remote] [refspec...]
        after = seg.split("push", 1)[1].split()
        positional = [t for t in after if not t.startswith("-")]
        refspecs = positional[1:]
        if refspecs:
            targets = {r.split(":")[-1].removeprefix("refs/heads/") for r in refspecs}
        else:
            targets = {current_branch(cwd)}  # no refspec: pushes the current branch
        if targets & PROTECTED_BRANCHES:
            block("never force-push main (universal-rules §2).")


def check_branch_name(cmd: str) -> None:
    patterns = [
        r"\bgit\s+(?:checkout|co)\s+-[bB]\s+(\S+)",
        r"\bgit\s+switch\s+(?:-c|-C|--create|--force-create)\s+(\S+)",
        r"\bgit\s+branch\s+(?!-)(\S+)",
    ]
    for pat in patterns:
        for name in re.findall(pat, cmd):
            name = name.strip("'\"")
            if name in PROTECTED_BRANCHES:
                continue
            if not BRANCH_RE.match(name):
                block(
                    f"branch name {name!r} must be `type/short-kebab-description` "
                    f"(types: {', '.join(BRANCH_TYPES)}), e.g. feat/churn-by-plan."
                )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # never break Claude on malformed input
    tool = data.get("tool_name", "")
    tin = data.get("tool_input", {}) or {}
    cwd = data.get("cwd", "") or os.getcwd()

    if tool in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = tin.get("file_path") or tin.get("notebook_path") or ""
        if is_protected_env_path(path):
            block("Claude never reads or edits .env (universal-rules §5).")
    elif tool == "Grep":
        if is_protected_env_path(tin.get("path", "")) or ENV_TOKEN.search(
            tin.get("glob", "") or ""
        ):
            block("Claude never searches inside .env (universal-rules §5).")
    elif tool in ("Bash", "PowerShell"):
        cmd = tin.get("command", "") or ""
        check_env_in_bash(cmd, cwd)
        check_force_push(cmd, cwd)
        check_main_commit(cmd, cwd)
        check_main_push(cmd, cwd)
        check_branch_name(cmd)
    sys.exit(0)


if __name__ == "__main__":
    main()
