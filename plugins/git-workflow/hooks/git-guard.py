#!/usr/bin/env python3
"""PreToolUse hook (matcher: Bash) — block git commands that destroy work
git cannot recover: force-pushes, remote branch deletion, hard resets,
forced cleans and forced checkouts.

Why a hook and not a permission rule: rules match by exact string or
trailing-* prefix only, so "Bash(git push --force*)" does NOT match
"git push origin main --force".

Why Python and not grep: a substring scan produces false positives on
ordinary shell. The first version blocked

    echo "runs BEFORE pushing"; [ -f "$x" ] && ...; git add -A

because the text contained "push" and a "-f". This parses the command into
segments and only inspects the arguments of an actual git subcommand.

Reads the PreToolUse payload on stdin. Prints a deny decision when it
matches; prints nothing otherwise (no output = allow).
"""
import json
import re
import shlex
import sys

# git's own "global" options; those in TAKES_VALUE swallow the next token, so
# the subcommand is not mistaken for their argument.
TAKES_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

# subcommand -> (flags that are destructive, human-readable reason)
DESTRUCTIVE_FLAGS = {
    "push":     ({"--force", "-f", "--force-with-lease", "--force-if-includes",
                  "--delete", "-d", "--mirror"}, "force or delete push"),
    "reset":    ({"--hard"}, "hard reset"),
    "clean":    ({"-f", "--force", "-ff"}, "forced clean"),
    "checkout": ({"--force", "-f"}, "forced checkout (discards local changes)"),
    "branch":   ({"-D"}, "forced branch delete"),
}

# A push refspec that deletes or force-updates a ref: "+main", ":stale-branch".
REFSPEC_DESTRUCTIVE = re.compile(r"^(\+|:)[A-Za-z0-9_./^~-]+|^[A-Za-z0-9_./^~-]*:$")

SEGMENT_SPLIT = re.compile(r"(?:\|\||&&|;|\||\n)")


def segments(command: str):
    """Split a shell command line into separately-executed segments."""
    return [s.strip() for s in SEGMENT_SPLIT.split(command) if s.strip()]


def tokens(segment: str):
    try:
        return shlex.split(segment)
    except ValueError:
        # Unbalanced quotes, $(...) oddities. Fall back to a naive split; the
        # caller still only inspects git subcommand arguments.
        return segment.split()


def inspect(segment: str):
    """Return a reason string if this segment is a destructive git command."""
    toks = tokens(segment)
    if "git" not in toks:
        return None

    i = toks.index("git") + 1
    # Skip git's global options to find the subcommand.
    while i < len(toks) and toks[i].startswith("-"):
        if toks[i] in TAKES_VALUE:
            i += 1
        i += 1
    if i >= len(toks):
        return None

    sub = toks[i]
    args = toks[i + 1:]
    if sub not in DESTRUCTIVE_FLAGS:
        return None

    flags, reason = DESTRUCTIVE_FLAGS[sub]

    for a in args:
        if a in flags:
            return reason
        # Bundled short flags: -fd, -fx, -dfx ...
        if re.fullmatch(r"-[a-zA-Z]{2,}", a):
            letters = set(a[1:])
            if sub == "clean" and "f" in letters:
                return reason
            if sub == "push" and ("f" in letters or "d" in letters):
                return reason

    if sub == "push":
        for a in args:
            if not a.startswith("-") and REFSPEC_DESTRUCTIVE.match(a):
                return "force or delete push (refspec)"

    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # malformed payload: not ours to judge
    command = (payload.get("tool_input") or {}).get("command") or ""

    for seg in segments(command):
        reason = inspect(seg)
        if reason:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"git-guard: {reason}. This can delete a teammate's commits or "
                        "uncommitted work, which git cannot recover. Explain the "
                        "consequence and have the user run it themselves."
                    ),
                }
            }))
            return


if __name__ == "__main__":
    main()
