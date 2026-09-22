#!/usr/bin/env python3
"""PreToolUse hook (matcher: Bash) — hold back git commands that destroy work.

Two decisions, not one:

  deny  destroys work that is not the user's to destroy, or destroys it in
        bulk: force and delete pushes, --mirror, reset --hard, clean -f,
        stash clear. Claude cannot run these at all. The user still can, in
        their own terminal.

  ask   discards the user's own uncommitted work, or a local branch, in a
        way that is sometimes exactly what was wanted: checkout of paths,
        restore, switch --force, stash drop, branch --delete --force. The
        command is shown and the user answers.

`git branch -D` is in the second group on purpose. GitHub's "Squash and
merge" — which the skill recommends — produces a new commit on main that does
not have the branch's commits as ancestors, so `git branch -d` refuses the
merged branch with "not fully merged". Denying -D outright left the everyday
workflow with no legal way to finish.

Why a hook and not a permission rule: rules match by exact string or
trailing-* prefix only, so "Bash(git push --force*)" does NOT match
"git push origin main --force".

Why a lexer and not grep or a regex split: both produce false positives on
ordinary shell, and a guard that blocks ordinary work gets switched off,
after which it protects nothing. shlex in non-POSIX mode keeps quoting
intact, so

    git commit -m "fix; git push -f later"

is one command with one quoted argument, not two commands.

What this is NOT: a security boundary. It restrains an assistant that is
trying to be helpful, not an adversary. `python -c 'os.system(...)'`, a git
alias, base64, and a dozen other spellings walk straight past it. Closing
those would cost false positives, and false positives are the failure that
actually matters here. See README, "What it cannot see".

Reads the PreToolUse payload on stdin. Prints a decision when a rule fires;
prints nothing otherwise (no output = allow).
"""
import json
import os
import re
import shlex
import sys

DENY = "deny"
ASK = "ask"

MAX_DEPTH = 3

# git's own "global" options; those in TAKES_VALUE swallow the next token, so
# the subcommand is not mistaken for their argument.
TAKES_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

# Programs whose argument is itself a command line, and so must be re-read.
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "mksh", "ash"}

# Shell operators, as the lexer emits them. Quoted text keeps its quotes in
# non-POSIX mode, so a ";" inside a commit message is never one of these.
OPERATOR_CHARS = set(";|&()<>")

# A push refspec that deletes or force-updates a ref: "+main", ":stale-branch".
REFSPEC_DESTRUCTIVE = re.compile(r"^(\+|:)[A-Za-z0-9_./^~-]+|^[A-Za-z0-9_./^~-]*:$")

# Bundled short flags: -fd, -xdf, -Df ...
BUNDLED = re.compile(r"-[a-zA-Z]{2,}$")


# --- lexing -----------------------------------------------------------------

def lex(line):
    """Tokenise one line, keeping quotes attached and operators separate."""
    try:
        lx = shlex.shlex(line, posix=False, punctuation_chars=True)
        lx.whitespace_split = True
        lx.commenters = ""
        # punctuation_chars already adds ~-./*?= to wordchars. These keep a
        # refspec (+main, :stale, main:main) and a gh placeholder in one piece.
        lx.wordchars += "+:@^%!,{}$"
        return list(lx)
    except ValueError:
        # Unbalanced quotes. Fall back to a naive split; the caller still only
        # inspects the arguments of a git subcommand.
        return line.split()


def unquote(tok):
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
        return tok[1:-1]
    return tok


def is_operator(tok):
    return bool(tok) and set(tok) <= OPERATOR_CHARS


def segments(toks):
    """Split a token list at shell operators into separately-run commands."""
    out, seg = [], []
    for t in toks:
        if is_operator(t):
            if seg:
                out.append(seg)
                seg = []
        else:
            seg.append(t)
    if seg:
        out.append(seg)
    return out


# --- flag matching ----------------------------------------------------------

def base(arg):
    """--force-with-lease=origin/main -> --force-with-lease"""
    return arg.split("=", 1)[0]


def hit(arg, flags):
    """Does `arg` name one of `flags`?

    Handles --flag=value, and the unambiguous long-option abbreviations git
    itself accepts, so --forc counts as --force.
    """
    a = base(arg)
    if a in flags:
        return True
    if a.startswith("--") and len(a) > 2:
        return any(f.startswith(a) for f in flags if f.startswith("--"))
    return False


def bundle(arg):
    """Letters of a bundled short flag, or an empty set."""
    a = base(arg)
    return set(a[1:]) if BUNDLED.fullmatch(a) else set()


def short(arg, letter):
    a = base(arg)
    return a == "-" + letter or letter in bundle(arg)


# --- per-subcommand rules ---------------------------------------------------

PUSH_FLAGS = {"--force", "-f", "--force-with-lease", "--force-if-includes",
              "--delete", "-d", "--mirror"}


