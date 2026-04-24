# Tasks: Prompt Externalization

## Phase: POC

Focus: Prove the conversion pipeline works end-to-end with the simplest source (plain text).

- [ ] T-01 [POC] Create prompts_backtracking.example.yaml from plain text sources
  - **Do:**
    1. Read `configs/prompts/backtracking_system.txt` (26 lines, English) and `configs/prompts/reconstruction_system.txt` (36 lines, English)
    2. Create `src/curation/prompts_backtracking.example.yaml` with `prompts:` top-level key
    3. Map: `prompts.backtracking_system.system` = full content of backtracking_system.txt
    4. Map: `prompts.reconstruction_system.system` = full content of reconstruction_system.txt
    5. Both source files are already English — verify fidelity, keep as-is
    6. Add AEGF copyright header comment block at top
  - **When:** Done when `src/curation/prompts_backtracking.example.yaml` exists, valid YAML, 2 keys under `prompts:`, content matches source.
  - **Verify:** `python -c "import yaml; d=yaml.safe_load(open('src/curation/prompts_backtracking.example.yaml')); assert 'prompts' in d; assert len(d['prompts'])==2; print('T-01 PASS')"`
  - **Commit:** `feat(spec): POC externalize backtracking prompts to YAML`
  - _Requirements: FR-1, FR-2, US-7_
  - _Design: Component 7_

## Phase: Remaining Files

- [ ] T-02 [P] Create prompts_frontend.example.yaml from Python constants
  - **When:** Done when file exists with 5 prompt keys (4 system + 1 user) and dead code header comment.
  - **Verify:** `python -c "import yaml; d=yaml.safe_load(open('src/export/prompts_frontend.example.yaml')); assert len(d['prompts'])==5; print('T-02 PASS')"`
  - **Commit:** `feat(spec): externalize frontend taxonomy prompts`
  - _Requirements: FR-1, US-6_
  - _Design: Component 6_
  - **Do:**
    1. Read `src/export/frontend_taxonomy_prompts.py` — constants at lines 34/70/82/118/136
    2. Create YAML with header comment noting dead code (file never imported)
    3. Map each constant to `prompts.<name>.system` or `.user`
    4. Content is already English — verify fidelity, keep as-is

- [x] T-03 [P] Create prompts_hard_query.example.yaml from Python method
  - **When:** Done when file exists with `forbidden_terms` (list, kept as-is) and `problem_focused` (translated) under `prompts:`.
  - **Verify:** `python -c "import yaml; d=yaml.safe_load(open('src/factory/prompts_hard_query.example.yaml')); assert 'forbidden_terms' in d['prompts']; assert 'problem_focused' in d['prompts']; print('T-03 PASS')"`
  - **Commit:** `feat(spec): externalize hard query prompts`
  - _Requirements: FR-1, US-2_
  - _Design: Component 2_
  - **Do:**
    1. Read `src/factory/hard_query_builder.py` — `_default_templates()` at line 73, `forbidden_terms` at line 76
    2. Extract `problem_focused` template, translate Spanish to English
    3. Store `forbidden_terms` as YAML list under `prompts.forbidden_terms` (keep as-is — literal match strings)
    4. Store template as `prompts.problem_focused.system`

- [ ] T-04 [P] Create prompts_trajectory.example.yaml from Python method
  - **When:** Done when file exists with 6 turn template keys under `prompts:`, all translated to English.
  - **Verify:** `python -c "import yaml; d=yaml.safe_load(open('src/factory/prompts_trajectory.example.yaml')); assert len(d['prompts'])==6; print('T-04 PASS')"`
  - **Commit:** `feat(spec): externalize trajectory turn templates`
  - _Requirements: FR-1, US-1_
  - _Design: Component 1_
  - **Do:**
    1. Read `src/factory/trajectory_generator.py` — `_default_templates()` at line 63
    2. Extract 6 turn templates: observation, reasoning, action, error, correct, verify
    3. Translate each from Spanish to English (preserve `{var}` placeholders, use `$var` per DSPy convention per AC-1.5)
    4. Store as `prompts.<turn_type>.system` with empty `user` field

- [ ] T-05 [VERIFY] Quality checkpoint: POC files valid
  - **When:** Done when POC and POC-adjacent files all parse as valid YAML.
  - **Verify:** `python -c "import yaml; [yaml.safe_load(open(f)) for f in ['src/curation/prompts_backtracking.example.yaml','src/export/prompts_frontend.example.yaml','src/factory/prompts_hard_query.example.yaml','src/factory/prompts_trajectory.example.yaml']]; print('V1 PASS')"`
  - **Commit:** `chore(spec): pass quality checkpoint`
  - _Design: All above_
  - **Do:** Run the Python verify script below. If any file fails to parse, stop and report which file caused the failure. If all pass, proceed.

- [ ] T-06 Create prompts_judge.example.yaml from eval_prompts.yaml
  - **When:** Done when file exists with 4 prompt groups, `gap_analysis` translated from Spanish, English groups verified for fidelity.
  - **Verify:** `python -c "import yaml; d=yaml.safe_load(open('src/audit/prompts_judge.example.yaml')); assert set(d['prompts'].keys())=={'professor_exam','professor_judge','gap_analysis','professor_judge_calibration'}; print('T-06 PASS')"`
  - **Commit:** `feat(spec): externalize judge/evaluation prompts`
  - _Requirements: FR-1, US-3_
  - _Design: Component 3_
  - **Do:**
    1. Read `configs/stage_5_evaluation/eval_prompts.yaml`
    2. Direct copy of 4 groups: `professor_exam`, `professor_judge`, `gap_analysis`, `professor_judge_calibration`
    3. `gap_analysis` is Spanish -> translate to English
    4. `professor_exam`, `professor_judge`, `professor_judge_calibration` are English -> verify fidelity

