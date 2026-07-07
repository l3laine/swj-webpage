# Mark 1 Checkpoint Design

## Purpose

Preserve the approved dedicated-Codex-user operating instructions as a local, readable checkpoint rather than session data.

## Artifact

Create `docs/marks/mark-1.md` in the current workspace.

The document begins with “Log out and back in so your new group membership takes effect. Then run Codex as the dedicated user:” and includes all subsequent guidance developed in the discussion:

- running Codex as the dedicated `codex` user;
- least-privilege group rules;
- verification of account privileges;
- access to `/srv/codex-workspaces`;
- access to the selected project `/home/blaine/wizytki_jaslo_page`;
- ACL installation and configuration;
- access-verification commands;
- the warning about `.git` contents and secrets;
- the consequence that global guidance for this account belongs at `/home/codex/.codex/AGENTS.md`.

## Format

Use concise Markdown with executable Bash blocks. Preserve command ordering and distinguish commands that require administrative privileges from explanatory notes.

## Verification

Confirm the file exists, starts with the requested sentence, contains no placeholders, and includes both authorized workspace paths. Commands are documented but are not executed as part of creating the checkpoint.
