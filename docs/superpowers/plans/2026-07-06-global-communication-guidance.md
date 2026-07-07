# Global Communication Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create persistent global Codex CLI guidance that applies the approved communication rules in every repository without relying on session data.

**Architecture:** Use the Codex-supported global entry point at `~/.codex/AGENTS.md`. Keep all current communication rules in that one file; reserve `~/.codex/guidance/` for future chapter files and document how any future split must be routed from the entry point.

**Tech Stack:** Markdown, Codex `AGENTS.md` instruction discovery, POSIX shell verification

---

## File Structure

- Create: `/home/blaine/.codex/AGENTS.md` — global personal communication guidance loaded by Codex.
- Verify: `/home/blaine/wizytki_jaslo_page/docs/superpowers/specs/2026-07-06-global-communication-guidance-design.md` — approved source specification; no modification required.

The global file does not belong to this repository, so it cannot be committed with the project. The design and implementation-plan documents are the repository-tracked audit trail.

### Task 1: Create the global guidance

**Files:**
- Create: `/home/blaine/.codex/AGENTS.md`

- [ ] **Step 1: Confirm that no global file has appeared since planning**

Run:

```bash
test ! -e /home/blaine/.codex/AGENTS.md
```

Expected: exit status `0` and no output. If the file now exists, stop and compare it with the content below; merge deliberately instead of overwriting it.

- [ ] **Step 2: Request permission to write outside the workspace**

Request approval for creating `/home/blaine/.codex/AGENTS.md`. Explain that this is the supported global Codex guidance location and will affect future Codex sessions across all repositories.

Expected: the user explicitly approves the filesystem write.

- [ ] **Step 3: Create the guidance file with the approved content**

Create `/home/blaine/.codex/AGENTS.md` with exactly:

```markdown
# Global Working Agreement

## Communication

- Use English by default.
- Give balanced responses: lead with the conclusion and include enough reasoning for the user to evaluate it.
- Keep decision points open while the user asks questions. Questions and requests for explanation do not constitute approval, rejection, selection, or cancellation.
- Treat a decision as final only when the user uses explicit wording such as “approved” or “I choose X.”
- For low-risk ambiguity, state the assumption and proceed. The user may correct the assumption at any time.
- For ambiguity that could materially change the result or cause costly, destructive, or difficult-to-reverse work, pause and ask one focused question.
- During longer tool-based work, provide brief progress updates before work starts, at meaningful milestones, and at least once every 60 seconds while work remains active.
- If a process appears stalled or looped, report it immediately. State what is waiting or blocked and what action will be tried next. Do not send repetitive updates without new information.
- Challenge questionable user decisions inline and concisely when supported by evidence or a reasonable technical suspicion.
- Label evidence-backed concerns separately from suspicions. Provide a recommended alternative and its trade-offs. Leave the final decision to the user unless safety, policy, or permissions prevent the requested action.
- Expand challenges, explanations, or alternatives when the user requests more detail.

## Guidance Maintenance

- Keep this file concise and reserve it for stable personal defaults that should apply across repositories.
- Keep project-specific instructions in repository-level `AGENTS.md` files.
- If this file becomes difficult to navigate, retain it as the global entry point and move detailed topics into `~/.codex/guidance/`. Add explicit instructions here describing when each chapter must be read; files in that directory are not loaded automatically.
```

Expected: the file is created without changing any repository-level instructions.

### Task 2: Verify file content and scope

**Files:**
- Test: `/home/blaine/.codex/AGENTS.md`

- [ ] **Step 1: Verify the file exists and is non-empty**

Run:

```bash
test -s /home/blaine/.codex/AGENTS.md
```

Expected: exit status `0` and no output.

- [ ] **Step 2: Scan for incomplete language**

Run:

```bash
rg -n 'TBD|TODO|FIXME|placeholder|implement later' /home/blaine/.codex/AGENTS.md
```

Expected: exit status `1` and no output, meaning no incomplete markers were found.

- [ ] **Step 3: Verify every approved behavioral requirement is represented**

Run:

```bash
rg -n 'English by default|balanced responses|decision as final|low-risk ambiguity|materially change the result|60 seconds|stalled or looped|evidence-backed|technical suspicion|Guidance Maintenance' /home/blaine/.codex/AGENTS.md
```

Expected: matches for all ten patterns. Inspect the output and confirm that each pattern appears in the intended rule.

- [ ] **Step 4: Confirm no session-data dependency was introduced**

Run:

```bash
rg -ni 'session[-_ ]?data|memory database|conversation state' /home/blaine/.codex/AGENTS.md
```

Expected: exit status `1` and no output.

### Task 3: Verify discovery in a fresh Codex session

**Files:**
- Test: `/home/blaine/.codex/AGENTS.md`

- [ ] **Step 1: End the current Codex session and start a fresh CLI session**

Start the session from a repository that has no repository-level `AGENTS.md` so the global guidance can be evaluated independently.

Expected: the new session starts normally.

- [ ] **Step 2: Check default language and response depth**

Prompt:

```text
Briefly explain what instructions govern your communication style in this session.
```

Expected: an English response with a concise conclusion and enough reasoning to evaluate it.

- [ ] **Step 3: Check low-risk assumption behavior**

Give a harmless request with a minor ambiguity that does not materially affect the outcome.

Expected: Codex prints its reasonable assumption and proceeds without blocking for confirmation.

- [ ] **Step 4: Check the open-decision behavior**

Ask Codex to present two alternatives, then ask a question about one alternative without selecting it.

Expected: Codex answers the question and keeps both alternatives open until the user explicitly says “approved” or “I choose X.”

- [ ] **Step 5: Check challenge behavior**

Propose a technically questionable but safe approach and ask Codex to evaluate it.

Expected: Codex labels evidence separately from suspicion, proposes an alternative with trade-offs, and leaves the decision to the user.

- [ ] **Step 6: Record verification outcome**

If all checks pass, report that global guidance discovery and representative behaviors were verified in a fresh session. If any check fails, record the exact observed behavior and revise only the rule responsible for that failure.

Expected: a concise pass report or a concrete failure report with the specific rule requiring adjustment.
