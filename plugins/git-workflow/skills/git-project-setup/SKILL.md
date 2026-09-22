---
name: git-project-setup
description: Put a project under git and create its GitHub repository. Use when the user starts a new project, asks to "set up git", "put this under version control", "create a repo for this", "get this on GitHub", or when they want to work on a project with others and it is not yet a git repository. Handles the .gitignore decision, repo-local git config, the first commit, and creating plus pushing to the remote. For everyday work in a repo that already exists, use git-groupwork instead.
---

# Setting up git for a project

Runs once per project. Work through the steps in order; stop at the decision
points and ask.

## Step 0 — probe the environment before anything else

Auth differs between environments and neither can be assumed. Run this once:

```bash
command -v gh >/dev/null && gh auth status >/dev/null 2>&1 && echo "MODE=gh" || \
  { [ -n "$GITHUBTOKEN$GH_TOKEN$GITHUB_TOKEN" ] && echo "MODE=token" || echo "MODE=local"; }
```

- **`MODE=gh`** — use `gh` for remote operations.
- **`MODE=token`** — no `gh`. Use `curl` against the REST API, and a credential
  helper that reads the token from the environment at runtime. Also export
  `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_SYSTEM=/dev/null` for every git
  call — in some sandboxes `~/.gitconfig` is *denied* rather than absent, and
  git treats that as fatal.
- **`MODE=local`** — everything local works; creating a remote and pushing do
  not. Say so plainly, do the local half, and stop.

**Never echo the token, never put it in argv, never in a remote URL.** Use:

```bash
git config --local credential.helper \
  '!f() { echo "username=x-access-token"; echo "password=${GITHUBTOKEN:-${GH_TOKEN:-$GITHUB_TOKEN}}"; }; f'
```

The fallback chain matters: the probe above accepts any of the three names, so
the helper has to read all three. Reading only `$GITHUBTOKEN` fails silently — a
push that asks for a password in a non-interactive shell and hangs.

## Step 1 — is this a sensible place for a repo?

```bash
pwd
```

If the path contains `CloudStorage`, `Dropbox`, `OneDrive`, `iCloud Drive` or
`Google Drive`, **say so before going further.** A sync client and git both
write to `.git` and can corrupt it; a Quarto build in such a folder has been
observed producing 18 "conflicted copy" files and a clobbered `index.html`.
Recommend a non-synced location such as `~/projects/`, and note that GitHub is
now the sharing mechanism, so syncing the folder does the same job twice.

Then check whether it is already a repo (`git rev-parse --git-dir`). If it is,
this skill is the wrong one — use `git-groupwork`.

## Step 2 — the .gitignore decision (ask, but concretely)

Do **not** ask an abstract question. People say "yes, fine" to abstract
questions. Show the actual inventory first:

```bash
find . -type f -not -path "./.git/*" -size +1M -exec ls -lh {} \; 2>/dev/null | awk '{print $5, $9}'
find . -type f \( -name ".Renviron" -o -name ".env" -o -name "*secret*" -o -name "*token*" -o -name "*key*" -o -name "*.pem" \) -not -path "./.git/*" 2>/dev/null
```

Then present: *"These files are over 1 MB: … These look like credentials: …
I propose excluding them. Keep anything?"*

