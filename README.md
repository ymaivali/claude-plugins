# ulo-plugins

A Claude Code plugin marketplace. Ülo Maiväli, University of Tartu —
Institute of Public Health and Family Medicine, Institute of Technology.

## Add it

```
/plugin marketplace add ymaivali/claude-plugins
```

## Plugins

### git-workflow

Git and GitHub for group projects in R and RStudio, with Claude Code doing the
commands. Two skills — setting a project up, and the everyday loop of pull,
commit, guarded push, branch, pull request and conflict resolution — plus an
enforced guard against force-pushes and other commands that destroy work git
cannot recover.

```
/plugin install git-workflow@ulo-plugins
```

**Read [its README](plugins/git-workflow/README.md) before installing.** It
adds a hook that inspects every Bash command Claude runs on your machine; that
README says exactly what the hook sees and what it does with it.

Companion handout: <https://ymaivali.github.io/git-for-groupwork/>

### tte-builder

Specifying a target trial and its emulation for pharmacoepidemiology and
comparative-effectiveness studies: a time-zero gate, PubMed-verified
references, explicit uncertainty tagging.

```
/plugin install tte-builder@ulo-plugins
```

## Note for students

Skills load when a session starts, so after installing, **start a new session**
— they will not appear in the one you installed them in.
