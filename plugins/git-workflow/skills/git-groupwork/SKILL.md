---
name: git-groupwork
description: Everyday git and GitHub work in a repository that already exists — pulling teammates' changes, committing, pushing, starting branches, opening and reviewing pull requests, and working through merge conflicts. Use when the user says things like "save my work", "commit this", "push it", "what did my teammates change", "am I behind", "make a branch", "open a PR", "review this PR", "I have a merge conflict", or when they finish a piece of work in a git repository. For a project that is not yet a repository, use git-project-setup instead.
---

# Everyday git for group work

## Two standing rules that shape everything below

**Narrate state, stay silent on mechanics.** Never report `git add` or
`git commit` — nobody needs to know. Always report *state*, in human terms:

> You were 2 commits behind — pulled Anna's changes to `R/02-describe.R`.
> This is going on a branch, not `main`.
> Your push would have overwritten Anna's work, so I pulled first.

The user is delegating the typing, not the understanding. One sentence of state
per action keeps their model of the repository alive; a list of commands does
not.

**The user owns meaning; you own mechanics.** Anything reversible and
mechanical, just do. Anything about what the work *claims*, or about
publishing, is theirs.

## Step 0 — before any editing, orient

```bash
git rev-parse --abbrev-ref HEAD
git fetch --quiet && git status --short --branch
```

If behind, **pull before they start work** — this is the single habit that
prevents most conflicts. Then say what arrived and who wrote it:

```bash
git log --oneline HEAD@{1}..HEAD --format='%h %an: %s'
```

If `git pull` complains `Need to specify how to reconcile divergent branches`,
set `git config --local pull.rebase false` and pull again. It is a missing
setting, not a user error — fix it, mention it once, move on.

## Step 1 — branch by default when there are collaborators

```bash
gh api "repos/{owner}/{repo}/collaborators" --jq 'length' 2>/dev/null \
  || git log --format='%ae' -n 200 | sort -u | wc -l
```

The `gh` call needs push access — it returns 403 for a read-only collaborator —
and it is unavailable without `gh` at all. So it falls back to counting distinct
commit authors, which is local and always answers.

**Anything but a confident `1` means branch.** More than one collaborator, or no
usable answer, and the user is starting new work: branch first and say so. Do
not remind and hope. Branching costs nothing up front and is confusing to
retrofit after two days of commits on `main`.

A failed probe must never read as *solo*. An earlier version of this skill ended
the line with `|| echo 1`, which sent work straight to `main` at exactly the
moment the check was broken.

```bash
git switch -c feature/<what-it-does>
```

Name it after the work — `feature/age-adjusted-model`, never `fix`, `test2`, or
the user's name. Solo repository: stay on `main`, no ceremony.

## Step 2 — commit freely

Commit without asking, as often as there are coherent units of work. Small
commits are cheap and each one is a point the user can return to.

Write the message yourself. Subject under ~60 characters; then a blank line and
**why**, because the diff already shows *what*. The reasoning, the alternative
rejected, the thing that will not be obvious in six weeks.

Before committing to `main`, check the project still runs — a repo whose `main`
is broken blocks everyone. Use whatever the project offers (`quarto render`,
the test suite, sourcing the scripts). If it fails, say so and do not commit to
`main`.

## Step 3 — push, guarded

Pushing publishes. Run the check, then decide:

```bash
# what is about to go out
FILES=$(git diff --name-only @{upstream}..HEAD 2>/dev/null || git ls-files)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
# oversized
echo "$FILES" | while read -r f; do [ -f "$f" ] && \
  [ "$(wc -c <"$f")" -gt 1048576 ] && echo "LARGE: $f ($(du -h "$f" | cut -f1))"; done
# secret-shaped
echo "$FILES" | grep -Ei '(^|/)(\.env|\.Renviron)$|secret|token|credential|\.pem$|\.p12$|id_rsa' || true
```

