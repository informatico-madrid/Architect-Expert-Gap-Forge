# Project Agents Architecture

> This document provides an overview of the agents defined in `.github/agents/` so the CTO can quickly understand what each one does without reading source code.

---

## 🎯 Main Agents

### AEGF.agent.md
**Purpose:** Main AEGF project agent

The main orchestrator agent for the AEGF (Architect-Expert-Gap-Forge) project. It governs the entire synthetic data generation pipeline to solve the "Knowledge Cutoff" problem in LLMs. It coordinates the discovery, factory, curation, training, and evaluation phases.

---

### coder.agent.md
**Purpose:** Code implementation agent

A specialized agent for writing, modifying, and refactoring Python code. It uses spec-driven development patterns and follows the conventions defined in the project constitution.

---

### copilot-instructions.md
**Purpose:** GitHub Copilot configuration

Specific instructions for GitHub Copilot on how to interact with the project, including security restrictions, code conventions, and expected behaviors.

---

## 🔧 Speckit Workflow Agents

Speckit is the specification-based workflow system. Each agent handles a specific phase of the feature lifecycle:

| Agent | Phase | Description |
|-------|-------|-------------|
| **speckit.specify** | Spec | Initial feature specification - defines what will be built |
| **speckit.analyze** | Analysis | Analyzes existing code and dependencies before implementation |
| **speckit.plan** | Planning | Creates detailed technical plans with specific tasks |
| **speckit.tasks** | Tasks | Generates and manages the task checklist (tasks.md) |
| **speckit.implement** | Implementation | Executes implementation following the established plan |
| **speckit.checklist** | Verification | Verifies that implementation meets acceptance criteria |
| **speckit.clarify** | Clarification | Resolves ambiguities and clears up confusing requirements |
| **speckit.qa** | Quality Assurance | Runs quality tests and validations |
| **speckit.constitution** | Constitution | Maintains and enforces project rules |
| **speckit.taskstoissues** | Issues | Converts tasks into GitHub issues |

---

## 🔄 Speckit Workflow

```
speckit.specify → speckit.clarify → speckit.analyze → speckit.plan 
     → speckit.tasks → speckit.implement → speckit.checklist → speckit.qa
```

Each agent is autonomous but consults `speckit.constitution` to maintain consistency with project policies.

---

## 📁 Definitions Location

| Type | Path |
|------|------|
| Agents | `.github/agents/*.agent.md` |
| Prompts | `.github/prompts/speckit.*.prompt.md` |
| Constitution | `.specify/memory/constitution.md` |

---

*Automatically generated for repository audit*