Write a `.gitignore` suited to the project's language. For R/RStudio always
include `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `.Renviron`,
rendered output (`*.html`, `_site/`, `.quarto/`), `.DS_Store`, and
**`Rplots.pdf`** — `Rscript` silently writes that whenever a script plots, so
it appears the first time you check that the project runs.

**"Never commit data" is wrong as a rule** and produces repositories nobody can
run. Apply the criterion instead, and put it in a comment in the `.gitignore`
so the next person sees the reasoning:

| Commit it | Exclude it |
|---|---|
| Small (under ~1 MB) | Large — git keeps every version forever |
| Simulated, or public | Personal, identifiable, or under a data agreement |
| Needed to run the code | Re-derivable from something already in the repo |

Say once, plainly: git never forgets. A secret that is committed and later
deleted is still in the history. So `.gitignore` must be right *before* the
first commit.

## Step 3 — init and configure, repo-locally

```bash
git init -b main
git config --local user.name  "<their real name>"
git config --local user.email "<the email their GitHub account uses>"
git config --local pull.rebase false
```

**Repo-local, not `--global`.** It behaves identically in both environments,
works where global config is denied, and does not mutate the user's machine.

Ask for the name and email if not already known — do not guess, and do not rely
on the macOS full-name fallback, which silently authors commits as whatever the
OS account is called.

`pull.rebase false` is not optional. Without it the first divergent `git pull`
fails with `fatal: Need to specify how to reconcile divergent branches.` — at
exactly the moment the user is least able to cope with it.

## Step 4 — first commit

Show what will be committed, then commit. Confirm the ignores actually held:

```bash
git status --short
git add -A
git status --ignored --short | grep '^!!'   # what .gitignore caught
```

If anything alarming appears staged (`A  data/patient_export.csv`), stop and
fix `.gitignore` before committing.

## Step 5 — create the remote (always ask first)

Creating a repository is outward-facing and a public one publishes content.
**Ask for the name and the visibility every time.** Default the name to the
folder name — folder name = repo name avoids a lot of later confusion.

`MODE=gh`:
```bash
gh repo create <name> --public|--private --source=. --remote=origin --push
```

`MODE=token`:
```bash
cat > "${TMPDIR:-/tmp}/repo.json" <<'JSON'
{"name":"<name>","private":true}
JSON

curl -sS -o "${TMPDIR:-/tmp}/repo.out" -w '%{http_code}\n' --config - <<EOF
url = "https://api.github.com/user/repos"
header = "Authorization: Bearer ${GITHUBTOKEN:-${GH_TOKEN:-$GITHUB_TOKEN}}"
header = "Accept: application/vnd.github+json"
data = "@${TMPDIR:-/tmp}/repo.json"
EOF
rm -f "${TMPDIR:-/tmp}/repo.json"

git remote add origin https://github.com/<owner>/<name>.git
git push -u origin main
```

Three things about that block are load-bearing:

- **The heredoc delimiter is unquoted (`<<EOF`, not `<<'EOF'`).** That is the
  whole mechanism. `curl --config` does no variable expansion of its own, so
  inside a quoted heredoc `Bearer $GITHUBTOKEN` is sent to GitHub as the literal
  eleven-character string `$GITHUBTOKEN` and you get a 401 that looks like a bad
  token. Unquoted, the shell substitutes the value on its way to curl's *stdin* —
  still never in argv, never in `ps`.
- **The JSON body goes through a file** (`data = "@..."`). An unquoted heredoc
  also eats the backslashes in `{\"name\":...}`, which corrupts the body.
- **Read the status code.** Expect `201`. `422` usually means the name is taken.

Then confirm the remote is real before trusting the push:

```bash
git ls-remote origin >/dev/null 2>&1 && echo reachable || echo "NOT reachable"
```

**Always an HTTPS remote.** SSH remotes fail outright in some environments
(no DNS for port 22, and `GIT_SSH_COMMAND=/bin/false` imposed). If a remote
already uses `git@github.com:`, rewrite it:

```bash
git remote set-url origin "$(git remote get-url origin | sed 's|git@github.com:|https://github.com/|')"
```

## Step 6 — verify, do not assume

List what the remote actually received and confirm the ignored files are absent.
Report it as state, not as commands:

> Pushed 9 files, 8.7 KB. `report.html` and `report_files/` were correctly left
> out. Live at github.com/…

## Step 7 — hand off

Tell them the two things they now need:

1. Everyday work is the `git-groupwork` skill — just say what you want.
2. To add teammates: **Settings → Collaborators** on GitHub. They must accept
   the invitation before they can push. Only do this when asked.

## Never

- Guess a name or email for commit identity.
- Create a repository, especially a public one, without asking.
- Commit before the `.gitignore` conversation has happened.
- Echo, log, or interpolate a token into a URL or argv.
