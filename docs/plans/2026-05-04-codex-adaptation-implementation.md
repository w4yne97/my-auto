# Codex Adaptation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Codex-native project guidance and module-level skills for the existing `my-auto` workflows.

**Architecture:** Keep Python modules and Claude skills unchanged. Add `AGENTS.md` for project-level Codex context, add three repo-local Codex skills under `codex/skills`, and provide an installer that symlinks those skills into `~/.agents/skills`.

**Tech Stack:** Markdown, Codex Agent Skills, Bash, existing Python CLI entrypoints.

---

### Task 1: Add Project-Level Codex Instructions

**Files:**
- Create: `AGENTS.md`

**Steps:**

1. Add repository overview and module boundaries.
2. Document storage trichotomy: config, runtime state, vault.
3. Document common setup, tests, and smoke commands.
4. Add safety rules for vault writes and unrelated worktree changes.

**Verify:**

Run: `test -f AGENTS.md && grep -Fq "Codex" AGENTS.md`

### Task 2: Add Module-Level Codex Skills

**Files:**
- Create: `codex/skills/auto-reading/SKILL.md`
- Create: `codex/skills/auto-learning/SKILL.md`
- Create: `codex/skills/auto-x/SKILL.md`
- Create: `codex/skills/*/agents/openai.yaml`

**Steps:**

1. Write concise frontmatter descriptions with clear trigger conditions.
2. Include command routing tables for legacy slash commands.
3. Link to original `.claude/skills/<name>/SKILL.md` for detailed behavior.
4. Include module-specific state/config/vault paths and common Python commands.

**Verify:**

Run:

```bash
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py codex/skills/auto-reading
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py codex/skills/auto-learning
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py codex/skills/auto-x
```

Expected: each command prints `Skill is valid!`.

### Task 3: Add Skill Installer

**Files:**
- Create: `codex/install-skills.sh`

**Steps:**

1. Add a Bash script that symlinks each repo-local skill into `~/.agents/skills`.
2. Make it idempotent and safe for existing matching symlinks.
3. Tell the user to restart Codex after installation.

**Verify:**

Run: `bash -n codex/install-skills.sh`

### Task 4: Document Codex Usage

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`

**Steps:**

1. Add a Codex section explaining `AGENTS.md`.
2. Add install command for repo-local skills.
3. State that Claude skills remain supported.

**Verify:**

Run:

```bash
grep -Fq "Codex" README.md
grep -Fq "Codex" README.zh-CN.md
```

### Task 5: Final Verification

**Files:**
- All changed files

**Steps:**

1. Run skill validators.
2. Run shell syntax check.
3. Run `git diff --check`.
4. Review `git status --short` and ensure `.DS_Store` files are not staged.