def rule_push(args):
    for a in args:
        if hit(a, PUSH_FLAGS) or bundle(a) & {"f", "d"}:
            return DENY, "force or delete push"
    for a in args:
        if not a.startswith("-") and REFSPEC_DESTRUCTIVE.match(a):
            return DENY, "force or delete push (refspec)"
    return None


def rule_reset(args):
    for a in args:
        if hit(a, {"--hard"}):
            return DENY, "hard reset (throws away uncommitted work)"
    return None


def rule_clean(args):
    for a in args:
        if hit(a, {"--force"}) or short(a, "f"):
            return DENY, "forced clean (deletes untracked files outright)"
    return None


def rule_checkout(args):
    for a in args:
        if hit(a, {"--force"}) or short(a, "f"):
            return DENY, "forced checkout (discards uncommitted changes)"
    if "--" in args or "." in args or "*" in args:
        return ASK, "checkout of paths (discards uncommitted changes to them)"
    return None


def rule_restore(args):
    staged = any(hit(a, {"--staged"}) or base(a) == "-S" for a in args)
    worktree = any(hit(a, {"--worktree"}) or base(a) == "-W" for a in args)
    if staged and not worktree:
        return None  # unstages only; the working tree is untouched
    return ASK, "restore (discards uncommitted changes)"


def rule_switch(args):
    for a in args:
        if hit(a, {"--force", "--discard-changes"}) or short(a, "f"):
            return ASK, "switch --force (discards uncommitted changes)"
        if base(a) == "-C" or "C" in bundle(a):
            return ASK, "switch --force-create (overwrites an existing branch)"
    return None


def rule_branch(args):
    delete = force = False
    for a in args:
        if base(a) == "-D" or "D" in bundle(a):
            delete = force = True
        if base(a) == "-d" or "d" in bundle(a) or hit(a, {"--delete"}):
            delete = True
        if base(a) == "-f" or "f" in bundle(a) or hit(a, {"--force"}):
            force = True
    if delete and force:
        return ASK, ("forced branch delete — git cannot see the branch's commits "
                     "on main, which is normal after a squash merge and alarming "
                     "otherwise")
    return None


def rule_stash(args):
    verb = next((a for a in args if not a.startswith("-")), None)
    if verb == "clear":
        return DENY, "stash clear (drops every stash; git cannot recover them)"
    if verb == "drop":
        return ASK, "stash drop (discards that stashed work)"
    return None


RULES = {
    "push": rule_push,
    "reset": rule_reset,
    "clean": rule_clean,
    "checkout": rule_checkout,
    "restore": rule_restore,
    "switch": rule_switch,
    "branch": rule_branch,
    "stash": rule_stash,
}


# --- walking the command ----------------------------------------------------

def inspect_git(toks, start):
    """Inspect one `git ...` occurrence starting at index `start`."""
    i = start + 1
    while i < len(toks) and unquote(toks[i]).startswith("-"):
        if unquote(toks[i]) in TAKES_VALUE:
            i += 1
        i += 1
    if i >= len(toks):
        return None

    sub = unquote(toks[i])
    rule = RULES.get(sub)
    if rule is None:
        return None
    return rule([unquote(a) for a in toks[i + 1:]])


def inspect_nested(toks, k, depth):
    """`bash -c '<command>'` — the quoted argument is itself a command line."""
    saw_c = False
    for t in toks[k + 1:]:
        w = unquote(t)
        if w.startswith("-"):
            if "c" in w.lstrip("-"):
                saw_c = True
            continue
        return inspect_command(w, depth + 1) if saw_c else None
    return None


def inspect_segment(toks, depth):
    for k, tok in enumerate(toks):
        name = os.path.basename(unquote(tok))
        if name == "git":
            found = inspect_git(toks, k)
        elif depth < MAX_DEPTH and name in SHELLS:
            found = inspect_nested(toks, k, depth)
        elif depth < MAX_DEPTH and name == "eval":
            found = next((f for f in (inspect_command(unquote(t), depth + 1)
                                      for t in toks[k + 1:]) if f), None)
        else:
            continue
        if found:
            return found
    return None


def inspect_command(command, depth=0):
    # Lines are lexed separately: without this, `git push origin main` on one
    # line and `grep -f pat.txt` on the next would read as one command.
    for line in command.splitlines() or [command]:
        for seg in segments(lex(line)):
            found = inspect_segment(seg, depth)
            if found:
                return found
    return None


# --- hook protocol ----------------------------------------------------------

ADVICE = {
    DENY: ("This can delete a teammate's commits or uncommitted work, which git "
           "cannot recover. Explain the consequence and have the user run it "
           "themselves. Do not look for a spelling that gets past this."),
    ASK: ("This discards work that is not committed anywhere else. Before the "
          "user answers, name exactly which files or commits would be lost."),
}


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # malformed payload: not ours to judge
    command = (payload.get("tool_input") or {}).get("command") or ""

    found = inspect_command(command)
    if not found:
        return
    decision, reason = found
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"git-guard: {reason}. {ADVICE[decision]}",
        }
    }))


if __name__ == "__main__":
    main()