Pushing to `main` turns on whether the repository is public, so find out rather
than assume:

```bash
gh repo view --json isPrivate --jq '.isPrivate' 2>/dev/null || echo unknown
```

`unknown` counts as public — ask.

**Push without asking** when all of these hold:
- nothing flagged above, and
- the branch is not `main`/`master`, **or** the repository is private.

**Ask first** when any of these hold:
- a file is over ~1 MB, or looks like a credential, or is an unexpected type
- the target is `main`/`master` **and** the repository is public
- the push is to a branch someone else also commits to

When asking, name the specific file and why — *"`data/cohort.csv` is 14 MB and
would be published to a public repo; push anyway?"* — not a generic prompt.

**`git push --force` is never autonomous, on any branch, for any reason.** It
deletes teammates' commits from the remote. If the user asks for it, explain
what it destroys and have them run it themselves.

This one is enforced, not merely instructed: a `PreToolUse` hook
(`git-guard.py`) lexes the command and inspects the arguments of the git
subcommand, so `git push origin main --force` is caught as surely as
`git push --force`, and so is `--force-with-lease=origin/main`.

The guard has two verdicts:

- **Deny** — you cannot run it at all: force and delete pushes, `--mirror`, a
  `+refspec` or `:refspec`, `reset --hard`, `clean -f`, `stash clear`.
- **Ask** — the user is shown the command and answers: `checkout -- <paths>`,
  `checkout .`, `restore`, `switch --force`, `stash drop`,
  `branch --delete --force`. These discard the user's *own* uncommitted work or
  a local branch, which is occasionally exactly what is wanted. Before they
  answer, name the files or commits that would be lost.

Relay the reason either way. **Do not look for a spelling that gets around a
deny.** There are spellings that work — the guard is a rail, not a wall — and
using one defeats the thing the user chose to install.

A rejected push (`! [rejected] … (fetch first)`) means a teammate pushed and
this push would overwrite them. Pull, resolve, push. Say that in those words.

## Step 4 — pull requests

Open one when the user asks, or offer once when a branch's work looks finished.
A PR body worth reviewing answers three questions — the third is the one people
skip and reviewers need most:

- **What** changed
- **Why** — the reasoning, not a restatement of the diff
- **How to check this** — the concrete command or observation a reviewer can run

```bash
git push -u origin <branch>
gh pr create --base main --title "…" --body "…"
```

No `gh`? Same thing over the API: `POST /repos/{owner}/{repo}/pulls` with
`{"title":…,"head":"<branch>","base":"main","body":…}`.

**Mergeability is asynchronous.** `mergeable` is legitimately `null` /
`UNKNOWN` for several seconds after a push, and for merged or closed PRs. Poll
a few times before reporting anything:

```bash
for i in 1 2 3 4; do
  gh pr view "$N" --json mergeable,mergeStateStatus --jq '"\(.mergeable)/\(.mergeStateStatus)"'
  sleep 5
done
```

## Step 5 — review, but do not merge

**Reviewing is yours. Pressing merge is a human's.** When asked to review a PR,
do it properly:

- does `main` still work with this merged — ideally checked from a clean clone
- does the change match what the description claims
- did any data file, credential, or rendered output creep in
- is anything obviously wrong in the code itself

Report findings. Then stop, and say who should merge.

In a repository with collaborators, **the author does not merge their own PR** —
a different person does. That five minutes of a teammate reading the diff is
the cheapest quality control available, and an AI merging on the author's
request turns the review into theatre. Solo repository: this relaxes, and the
user can merge their own.

Recommend **Squash and merge** over GitHub's default "Create a merge commit":
one commit on `main` per contribution, readable history, and reverting a bad
contribution becomes a single step. It has one consequence for the cleanup in
Step 6 — read that before deleting the branch.

## Step 6 — the step everyone forgets

**Merging on GitHub does not change anything locally.** After a merge, for
everyone in the group:

