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