- [ ] T-07 Create prompts_calibration.example.yaml from list-of-objects
  - **When:** Done when file exists with 6 prompt keys (001-006), each with `.system` (parameter_target), `.user` (translated question), and `.metadata` dict.
  - **Verify:** `python -c "import yaml; d=yaml.safe_load(open('src/audit/prompts_calibration.example.yaml')); assert len(d['prompts'])==6; assert all('metadata' in v for v in d['prompts'].values()); print('T-07 PASS')"`
  - **Commit:** `feat(spec): externalize calibration prompts with metadata`
  - _Requirements: FR-1, FR-4, FR-5, US-4_
  - _Design: Component 4_
  - **Do:**
    1. Read `configs/stage_6_calibration/calibration_prompts.yaml` — list-of-objects format
    2. For each active prompt (ids 001-006): flatten to `prompts.<id>.system` = parameter_target, `prompts.<id>.user` = translated question
    3. Store `type`, `parameter_target`, `evaluation_focus` as `prompts.<id>.metadata`
    4. Translate questions from Spanish to English

- [ ] T-08 Create prompts_taxonomy.example.yaml from nested YAML
  - **When:** Done when file exists with ~21 prompt group keys, excluded data sections, Spanish translated, agentic_taxonomy difference noted in header.
  - **Verify:** `python -c "import yaml; d=yaml.safe_load(open('src/factory/prompts_taxonomy.example.yaml')); k=list(d['prompts'].keys()); assert len(k)>=18; print(f'T-08 PASS ({len(k)} keys)')"`
  - **Commit:** `feat(spec): externalize taxonomy prompts consolidated`
  - _Requirements: FR-1, FR-6, US-5_
  - _Design: Component 5_
  - **Do:**
    1. Read `configs/stage_2_factory/taxonomy/home_assistant/prompts_taxonomy.yaml`
    2. Exclude: `version`, `ha_error_templates`, `legacy_2023_patterns`, `jinja_ha_error_templates`, `jinja_legacy_2023_patterns`, `tools_definition`
    3. Flatten dotted paths: `system.python.base` -> `system_python_base`, map to `.system` or `.user` based on parent
    4. Translate all Spanish content to English
    5. Add header comment noting `agentic_taxonomy.yaml` is 99% identical

## Phase: Verification

- [ ] T-09 [VERIFY] Final verification: all 7 files valid, schema-compliant, no Spanish remaining
  - **Do:**
    1. Run the Python verify script below (checks parse, counts, zero diff)
    2. If any check fails, stop, report the specific failure, and fix
    3. Verify no Spanish text remains in translated files (except domain terms/forbidden_terms)
    4. Verify zero diff on non-`.example.yaml` files (hard invariant: FR-8/FR-9)
    5. Confirm: all 7 output paths are under `src/*/` — no overlap with existing `configs/` files, no existing imports affected
  - **When:** Done when all 7 files parse, prompt counts match source, no Spanish text in translated files, zero diff on non-new files.
  - **Verify:**
    ```bash
    python -c "
    import yaml, sys, subprocess, re

    files = [
        'src/factory/prompts_trajectory.example.yaml',
        'src/factory/prompts_hard_query.example.yaml',
        'src/factory/prompts_taxonomy.example.yaml',
        'src/audit/prompts_judge.example.yaml',
        'src/audit/prompts_calibration.example.yaml',
        'src/export/prompts_frontend.example.yaml',
        'src/curation/prompts_backtracking.example.yaml',
    ]

    # 1. All parse + have prompts top-level key
    for f in files:
        d = yaml.safe_load(open(f))
        assert 'prompts' in d, f'{f}: missing prompts key'

    # 2. Prompt counts (minimum expected)
    counts = {
        'src/factory/prompts_trajectory.example.yaml': 6,
        'src/factory/prompts_hard_query.example.yaml': 2,  # forbidden_terms + problem_focused
        'src/factory/prompts_taxonomy.example.yaml': 18,   # ~21 prompt groups, expect >=18
        'src/audit/prompts_judge.example.yaml': 4,
        'src/audit/prompts_calibration.example.yaml': 6,
        'src/export/prompts_frontend.example.yaml': 5,     # 4 system + 1 user
        'src/curation/prompts_backtracking.example.yaml': 2,
    }
    for f, expected in counts.items():
        d = yaml.safe_load(open(f))
        actual = len(d['prompts'])
        assert actual >= expected, f'{f}: expected >= {expected}, got {actual}'

    # 3. Zero diff on non-new files
    result = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().split('\n') if l and '.example.yaml' not in l]
    assert not modified, f'Modified non-new files: {modified}'

    print('T-09 PASS')
    "
    ```
  - **Commit:** `chore(spec): verify all 7 prompt files`
  - _Requirements: FR-1 through FR-9, NFR-1 through NFR-3_

## Notes

- POC shortcut: T-01 (backtracking) is the simplest source (plain text -> YAML, 2 keys). If this works, the harder sources (Python method extraction, nested YAML flattening) follow the same pattern.
- No code changes: all 7 output files are new. No `.py` or existing `.yaml` modified.
- Translation: Spanish->English for trajectory, hard_query, judge (gap_analysis), calibration, taxonomy, backtracking. Frontend is already English.
- Hard invariant: `git diff --name-only` must show zero non-`.example.yaml` files.
