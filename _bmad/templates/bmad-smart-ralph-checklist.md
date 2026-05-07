# BMAD ⇄ smart-ralph Integration Checklist

Purpose: minimal contract for smart-ralph to report implementation progress so BMAD can track sprints/epics/stories.

Recommended path convention
- _bmad-output/implementation-artifacts/sprints/{sprint_id}/stories/{story_id}-status.json

Required fields (in JSON status file)
- sprint_id, epic_id, story_id
- status: queued | running | blocked | done | failed
- timestamps: created_at, started_at, finished_at, last_update
- executor.type, executor.id
- artifacts: commits[], prs[], builds[]
- tests: unit/integration/e2e {status, report}
- blockers[]

When to write/update
- Create file when story queued
- Update status to "running" when start
- Append artifacts as commits/PRs are created
- Update tests and code_review results when available
- Set finished_at and status when done or failed

BMAD consumption
- BMAD watches the path convention or can be invoked via `bmad-sprint-status` to refresh
- Keep files idempotent: overwrite full JSON or perform atomic write (write to tmp + move)

Examples
- Minimal file: use `sprint-story-status-template.json` (placed in _bmad/templates)
- Summary file per sprint: `_bmad-output/implementation-artifacts/sprints/{sprint_id}/sprint-status.json`

Tips
- Include PR and commit URLs so BMAD links artifacts
- Use consistent executor.id (smart-ralph job id) for traceability
- Log blockers with severity and contact info

If desired, smart-ralph can POST these JSONs to a small webhook service that writes them into the path convention (atomic file writes recommended).