```bash
gh pr view <N> --json state --jq '.state'        # expect MERGED
git switch main && git pull && git fetch --prune
git branch -d <the-merged-branch>
```

**Check the PR state first, then delete.** The order matters, because of this:

> `error: The branch 'feature/x' is not fully merged.`

After a **squash** merge that message is expected and does not mean the work is
unsaved. Squashing writes one new commit on `main` that does not have the
branch's commits as ancestors, so git honestly cannot see a merge, and `-d`
refuses. The PR saying `MERGED` is the evidence git lacks; with it,
`git branch -D <branch>` is the correct command, and the guard will ask before
it runs — that `MERGED` is the answer to give.

Without a `MERGED` from the PR, the message means exactly what it says. Do not
reach for `-D` to make it go away.

Skip this whole step and the user will, a week later, commit new work onto a
branch that was merged and deleted, and be thoroughly confused. Do it unprompted
whenever a PR is seen to have merged.

## Step 7 — merge conflicts: advise, never decide

A conflict is not an error. It means two people changed the same lines and git
refuses to guess. `git merge --abort` puts everything back untouched — offer it
early if the user is rattled.

**Read the two sides and tell the user what each one says**, then ask which the
group means to claim. Often the honest answer is *both*, rewritten — each side
usually says something the other omitted.

**The sides are not always equal, and this matters:**

| Situation | `HEAD` is | Other side is | Default posture |
|---|---|---|---|
| Pulled into a shared branch | your draft | their draft | combine both; ask |
| Merged `main` into your branch | your unreviewed work | **work the group already accepted** | keep `main`'s version, add yours |

In the second case, overwriting the other side silently reverses a decision the
group already made — inside a merge commit, where no reviewer will ever see it.
If the user thinks `main` is wrong, that is a conversation in the PR, not a
quiet edit during a merge.

Direction matters too: to fix a conflicting PR, merge `main` **into the
branch** (`git merge origin/main`), never the branch into `main` — the latter
bypasses the pull request and the reviewer entirely.

Before committing any resolution, two checks:

```bash
grep -rnE '^(<<<<<<<|=======|>>>>>>>)' <file> || echo "clean"
# then actually run/render the project — a half-resolved file is valid text and invalid code
```

The second check is how `<<<<<<< HEAD` fails to reach a submitted report.

## Symptom → action

| What they see | What it means | Do |
|---|---|---|
| `! [rejected] … (fetch first)` | teammate pushed; you'd overwrite them | pull, resolve, push. Never `--force` |
| `Need to specify how to reconcile` | missing `pull.rebase` setting | `git config --local pull.rebase false` |
| `CONFLICT (content)` | same lines both sides | Step 7 |
| `Please tell me who you are` | no commit identity | set `user.name`/`user.email` repo-locally; ask, don't guess |
| PR says `CONFLICTING`/`DIRTY` | `main` moved while the PR was open | `git merge origin/main` *in the branch* |
| `branch 'x' is not fully merged` | usually a squash merge; git sees no ancestry | confirm the PR is `MERGED`, then `-D`. Step 6 |
| push hangs, or file >100 MB refused | something huge got committed | if unpushed, undo the commit and gitignore it. If pushed: tell them, and treat any secret as burned |

## Never

- `git push --force` autonomously.
- Merge a PR the user authored, in a repo with collaborators.
- Resolve a conflict by picking a side without telling the user what each side said.
- Push a file over ~1 MB, or a credential-shaped file, without asking.
- Discard uncommitted work — `checkout -- .`, `restore`, `switch -f`,
  `stash drop` — without first naming exactly which files would be lost.
- Delete a branch with `-D` on the strength of the error message alone. The PR
  must say `MERGED`.
- Route around the guard once it has denied something: no `bash -c`, no
  `/usr/bin/git`, no subshell, no alias. Relay the reason instead.
- Echo a token, or put one in argv or a remote URL.
