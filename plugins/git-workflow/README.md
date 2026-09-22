# git-workflow

Git and GitHub for group projects in R and RStudio, with Claude Code doing the
commands.

Companion to the course handout:
<https://ymaivali.github.io/git-for-groupwork/>

## Install

Two commands, typed in Claude Code:

```
/plugin marketplace add ymaivali/claude-plugins
```

```
/plugin install git-workflow@ulo-plugins
```

Then restart Claude Code, or start a new session — **skills are loaded at
session start, so they will not appear in the session you installed them in.**

## What you get

**Two skills.** You do not invoke them by name; say what you want and the right
one loads.

| Say something like | What happens |
|---|---|
| "set up git for this project" | New repository: the `.gitignore` conversation, your commit identity, first commit, a GitHub repo, first push |
| "commit this", "push it", "am I behind?", "open a PR", "I have a conflict" | The everyday loop |

**One guard.** See below — read this part before installing.

## The guard: what it does and what it sees

This plugin installs a `PreToolUse` hook. Being straightforward about it,
because it is your computer:

- It runs on **every Bash command Claude runs** in your sessions — not only git
  ones.
- It receives the **text of the command** and nothing else. No file contents, no
  environment variables, no credentials.
- It sends **nothing anywhere**. It is a local Python script — `wc -l` says 333
  lines, of which well over a third is comment — with no network access and no
  imports beyond the standard library. Read it: `hooks/git-guard.py`.
- Its only possible output is *"deny this command"* or *"ask the user about this
  command"*, each with a reason. It cannot modify a command or run anything.

### Why it exists

`git push --force` deletes your teammates' commits from GitHub. So do
`git push origin +main` and `git push origin :branch`. `git reset --hard` and
`git clean -f` delete uncommitted work, which is the one thing git cannot get
back. These are the failures that cost a group a week, and they are usually
typed by someone following a Stack Overflow answer that was not thinking about
their group.

Claude Code permission rules cannot reliably block them, because those rules
match by prefix only: a rule for `git push --force` does not match
`git push origin main --force`. Hence a hook, which parses the command instead.

### What it denies

Claude cannot run these at all:

`--force`, `--force-with-lease`, `--force-if-includes`, `-f`, `--delete`, `-d`
and `--mirror` on `git push`, including the `--force-with-lease=origin/main`
form and git's own abbreviations (`--forc`); a `+ref` or `:ref` push refspec;
`git reset --hard`; `git clean -f`; `git checkout --force`; `git stash clear`.

When it fires, you are told why. You can still run the command yourself in your
own terminal — it restrains Claude, not you.

### What it asks you about

These throw away *your own* uncommitted work, or a local branch. Sometimes that
is exactly what you want, so Claude is made to show you the command and wait:

`git checkout -- <paths>`, `git checkout .`, `git restore` (unless it is
`--staged` only, which just unstages), `git switch --force` /
`--discard-changes` / `-C`, `git stash drop`, and `git branch --delete --force`
in all its spellings (`-D`, `-Df`, `-d -f`, `--delete --force`).

`git branch -D` is an ask rather than a deny for a concrete reason. GitHub's
**Squash and merge** — which this plugin recommends — puts one new commit on
`main` that does not have your branch's commits as ancestors, so `git branch -d`
refuses the merged branch with *"not fully merged"*. Denying `-D` outright left
the everyday workflow with no legal way to finish, which is how a guard gets
switched off. The skill instead checks that the PR says `MERGED` first.

### What it does not touch

Everything else, including `git push`, `git push -u`, `git push --dry-run`,
`git pull`, `git branch -d` (the safe delete), `git reset --soft`,
`git restore --staged`, `git stash pop`, `git clean -n`, and
`git merge --abort`.

It also leaves ordinary shell alone. Two earlier versions did not. The first
blocked

```sh
echo "runs BEFORE pushing"; [ -f "$x" ] && git add -A
```

because the text contained "push" and a `-f`. The second still blocked

```sh
git commit -m "fix; git push -f later"
```

because it split the line on `;` before looking at quoting, so half a commit
message became a command. It now lexes the line with `shlex`, which keeps
quoted arguments in one piece, and inspects only the arguments of an actual git
subcommand.

### What it cannot see

Being equally straightforward about the limits, because a guard oversold is
worse than one understood:

- It is **not a security boundary.** It restrains an assistant trying to be
  helpful, not an adversary. `python -c "os.system(...)"`, a git alias, a
  base64'd command and a dozen other spellings walk straight past it. Closing
  those would cost false positives, and false positives are the failure that
  actually matters here.
- It does catch the spellings an assistant reaches for by habit: `bash -c '…'`,
  `(…)` subshells, `/usr/bin/git`, a single `&` between commands, `eval`,
  `--flag=value`, and git's own option abbreviations.
- `git checkout <file>` without the `--` separator is indistinguishable from
  `git checkout <branch>` without touching the disk, so it is not caught.
  `git checkout -- <file>` and `git checkout .` are.
- A heredoc or multi-line string that *contains* a destructive git command as
  text will be flagged. Lines are treated as separate commands.
- It sees only what the Bash tool runs. Anything you type in your own terminal
  is yours.

### Verify it yourself, do not take my word for it

```bash
python3 ~/.claude/plugins/*/plugins/git-workflow/hooks/git-guard-test.py
```

104 cases, expecting `deny`, `ask` or `allow` for each. The ones that matter
most are the false-positive cases at the bottom of the file — a guard that
blocks ordinary work gets switched off, and then it protects nothing.

If you would rather not have it, install the skills and delete
`hooks/hooks.json` from the installed plugin, or do not install the plugin and
copy the two `skills/` folders into `~/.claude/skills/` by hand. You then get
the advice without the rail.

## How the skills behave

Four deliberate choices, so nothing surprises you:

1. **Commits happen without asking. Pushes are checked first.** Before pushing,
   it looks for files over ~1 MB and files that look like credentials. Clean →
   it pushes. Not clean → it names the file and asks.
2. **It branches by default** when the repository has more than one
   collaborator, rather than reminding you and hoping.
3. **It reviews pull requests but never merges them.** A teammate presses merge
   — that five minutes of someone reading your diff is the cheapest quality
   control there is.
4. **It tells you the state of the repository, not the commands it ran.** You
   will see "you were 2 commits behind Anna", not `git pull`. The point is that
   you keep the mental model while delegating the typing.

## Merge conflicts

It will explain both sides and what each one says. It will not choose. A
conflict means two people wrote different things in the same place, and only
your group knows which version you mean to claim — often both, rewritten.

## Requirements

- git, and the GitHub CLI (`gh`) authenticated with `gh auth login`
- Python 3 for the guard (present on macOS and Linux by default)
- R and RStudio for the R-specific parts

Setup instructions for all three operating systems are in Part 0 of the
handout.
