# Agent Workflow & Memory Policy (Roo / GitHub Copilot)

Purpose

- This document defines how AI agents operating in this repository must behave with respect to memory (Qdrant MCP) and the Spec‑Driven workflow. It is an operational policy for agent behaviour and MCP tool use only — it does NOT describe application business logic or implementation details.

Scope

- Applies to all automated agents and agent-modes (Roo, GitHub Copilot personas, and repo-integrated agents) that use the MCP Qdrant tools (`qdrant-find`, `qdrant-store`).
- Excludes: application-level domain rules, feature specs content, and implementation decisions (those live in `specs/` and `.specify/`).

### Agent Operational Rules (Non-Negotiable)

- Agents MUST NOT modify production scripts solely to make tests pass. If a test indicates a real production bug, agents MUST stop, report the issue, and obtain explicit human confirmation before editing production code.
- Agents MUST include the project's standard file header in every new source file they create. The required header must contain:
   - a shebang (`#!/usr/bin/env python3`) for Python files,
   - the project identifier `Architect-Expert-Gap-Forge (AEGF)`,
   - a copyright line (e.g., `Copyright (c) YEAR Name <email>`), and
   - an `SPDX-License-Identifier:` line (for example `SPDX-License-Identifier: Apache-2.0`).

   - CI enforces this check via `scripts/check_headers.py` (workflow: `.github/workflows/header-check.yml`).
   - Agents MUST run `scripts/check_headers.py --check` locally (or enable the repository githook / pre-commit) before staging files; do not stage files that fail the check.

- Violation of these rules renders the agent non-compliant with the Architectural Gold Standard.
- Agents MUST format proposed commit messages using the Conventional Commits convention: `type(scope?): subject`.
   - Allowed `type` values: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `perf`, `style`, `revert`.
   - The `subject` must be imperative, lower-case, and no longer than 50 characters. An optional body may follow after a blank line and should be wrapped at 72 characters.
   - Agents MUST NOT include secrets, credentials, or personal-identifying information in commit messages.

### Language requirement for agents

- Agents MUST use English for all agent-generated content, including but not limited to assistant messages, code comments, docstrings, generated files, and proposed commit messages.
- Use clear, idiomatic English suitable for an international engineering audience; avoid local language-only comments or messages.

Core Principles

1. Spec‑Driven First: Before proposing, editing, or writing any code or infra change, an agent MUST:
    - Read the relevant specification(s) from `.specify/` and `specs/` (feature `spec.md`, `plan.md`, `tasks.md`) that relate to the task.
    - Execute an MCP query via `qdrant-find` scoped to the feature/spec context to retrieve historical decisions, rationale, and related artifacts.
    - If `qdrant-find` fails, fall back to local spec discovery (search `specs/`, `.specify/`, `configs/`) and DO NOT modify code until the spec/context is reconciled with a human.

2. Memory Operations (qdrant-find / qdrant-store):
   - At the start of a discrete task: run `qdrant-find` with a targeted query (feature name, spec path, or explicit tags) to collect prior decisions and context.
   - At the end of a discrete task that produced an enduring design decision or reusable artifact, run `qdrant-store` to persist a short, high‑quality summary and metadata.
   - NEVER store transient debugging logs, ephemeral step‑by‑step traces, test failures, credentials, or PII in Qdrant.

3. What MAY be stored (high value, long-lived):
   - Architectural decisions and their concise rationales (what was chosen and why)
   - Stable API contracts and interface summaries (endpoints, schemas, versioned contracts)
   - Reusable code patterns, snippets (small, canonical examples) and recommended idioms
   - Agent‑verified documentation or decision summaries that aid future reasoning

4. What MUST NOT be stored:
   - Secrets, API keys, tokens, credentials, or any plain-text PII (names, emails, SSNs)
   - Raw test execution logs or ephemeral heap dumps
   - Step-by-step local debugging traces that contain sensitive environment data
   - Large raw artifacts (full source files); store a short summary + reference instead

5. Store Metadata Requirements (mandatory fields):
   - `type`: one of `architecture|contract|pattern|doc-summary|decision`
   - `source_path`: repository-relative path(s) to authoritative files (if applicable)
   - `tags`: list of short tags (feature-slug, team, topic)
   - `author`: agent id or human author
   - `timestamp`: ISO 8601 UTC
   - `summary`: 1–3 sentence human-readable summary
   - `references`: optional list of file paths or URLs
   - `sensitive`: boolean (default `false`) — if `true` agent MUST abort and ask a human

   Example metadata (JSON-like):

```json
{
  "type": "decision",
  "source_path": "specs/000-proyecto-actual/spec.md",
  "tags": ["feature-x","api"],
  "author": "roo-code-aegf-coder",
  "timestamp": "2026-03-08T12:34:56Z",
  "summary": "Resolved to use JSONL records with fields id, prompt, completion; rationale: aligns with eval pipeline",
  "references": ["configs/stage_5_evaluation/eval_config.yaml"],
  "sensitive": false
}
```

