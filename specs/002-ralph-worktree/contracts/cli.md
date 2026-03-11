# CLI Contract: ralph-loop.sh

**Type**: Bash CLI script  
**File**: `.ralph/ralph-loop.sh`  
**Feature**: 002-ralph-worktree

---

## Synopsis

```
.ralph/ralph-loop.sh <spec-dir> [flags]
.ralph/ralph-loop.sh --resume [flags]
.ralph/ralph-loop.sh --clean [<slug>]
```

---

## Arguments

| Argument | Required | Description |
|---|---|---|
| `<spec-dir>` | Yes (unless `--resume` or `--clean`) | Path to spec directory, e.g. `specs/001-stage1-discovery` |

---

## Flags

### Existing flags (unchanged contract)

| Flag | Type | Default | Description |
|---|---|---|---|
| `--max N` | int | `100` | Global max iterations |
| `--review-every N` | int | `5` | Artifact review interval |
| `--agent TYPE` | string | `claude` | Agent: `claude\|goose\|custom` |
| `--no-yolo` | bool | off | Disable `--dangerously-skip-permissions` |
| `--resume` | bool | off | Resume from existing `.ralph/state.json` |
| `-h, --help` | bool | off | Show help |

### New flags (this feature)

| Flag | Type | Default | Description |
|---|---|---|---|
| `--no-worktree` | bool | off | Legacy mode: disable git worktree entirely |
| `--skip-preflight` | bool | off | Skip all preflight checks (prints `[WARN]`) |
| `--clean [slug]` | string? | (active slug from state.json) | Clean merged worktrees for given feature slug |

---

## Environment Variables

### Existing (unchanged)

| Variable | Default | Description |
|---|---|---|
| `RALPH_AGENT` | `claude` | Agent type |
| `RALPH_MAX_ITER` | `100` | Max iterations |
| `RALPH_REVIEW_EVERY` | `5` | Review interval |
| `RALPH_MAX_RETRIES` | `5` | Per-task retry limit |
| `RALPH_YOLO` | `true` | Skip-permissions flag |
| `CLAUDE_CMD` | `claude` | Claude CLI binary |
| `GOOSE_MODEL` | — | Goose model |
| `GOOSE_PROVIDER` | — | Goose provider |

### New (this feature)

| Variable | Default | Description |
|---|---|---|
| `RALPH_PUSH` | `false` | Set `true` to push worktree branch to origin after each iteration |

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success: all tasks complete, or `--clean` finished, or `--help` |
| `1` | Error: preflight failed, bad args, agent not found, git error |

---

## Output Contract — normal run

Required lines printed to stdout at successful/capped termination (worktree mode):

```
[INFO] Worktree: .worktrees/<slug>-<ts>/
[INFO] Branch:   ralph/<slug>-<ts>
[INFO] To merge:
[INFO]   git merge --squash ralph/<slug>-<ts> && git commit -m "feat(<slug>): <description>"
[INFO] Or (preserve full history):
[INFO]   git merge ralph/<slug>-<ts>
```

---

## Output Contract — preflight failure

Required lines printed to stderr + exit 1 (before any worktree is created):

```
[ERROR] <specific problem description>
[INFO]  Fix: <exact command to resolve>
```

Examples:
```
[ERROR] Hay 3 archivos modificados sin commit en el repo principal
[INFO]  Fix: git add -A && git commit -m "wip: save work before ralph"

[ERROR] Merge en curso detectado (.git/MERGE_HEAD)
[INFO]  Fix: git merge --abort

[ERROR] safe.directory error — el repo puede ser propiedad de otro usuario
[INFO]  Fix: git config --global --add safe.directory /ruta/al/repo
```

---

## Backwards Compatibility

All behavior when `--no-worktree` is passed MUST be identical to the original script (pre-feature). The flag is the explicit opt-out for legacy mode.

The existing `git push origin "$current_branch"` line (line 803) is replaced by conditional push logic (RALPH_PUSH guard). When `--no-worktree` and `RALPH_PUSH` is unset, no push happens (aligns previous silent-fail behavior).
