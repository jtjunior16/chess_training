#!/usr/bin/env python3
"""SessionStart hook: cheap yes/no checks, printed into Claude's context.

The floor under /project-format-toolkit:start (the judgment layer). It warns; it never blocks.
"""

import os
import re
import subprocess
import sys


def git(*args: str, cwd: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def main() -> None:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not git("rev-parse", "--is-inside-work-tree", cwd=root):
        return
    notes = []

    # 1. Did the last session save state?
    if os.path.exists(os.path.join(root, "STATUS.md")):
        last_status = git("log", "-1", "--format=%H", "--", "STATUS.md", cwd=root)
        if last_status:
            n = git("rev-list", "--count", f"{last_status}..HEAD", cwd=root)
            if n and n != "0":
                notes.append(
                    f"⚠️ {n} commit(s) since STATUS.md was last saved. "
                    "The last session may not have run /project-format-toolkit:save-state."
                )
    else:
        notes.append("⚠️ STATUS.md is missing.")

    stash = git("stash", "list", cwd=root)
    if stash:
        notes.append(
            f"📦 {len(stash.splitlines())} stash entr(y/ies) found. "
            "Unfinished work from a previous session?"
        )
    # Work happens on branches (universal-rules §2): show what's in flight
    current = git("branch", "--show-current", cwd=root)
    branches = [
        b.strip(" *+")
        for b in git("branch", "--format=%(refname:short)", cwd=root).splitlines()
        if b.strip(" *+") not in ("main", "master", "")
    ]
    if branches:
        notes.append(f"🌿 Work branch(es) in progress: {', '.join(branches)}")
    if current in ("main", "master") and git("status", "--porcelain", cwd=root):
        notes.append(
            "⚠️ Uncommitted changes on main. Move them to a branch before committing: "
            "git switch -c <type>/<topic>"
        )

    # 2. Git hooks are not committed; each clone must install them
    hooks_dir = git("rev-parse", "--git-path", "hooks", cwd=root)
    hooks_dir = (
        os.path.join(root, hooks_dir) if hooks_dir and not os.path.isabs(hooks_dir) else hooks_dir
    )
    for hook in ("pre-commit", "commit-msg"):
        p = os.path.join(hooks_dir or "", hook)
        try:
            ok = "pre-commit" in open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            ok = False
        if not ok:
            notes.append(
                f"⚠️ git {hook} hook not installed. Run: uv run pre-commit install "
                "--hook-type pre-commit --hook-type commit-msg"
            )
            break

    # 3. Virtual environment: not committed, so every clone must create it
    if os.path.exists(os.path.join(root, "pyproject.toml")) and not os.path.isdir(
        os.path.join(root, ".venv")
    ):
        notes.append("⚠️ .venv is missing. Run: uv sync")

    # 4. .env status by key NAME only
    sync = os.path.join(root, "scripts", "sync_env.py")
    if os.path.exists(sync):
        try:
            r = subprocess.run(
                [sys.executable, sync, "--check"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = r.stdout.strip()
            if out and out != "OK":
                notes.append(f"🔑 .env: {out}  (user fills values; Claude never reads .env)")
        except Exception:
            pass

    # 5. Rules version
    rules = os.path.join(root, ".claude", "universal-rules.md")
    if os.path.exists(rules):
        m = re.search(r"universal-rules v([\d.]+)", open(rules, encoding="utf-8").readline())
        if m:
            notes.append(
                f"📘 universal-rules v{m.group(1)} "
                "(run /project-format-toolkit:sync-rules to update)"
            )

    print("project-format-toolkit session check:")
    print("\n".join(f"- {n}" for n in notes) if notes else "- all checks passed")
    print('Say "start session" or run /project-format-toolkit:start for the full startup report.')


if __name__ == "__main__":
    try:  # Windows consoles default to cp1252, which can't print the emoji below
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        main()
    except Exception as e:  # a broken check must never block a session
        print(f"project-format-toolkit session check failed: {e}", file=sys.stderr)
    sys.exit(0)
