# Epic 1: Layer 1 DSPy Integration

BMAD Epic 1 from `_bmad-output/planning-artifacts/epics.md` (v4.0).

This epic is being decomposed by Smart Ralph triage.
See BMAD artifacts in `_bmad-output/planning-artifacts/` for reference.

---

## Source Bug Corrections from Prompt Externalization (Epic 0)

During the `prompt-externalization` spec completion (Epic 0), an adversarial
review (internal + independent external) found issues in the source files that
the `.example.yaml` files faithfully preserved. These are NOT bugs introduced by
the externalization — they are pre-existing source bugs that Epic 1 must fix
when converting `.example.yaml` templates into DSPy Signatures.

**Key principle**: Epic 0's job was to catalog and translate (create `.example.yaml`
templates). Epic 1's job is to convert those templates into DSPy Signatures,
which is where the source bugs should actually be fixed.

### The 7 Issues

| # | Issue | Severity | Epic 1 Story | Fix Required |
|---|-------|----------|-------------|--------------|
| 1 | Typo "Architecture architecture" in `eval_prompts.yaml:10` | LOW | 1.4 (JudgeSignature) | Fix typo when creating DSPy Signature for judge |
| 2 | Calibration `parameter_target` stored as `.system` key | MEDIUM | 1.6 (CalibrationSignature) | Properly structure parameter metadata in Signature, not as prompt text |
| 3 | `$var` vs `{var}` placeholder inconsistency across sources | MEDIUM | 1.1 (TrajectorySignature) | Standardize placeholder syntax in all DSPy Signatures |
| 4 | `</think>` trailing space inconsistency in judge prompts | LOW | 1.4 (JudgeSignature) | Normalize whitespace during Signature creation |
| 5 | Python vs Jinja output protocol inconsistency | FALSE POSITIVE | None | **No fix needed** — both use identical `<write_action>/<path>/<content>` format |
| 6 | Forbidden terms in Spanish not documented for DSPy | MEDIUM | 1.7 (Hard Query) | Add explicit comment in Signature: "These are literal match strings from source — keep as-is" |
| 7 | Dead code `frontend_taxonomy_prompts.py` never imported | LOW | 1 or cleanup task | Remove dead file when DSPy Signatures replace its constants |

### Notes per Story

**Story 1.1 (TrajectorySignature)**:
- Issue #3: All trajectory prompts use `{var}` (Python `str.format`). Do NOT use `$var`.
- Match the existing production code convention.

**Story 1.4 (JudgeSignature)**:
- Issue #1: Fix "Architecture architecture" → "Architecture" in `gap_analysis` prompt.
- Issue #4: Normalize `</think>` whitespace across all judge prompts.

**Story 1.6 (CalibrationSignature)**:
- Issue #2: The `parameter_target` field (e.g., "top_k, presence_penalty") is metadata
  about the calibration experiment, NOT part of the prompt content. Structure it as
  a separate field in the Signature, not as `.system` text.

**Story 1.7 (Hard Query)**:
- Issue #6: The `forbidden_terms` list contains literal Python match strings.
  Document in the Signature: "MUST remain in original language — they are literal
  pattern match strings from source code, not user-facing prompts."

### Source Files Referenced

| Source File | Location | Language |
|-------------|----------|----------|
| `configs/stage_5_evaluation/eval_prompts.yaml` | Stage 5 eval | gap_analysis: Spanish→English (translated), professor_*: English |
| `configs/stage_6_calibration/calibration_prompts.yaml` | Stage 6 calib | Spanish→English (translated) |
| `configs/stage_2_factory/taxonomy/.../prompts_taxonomy.yaml` | Stage 2 taxonomy | Spanish→English (translated) |
| `src/factory/hard_query_builder.py` | Factory | Mixed: forbidden_terms Spanish literals, templates English |
| `src/factory/trajectory_generator.py` | Factory | Spanish→English (translated) |
| `src/export/frontend_taxonomy_prompts.py` | Export | English (dead code, never imported) |