6. Query Best Practices
   - Use precise queries (feature slug, spec path, or tag) rather than broad natural language prompts.
   - Inspect the `source_path` and load the referenced file(s) before relying on an entry.
   - Validate returned memory: cross-check with `.specify/` and `specs/` content before applying changes.
   - If multiple conflicting memories exist, prefer the most recent entry with a verifiable `source_path`, and raise a human review if ambiguity persists.

7. Granularity & Summarization
   - Store concise artifacts: 1–3 paragraph summaries only. For large documents, store a short abstract + pointer.
   - Avoid storing full files. If a file must be indexed, store a summary plus `source_path`.

8. Versioning & Supersession
   - When a new decision supersedes an older one, create a new memory entry and include `supersedes: [<old-id>]` in metadata.
   - Do NOT overwrite previous entries unless explicitly instructed by a human and recorded in metadata with justification.

9. Human-in-the-loop & Git Safety
   - Agents may propose patches and commit messages, but MUST NOT run `git commit` or `git push` or modify remote history without explicit, interactive human approval.
   - Agents MUST present a clear delta (files changed and proposed commit message) for human review prior to any staging or commit action.

10. Failure Modes & Logging
   - If `qdrant-find` or `qdrant-store` errors occur, the agent must: 1) log locally, 2) notify the human operator, 3) fall back to local spec discovery where safe.
   - Treat inability to store as non-fatal but require human confirmation if the operation's outcome depends on persistence.

11. Privacy & Redaction
   - Before calling `qdrant-store`, agents must scan the content for PII/credentials and redact or abort and ask for human guidance.
   - If redaction is applied, include `redacted: true` in metadata and a short reason in `summary`.

12. Allowed Tooling Surface (MCP)
   - Use `qdrant-find` for retrieval and `qdrant-store` for persistent memories.
   - Use local search in `.specify/` and `specs/` for authoritative spec content; prefer authoritative spec files over memory search when conflicts arise.

Example: Spec-Driven Code Change Workflow
1. Agent receives request to implement/change feature X.
2. Agent runs `qdrant-find` scoped to `tags:feature-x` + reads `specs/<feature>/spec.md` and `plan.md`.
3. Agent generates a proposed patch and a brief design note.
4. Agent presents the patch and the summary to the human reviewer and requests approval.
5. After human approval and merge, agent runs `qdrant-store` to record the design decision with required metadata.

Governance & Exceptions
 - Any deviation from this policy that affects memory storage (e.g., storing PII due to operational need) requires explicit human approval and must be logged with justification.
 - Agents should periodically (monthly) surface their top stored memories for human review to ensure continued relevance and remove stale entries.

Revision & Ownership
 - Owned by: `platform/ai-ops` team (or repository owners if no team defined)
 - Revision notes: update this file when MCP tooling, schema, or governance changes.
# 🧠 Project Workflow & AI Agent Stack (Single Source of Truth)

This document is the absolute source of truth for all AI agents (GitHub Copilot, Roo Code, Goose, etc.) operating in this repository. If you are an AI agent, you MUST adhere strictly to these rules.

## 1. Core Architecture: Spec-Driven Development (SDD)
We do not use "vibe coding". We use a strict Spec-Driven Development methodology.
- **Specs First:** No code is written without a specification.
- **Workflow:** `/specify` (What) -> `/plan` (How) -> `/tasks` (Breakdown into `prd.json`) -> `/implement` (Code).
- **Language Policy:** All generated documentation, specifications, technical plans, code comments, variable names, and commit messages MUST be written entirely in English.

## 2. Agent Roles & Responsibilities
Agents will assume specific roles based on the current task. Do not mix roles.
- **Architect Role:** Focuses on system design. Reads existing code, creates `spec.md`, `plan.md`, and breaks down tasks into `prd.json`. Does NOT write implementation code.
- **Code/Developer Role:** Focuses on implementation. Reads the current task from `prd.json` or `tasks.md`, writes the code, runs tests, and updates `progress.txt` with transient learnings.
- **Autonomous Execution (Ralph Loop / Goose):** Operates statelessly. Finds the first task in `prd.json` with `"passes": false`, implements it, verifies via tests, commits to Git, marks as `"passes": true`, and terminates to clear context.

## 3. Memory Management (Qdrant MCP)
You have access to an MCP server connected to a Qdrant vector database. It is your exclusive responsibility to keep this index updated without human intervention.
- **Research Phase (`qdrant-find`):** Before writing or modifying any file, always search the database for similar code patterns, existing implementations, or previous architectural decisions.
- **Indexing Phase (`qdrant-store`):** Use this ONLY for permanent, long-term knowledge. 
  - **YOU MUST STORE:** Architectural decisions, core business rules, API contracts, and reusable code patterns.
  - **RESTRICTION (DO NOT STORE):** NEVER save transient states, temporary test failures, debugging logs, to-do lists, or step-by-step progress. Transient information belongs in `progress.txt`, not in the vector database.

## 4. Data Format Optimization
- **Large Datasets:** If you need to ingest or output massive JSON files (logs, schemas, mock data), utilize the TOON format to minimize token consumption.
