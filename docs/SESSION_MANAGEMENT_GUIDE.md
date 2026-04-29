# Managing Long-Running Projects with Claude Sessions

*Lessons learned from an AFL betting model project across 12+ sessions spanning weeks of iterative development. This guide is for any multi-session project where Claude (Cowork or CLI) needs to pick up where it left off without burning tokens re-reading everything.*

## The Problem

Every new Claude session starts cold. It has no memory of prior sessions. To do useful work, it needs to rebuild context — and the naive approach (dump everything into files, let Claude read it all) gets expensive fast.

In our case, after ~10 sessions we had a single session log at 295 lines, a CLAUDE.md at 130 lines, a handoff prompt at 30 lines, and 17 markdown files in the root directory. Every new session burned 450+ lines of context before doing any actual work. The session log kept growing, old decisions stayed inline with current ones, and Claude would often read the full codebase "just to be safe."

## The Solution: Three-File Startup

A new session should read at most three short files to be fully productive:

**1. `CLAUDE.md` (~60 lines)** — Project-level constants. What the project is, constraints that must never be violated, key file locations, folder structure, dependencies. This changes rarely. Think of it as the README for Claude, not for humans.

**2. `SESSION_LOG_COWORK.md` (~15-25 lines)** — What happened in the LAST session only. Key outcomes, active decisions, and what's pending. This file gets replaced entirely each session — the outgoing session writes its log here, and the incoming session reads it then overwrites with its own.

**3. `COWORK_HANDOFF_PROMPT.md` (~15 lines)** — The action list. What to do next, in priority order, with exact filenames. No background, no justification — just the task list.

**Total startup: ~100 lines.** Everything else is accessed on demand.

## The Index

**`INDEX.md`** — A flat list of every file in the project with a one-line description, organised by folder. When Claude needs to find something, it reads this instead of scanning the filesystem or grepping across the codebase.

Update it whenever files are added, moved, or deleted. It's a small maintenance cost that prevents expensive exploratory reads.

## Session Log Lifecycle

This is the part that took us the longest to get right. The key insight: **session logs are for the next session, not for posterity.**

**What we tried first:** One continuous `SESSION_LOG.md` that grew with every session. By session 10 it was 295 lines and contained decisions from weeks ago that were no longer relevant. Every new session read the whole thing.

**What works:** Each session gets its own log. The current one lives at a fixed path (`SESSION_LOG_COWORK.md`). When a new session starts, it:
1. Reads the current log (to learn what happened last time)
2. Does its work
3. Archives the old log to `archive/session_logs/SESSION_N.md`
4. Writes its own log to `SESSION_LOG_COWORK.md`

The archived logs are never read unless someone explicitly needs to look up an old decision.

**What goes in a session log:**
- Key outcomes (what changed, what was built)
- Decisions made (and the reasoning, briefly)
- What's pending for next session
- References to any files created or modified

**What does NOT go in a session log:**
- Full analysis results (put these in their own files)
- Background context (that's what CLAUDE.md is for)
- Step-by-step narration of what Claude did
- Duplicated information from other files

## Folder Structure

Keep the root directory clean. Root should contain only:
- Context files (CLAUDE.md, handoff, session log, index)
- Core code files
- Standard project files (README, requirements.txt, .gitignore)

Everything else goes in purpose-built folders:

```
prompts/              Active CLI/task prompts
prompts/completed/    Finished prompts (reference only)
docs/                 Specs, backlog, findings
analysis/             Analysis scripts and results
archive/              Old session logs, old prompts, old findings
archive/session_logs/ One file per session
pipeline/             Data fetching and automation
Data/                 Raw data files
```

The key principle: **a new session should never need to scan the root directory to figure out what's going on.** CLAUDE.md and the handoff tell it everything.

## CLAUDE.md Design

This file is the project's constitution. It should be short, stable, and authoritative.

**Include:**
- What the project is (2-3 sentences max)
- Hard constraints that must never be violated
- The current model/system summary (a small table works well)
- Key file locations (not every file — just the important ones)
- Folder structure (one line per folder)
- How to find things (pointer to INDEX.md)
- How to find session context (pointer to handoff + session log)
- Dependencies and setup

**Exclude:**
- Session history (that's what session logs are for)
- Detailed explanations of decisions (link to docs/ instead)
- Anything that changes frequently
- Prose explanations of things that can be a table

**Target: under 70 lines.** If it's longer, something belongs in a different file.

## Handoff Prompt Design

The handoff prompt exists for one purpose: tell the next session what to do. It should be the shortest file in the project.

**Template:**
```markdown
# Handoff

Read `CLAUDE.md` then `SESSION_LOG_COWORK.md`. If you need to find a file, check `INDEX.md`.

## Next actions
1. [Task with exact filename or command]
2. [Task with exact filename or command]
3. ...

## CLI launch (if applicable)
[Exact commands to start a CLI session]
```

No background. No "you are resuming a project." No context that's already in CLAUDE.md. Just the list.

## Common Mistakes

**Growing session logs.** The biggest token sink. One bad session log that never gets trimmed can cost you hundreds of lines of context every single session for the rest of the project.

**Duplicating context.** If the same information appears in CLAUDE.md, the session log, and the handoff prompt, you're paying for it three times. Each file has one job.

**Detailed discarded-ideas sections.** You need to record what was tried and failed (to prevent re-testing), but you don't need three paragraphs on why. One line per discarded idea is enough: "Travel/fatigue — tested, no signal, bookmakers already price it."

**CLI prompts in the root directory.** They accumulate fast. After 10 research tasks we had 13 prompt files in root. Move them to `prompts/` and separate active from completed.

**No index.** Without an index, Claude's only option for finding files is globbing and grepping — which means reading directory listings, opening files speculatively, and burning tokens on wrong guesses. A 60-line index prevents all of that.

**Skipping the archive step.** Old session logs and completed prompts feel harmless sitting in the project. But Claude reads file listings, sees them, and sometimes reads them "just in case." Move completed work to `archive/` so it's out of the default scan path.

## Applying to a New Project

1. Create `CLAUDE.md` at project start. Keep it under 70 lines.
2. Create `INDEX.md` and update it as you go.
3. Create `COWORK_HANDOFF_PROMPT.md` with your first action list.
4. After each session, write `SESSION_LOG_COWORK.md` (replacing the previous one, archiving the old).
5. Set up `prompts/`, `docs/`, `archive/`, and any project-specific folders from the start.
6. Periodically audit: is CLAUDE.md still under 70 lines? Is the session log just one session? Are completed prompts archived?

The upfront investment is about 15 minutes. The ongoing cost is ~2 minutes per session to archive and update. The saving is substantial — in our case, roughly 75% reduction in startup token cost.
