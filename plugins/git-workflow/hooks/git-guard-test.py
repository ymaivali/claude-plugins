#!/usr/bin/env python3
"""Test suite for git-guard.py. Run after any edit to the guard:

    python3 ~/.claude/hooks/git-guard-test.py

Each case is (expected, command) where expected is "deny" or "allow".
The false-positive cases matter more than the deny cases: a guard that
blocks ordinary shell gets switched off, which is worse than no guard.
"""
import json
import subprocess
import sys
from pathlib import Path

GUARD = str(Path(__file__).with_name("git-guard.py"))

CASES = [
    # --- must be denied: force push, every spelling and position ---
    ("deny", "git push --force"),
    ("deny", "git push origin main --force"),
    ("deny", "git push -f origin main"),
    ("deny", "git push origin main -f"),
    ("deny", "git push --force-with-lease"),
    ("deny", "git push --force-if-includes origin main"),
    ("deny", "git -C /some/repo push origin main --force"),
    ("deny", "git --no-pager push origin main --force"),
    ("deny", "cd /tmp/x && git push --force"),
    ("deny", "git push origin +main"),
    ("deny", "git push origin +refs/heads/main"),
    ("deny", "git push origin :stale-branch"),
    ("deny", "git push --delete origin feature/x"),
    ("deny", "git push -d origin feature/x"),
    ("deny", "git push --mirror origin"),
    # --- other destructive git ---
    ("deny", "git reset --hard HEAD~1"),
    ("deny", "git reset --hard"),
    ("deny", "git clean -fd"),
    ("deny", "git clean -df"),
    ("deny", "git clean --force"),
    ("deny", "git checkout --force main"),
    ("deny", "git branch -D feature/unmerged"),
    ("deny", "git status && git push --force"),

    # --- must be allowed: ordinary git ---
    ("allow", "git push"),
    ("allow", "git push origin main"),
    ("allow", "git push -u origin feature/describe-by-sex"),
    ("allow", "git push --dry-run"),
    ("allow", "git push --set-upstream origin feature/x"),
    ("allow", "git pull"),
    ("allow", "git fetch --prune"),
    ("allow", "git status --short --branch"),
    ("allow", "git log --oneline --graph -10"),
    ("allow", "git commit -m 'fix: broken thing'"),
    ("allow", "git commit -am 'note: see docs/readme'"),
    ("allow", "git switch -c feature/new-thing"),
    ("allow", "git branch -d feature/merged"),
    ("allow", "git branch -vv"),
    ("allow", "git checkout main"),
    ("allow", "git reset HEAD~1"),            # soft reset: keeps the work
    ("allow", "git reset --soft HEAD~1"),
    ("allow", "git diff --name-only"),
    ("allow", "git merge origin/main"),
    ("allow", "git merge --abort"),

    # --- false-positive traps: the first implementation failed ALL of these ---
    # the word "push" in prose plus a -f shell test operator
    ("allow", 'echo "runs BEFORE pushing"; [ -f "$x" ] && git add -A'),
    # -f as an argument to a different program in the same line
    ("allow", "grep -f patterns.txt data.csv && git commit -m done"),
    ("allow", "rm -f stale.log && git add -A"),
    ("allow", "find . -name '*.R' && git push origin main"),
    # --force belonging to another tool
    ("allow", "npm install --force"),
    ("allow", "npm install --force && git status"),
    ("allow", "quarto render --force && git add -A"),
    # a filename that merely contains the word
    ("allow", "git add notes-about-force-push.md"),
    ("allow", "git commit -m 'document why we never force-push'"),
    # colon inside a message, not a refspec
    ("allow", "git push origin main:main"),   # explicit same-name refspec, not a delete
]


def decide(command: str) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    out = subprocess.run([sys.executable, GUARD], input=payload,
                         capture_output=True, text=True).stdout.strip()
    if not out:
        return "allow"
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"]


def main():
    failures = []
    for expected, command in CASES:
        got = decide(command)
        if got != expected:
            failures.append((expected, got, command))

    print(f"{len(CASES)} cases: {len(CASES) - len(failures)} passed, {len(failures)} failed")
    for expected, got, command in failures:
        print(f"  MISMATCH expected={expected} got={got}  {command}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
