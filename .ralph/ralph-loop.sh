#!/usr/bin/env bash
#
# Ralph Loop — SpecKit Integrated Edition
#
# Autonomous task execution loop with:
#   - JSON state machine (ralph-state.json)
#   - Three-layer verification (contradiction, signal, artifact review)
#   - [VERIFY] checkpoint support
#   - Recovery mode (auto-generate fix tasks on failure)
#   - Per-task retry limits
#   - Global iteration safety cap
#   - progress.txt log for human audit
#
# Usage:
#   .ralph/ralph-loop.sh specs/001-stage1-discovery    # Execute spec
#   .ralph/ralph-loop.sh specs/001-feature --max 50    # With iteration cap
#   .ralph/ralph-loop.sh --resume                      # Resume from state.json
#
# Environment:
#   RALPH_AGENT          Agent CLI: claude (default), goose, custom
#   RALPH_MAX_ITER       Global max iterations (default: 100)
#   RALPH_REVIEW_EVERY   Run artifact review every N tasks (default: 5)
#   RALPH_MAX_RETRIES    Per-task retry limit (default: 5)
#   CLAUDE_CMD           Claude CLI binary (default: claude)
#   GOOSE_MODEL          Goose model for work phase
#   GOOSE_PROVIDER       Goose provider for work phase
#   RALPH_VLLM_URL       vLLM API URL (default: http://192.168.1.201:4000)
#   RALPH_VLLM_MODEL     vLLM model name (default: qwen3-5-35b-a3b-nvfp4)
#   RALPH_VLLM_API_KEY   vLLM API key (default: EMPTY for local)
#
set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RALPH_DIR="$SCRIPT_DIR"

RALPH_AGENT="${RALPH_AGENT:-claude}"
CLAUDE_CMD="${CLAUDE_CMD:-claude}"
RALPH_MAX_ITER="${RALPH_MAX_ITER:-100}"
RALPH_REVIEW_EVERY="${RALPH_REVIEW_EVERY:-5}"
RALPH_MAX_RETRIES="${RALPH_MAX_RETRIES:-5}"
RALPH_YOLO="${RALPH_YOLO:-true}"

# Test concurrency guard: limit how many pytest processes this loop allows
RALPH_TEST_CONCURRENCY="${RALPH_TEST_CONCURRENCY:-1}"

# vLLM local backend configuration (for goose agent)
RALPH_VLLM_URL="${RALPH_VLLM_URL:-http://192.168.1.201:4000}"
RALPH_VLLM_MODEL="${RALPH_VLLM_MODEL:-qwen3-5-35b-a3b-nvfp4}"
RALPH_VLLM_API_KEY="${RALPH_VLLM_API_KEY:-}"
# Use CUSTOM_VLLM_API_KEY because goose custom provider expects this env var
CUSTOM_VLLM_API_KEY="${CUSTOM_VLLM_API_KEY:-${RALPH_VLLM_API_KEY:-}}"

# Worktree mode globals (T01)
WORKTREE_ENABLED=true
SKIP_PREFLIGHT=false
RALPH_PUSH="${RALPH_PUSH:-false}"
PUSH_TRACKING_SET=false
WORKTREE_PATH=""
WORKTREE_BRANCH=""
WORKTREE_CREATED_AT=""
BASE_BRANCH=""
CLEAN_MODE=false
CLEAN_SLUG=""

COUNT_SCRIPT="$RALPH_DIR/scripts/count_tasks.py"
MERGE_SCRIPT="$RALPH_DIR/scripts/merge_state.py"
CONSTITUTION="$PROJECT_DIR/.specify/memory/constitution.md"
SPECKIT_IMPLEMENT_AGENT="$PROJECT_DIR/.github/agents/speckit.implement.agent.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Logging
# ============================================================================
log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Memory tracking for debugging memory leaks
RALPH_MEM_LOG="${RALPH_MEM_LOG:-$PROJECT_DIR/.ralph/memory.log}"

log_memory() {
    local label="${1:-unknown}"
    if command -v python3 &>/dev/null; then
        local mem_mb
        mem_mb=$(python3 -c "
import sys
try:
    import psutil
    print(f'{psutil.Process().memory_info().rss / 1024 / 1024:.1f}')
except ImportError:
    import resource
    mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    import platform
    if platform.system() == 'Darwin':
        print(f'{mem_kb / 1024 / 1024:.1f}')
    else:
        print(f'{mem_kb / 1024:.1f}')
" 2>/dev/null || echo "N/A")
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iter=$global_iter Label=$label Mem=${mem_mb}MB" >> "$RALPH_MEM_LOG"
    fi
}

compute_sha1() {
    local f="$1"
    if [[ ! -f "$f" ]]; then
        echo ""
        return 0
    fi
    if command -v sha1sum >/dev/null 2>&1; then
        sha1sum "$f" | awk '{print $1}'
    else
        python3 - "$f" <<'PY'
import hashlib,sys
p=sys.argv[1]
print(hashlib.sha1(open(p,'rb').read()).hexdigest())
PY
    fi
}

# ============================================================================
# Help
# ============================================================================
show_help() {
    cat << 'EOF'
Ralph Loop — SpecKit Integrated Edition

Autonomous task execution with JSON state machine and multi-layer verification.

USAGE:
    .ralph/ralph-loop.sh <spec-dir>              # Execute spec tasks
    .ralph/ralph-loop.sh <spec-dir> --max 50     # Limit iterations
    .ralph/ralph-loop.sh --resume                 # Resume from state.json

OPTIONS:
    --max N           Maximum iterations (default: 100)
    --review-every N  Artifact review interval (default: every 5 tasks)
    --agent TYPE      Agent: claude|goose|custom (default: claude)
    --no-yolo         Disable skip-permissions flag
    --resume          Resume from existing .ralph/state.json
    --no-worktree     Run in legacy mode without git worktree
    --skip-preflight  Skip preflight checks [WARN]
    --clean [slug]    Remove merged worktrees for given spec slug
    -h, --help        Show this help

WORKFLOW:
    1. Initialize state.json from tasks.md
    2. Pick next incomplete task (by taskIndex)
    3. WORK PHASE: agent implements the task
    4. VERIFY PHASE: three-layer verification
       Layer 1: Contradiction detection
       Layer 2: TASK_COMPLETE signal check
       Layer 3: Periodic artifact review (every N tasks)
    5. Update state.json, progress.txt, tasks.md
    6. Repeat until ALL_TASKS_COMPLETE or max iterations

AGENTS:
    claude   - Claude Code CLI (default)
    goose    - Goose CLI with recipes
    custom   - Set RALPH_CUSTOM_CMD environment variable

VLLM BACKEND (for goose agent):
    When RALPH_VLLM_URL is set, goose will use the OpenAI-compatible
    API at that URL instead of external providers.
    Environment variables:
    - RALPH_VLLM_URL      vLLM API URL (default: http://192.168.1.201:4000)
    - RALPH_VLLM_MODEL    vLLM model name (default: qwen3-5-35b-a3b-nvfp4)
    - RALPH_VLLM_API_KEY  API key (default: EMPTY for local)

Example:
    RALPH_AGENT=goose RALPH_VLLM_URL=http://192.168.1.201:4000 .ralph/ralph-loop.sh specs/xxx

EOF
}

# ============================================================================
# Argument Parsing
# ============================================================================
SPEC_DIR=""
RESUME_MODE=false

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --max)
                RALPH_MAX_ITER="$2"
                shift 2 ;;
            --review-every)
                RALPH_REVIEW_EVERY="$2"
                shift 2 ;;
            --agent)
                RALPH_AGENT="$2"
                shift 2 ;;
            --no-yolo)
                RALPH_YOLO=false
                shift ;;
            --resume)
                RESUME_MODE=true
                shift ;;
            --no-worktree)
                WORKTREE_ENABLED=false
                shift ;;
            --skip-preflight)
                SKIP_PREFLIGHT=true
                shift ;;
            --clean)
                CLEAN_MODE=true
                CLEAN_SLUG="${2:-}"
                [[ -n "${2:-}" ]] && shift
                shift ;;
            -h|--help)
                show_help
                exit 0 ;;
            -*)
                log_error "Unknown flag: $1"
                show_help
                exit 1 ;;
            *)
                SPEC_DIR="$1"
                shift ;;
        esac
    done
}

# ============================================================================
# State Management
# ============================================================================
STATE_FILE="$PROJECT_DIR/.ralph/state.json"

read_state() {
    local key="$1"
    python3 -c "import json,sys; d=json.load(open('$STATE_FILE')); print(d.get('$key',''))"
}

init_state() {
    local spec_dir="$1"
    local tasks_file="$spec_dir/tasks.md"
    local feature_id feature_name

    if [[ ! -f "$tasks_file" ]]; then
        log_error "tasks.md not found: $tasks_file"
        exit 1
    fi

    # Extract feature ID and name from dir name (e.g., 001-stage1-discovery)
    local dir_basename
    dir_basename=$(basename "$spec_dir")
    feature_id=$(echo "$dir_basename" | grep -oP '^\d{3}' || echo "000")
    feature_name="$dir_basename"

    log_info "Initializing state from: $tasks_file"

    python3 "$MERGE_SCRIPT" "$STATE_FILE" \
        --init "$tasks_file" \
        --set "featureId=$feature_id" \
        --set "name=$feature_name" \
        --set "basePath=$spec_dir" \
        --set "maxGlobalIterations=$RALPH_MAX_ITER" \
        --set "maxTaskIterations=$RALPH_MAX_RETRIES" \
        --set "reviewInterval=$RALPH_REVIEW_EVERY" \
        --set "lastReviewAt=0"

    # Write worktree fields if worktree mode enabled (T11)
    if [[ "$WORKTREE_ENABLED" == "true" ]]; then
        python3 "$MERGE_SCRIPT" "$STATE_FILE" \
            --set "worktreePath=$WORKTREE_PATH" \
            --set "worktreeBranch=$WORKTREE_BRANCH" \
            --set "worktreeCreatedAt=$WORKTREE_CREATED_AT" \
            --set "baseBranch=$BASE_BRANCH"
    fi

    log_ok "State initialized: $(python3 "$COUNT_SCRIPT" "$tasks_file")"
}

update_state() {
    python3 "$MERGE_SCRIPT" "$STATE_FILE" "$@"
}

# ============================================================================
# Task Operations
# ============================================================================
get_task_counts() {
    local tasks_file="$1"
    python3 "$COUNT_SCRIPT" "$tasks_file"
}

get_task_at_index() {
    # Extract the Nth task line (0-based) from tasks.md
    local tasks_file="$1"
    local index="$2"
    python3 -c "
import re, sys
from pathlib import Path

TASK_RE = re.compile(r'^- \[(?P<mark>[ xX])\] ')
lines = Path('$tasks_file').read_text().splitlines()
count = 0
for i, line in enumerate(lines):
    if TASK_RE.match(line):
        if count == $index:
            # Collect task line + indented body
            result = [line]
            for j in range(i+1, len(lines)):
                if lines[j].startswith('  ') or lines[j].startswith('\t'):
                    result.append(lines[j])
                else:
                    break
            print('\n'.join(result))
            sys.exit(0)
        count += 1
print('TASK_NOT_FOUND', file=sys.stderr)
sys.exit(1)
"
}

mark_task_done() {
    # Mark the Nth task (0-based) as [x] in tasks.md
    local tasks_file="$1"
    local index="$2"
    python3 -c "
import re
from pathlib import Path

TASK_RE = re.compile(r'^- \[ \] ')
path = Path('$tasks_file')
lines = path.read_text().splitlines()
count = 0
for i, line in enumerate(lines):
    if TASK_RE.match(line):
        if count == $index:
            lines[i] = line.replace('- [ ] ', '- [x] ', 1)
            break
        count += 1
path.write_text('\n'.join(lines) + '\n')
"
}

# ============================================================================
# Contradiction Detection (Layer 1)
# ============================================================================
CONTRADICTION_PHRASES=(
    "requires manual"
    "cannot be automated"
    "could not complete"
    "needs human"
    "manual intervention"
    "unable to"
    "cannot complete"
    "cannot do"
    "cannot execute"
    "i cannot"
    "i can't"
    "beyond my capacity"
)

check_contradictions() {
    local output="$1"
    local output_lower
    output_lower=$(echo "$output" | tr '[:upper:]' '[:lower:]')

    for phrase in "${CONTRADICTION_PHRASES[@]}"; do
        if echo "$output_lower" | grep -qF "$phrase"; then
            if echo "$output" | grep -qE "TASK_COMPLETE|<promise>DONE</promise>"; then
                echo "CONTRADICTION: agent says '$phrase' but also claims completion"
                return 1
            fi
        fi
    done
    return 0
}

# ============================================================================
# Signal Verification (Layer 2)
# ============================================================================
check_completion_signal() {
    local output="$1"
    # Look for TASK_COMPLETE as a standalone output line (not in quotes)
    # Check last lines only
    local last_lines
    last_lines=$(echo "$output" | tail -3)
    if echo "$last_lines" | grep -qF "TASK_COMPLETE"; then
        # Make sure it's standalone, not quoted
        if echo "$last_lines" | grep -qE "^TASK_COMPLETE$"; then
            return 0
        fi
    fi
    # Also check for promise format
    if echo "$output" | grep -qF "<promise>DONE</promise>"; then
        return 0
    fi
    return 1
}

check_all_complete_signal() {
    local output="$1"
    # Look for ALL_TASKS_COMPLETE as a standalone output line (not in quotes)
    # Check last lines only
    local last_lines
    last_lines=$(echo "$output" | tail -3)
    if echo "$last_lines" | grep -qF "ALL_TASKS_COMPLETE"; then
        # Make sure it's standalone, not quoted
        if echo "$last_lines" | grep -qE "^ALL_TASKS_COMPLETE$"; then
            return 0
        fi
    fi
    # Also check for promise format
    if echo "$output" | grep -qF "<promise>ALL_DONE</promise>"; then
        return 0
    fi
    return 1
}

# ============================================================================
# Artifact Review (Layer 3)
# ============================================================================
should_run_review() {
    local task_index="$1"
    local total_tasks="$2"
    local last_review="$3"
    local interval="$4"

    # Review at: every N tasks, phase boundaries, final task
    if (( task_index - last_review >= interval )); then
        return 0
    fi
    if (( task_index == total_tasks - 1 )); then
        return 0
    fi
    return 1
}

run_artifact_review() {
    local spec_dir="$1"
    local task_desc="$2"
    local task_index="$3"

    log_info "Running artifact review (task $task_index)..."

    local review_prompt
    local _review_wt_path="${WORKTREE_PATH:-$PROJECT_DIR}"
    local _review_constitution="${_review_wt_path}/.specify/memory/constitution.md"
    local _review_tests_cmd="cd ${_review_wt_path} && pytest tests/ -x --tb=short 2>&1 | tail -30"
    local _review_lint_cmd="cd ${_review_wt_path} && ruff check src/ 2>&1 | tail -20"
    review_prompt=$(cat <<REVIEW_EOF
You are a CODE REVIEWER (QA Architect) performing an artifact review.

## Context
- Constitution: Read $_review_constitution
- Spec: Read $spec_dir/spec.md
- Plan: Read $spec_dir/plan.md  
- Tasks: Read $spec_dir/tasks.md
- Progress: Read $PROJECT_DIR/progress.txt (last 50 lines)
- Current task just completed: $task_desc
- Working directory for all shell commands: $_review_wt_path

## Review Criteria
1. Does the code match the architectural design in plan.md?
2. Does it follow the rules in constitution.md? (naming, typing, headers, etc.)
3. Are there obvious bugs, missing error handling, or broken tests?
4. Run: $_review_tests_cmd
5. Run: $_review_lint_cmd

## Output
If everything looks good: output REVIEW_PASS
If issues found: output REVIEW_FAIL followed by specific feedback on each line.

Be strict. Reject if constitution.md rules are violated.
REVIEW_EOF
    )

    local review_output=""
    local exit_code=0

    set +e
    case "$RALPH_AGENT" in
        claude)
            local flags="-p"
            [[ "$RALPH_YOLO" == "true" ]] && flags="$flags --dangerously-skip-permissions"
            review_output=$(echo "$review_prompt" | "$CLAUDE_CMD" $flags 2>&1)
            exit_code=$?
            ;;
        goose)
            # Goose: pass prompt directly via stdin (like claude -p flag)
            if [[ -n "${RALPH_VLLM_URL:-}" ]]; then
                log_info "Using vLLM for review: $RALPH_VLLM_URL with model: $RALPH_VLLM_MODEL"
                review_output=$(
                    echo "$review_prompt" | \
                    OPENAI_HOST="$RALPH_VLLM_URL" \
                    OPENAI_API_KEY="$CUSTOM_VLLM_API_KEY" \
                    CUSTOM_VLLM_API_KEY="$CUSTOM_VLLM_API_KEY" \
                    GOOSE_MODEL="$RALPH_VLLM_MODEL" \
                    goose run -i - 2>&1
                )
                exit_code=$?
            else
                review_output=$(echo "$review_prompt" | \
                    GOOSE_PROVIDER="${RALPH_REVIEWER_PROVIDER:-$GOOSE_PROVIDER}" \
                    GOOSE_MODEL="${RALPH_REVIEWER_MODEL:-$GOOSE_MODEL}" \
                    goose run -i - 2>&1)
                exit_code=$?
            fi
            ;;
    esac
    set -e

    if [[ $exit_code -ne 0 ]]; then
        log_warn "Review agent failed (exit $exit_code), skipping review"
        return 0
    fi

    # Accept multiple review token formats for compatibility with different reviewers.
    if echo "$review_output" | grep -q -E "REVIEW_PASS|SHIP"; then
        log_ok "Artifact review: PASS"
        return 0
    elif echo "$review_output" | grep -q -E "REVIEW_FAIL|REVISE"; then
        log_warn "Artifact review: FAIL"
        # extract feedback after either REVIEW_FAIL or REVISE marker (if any)
        local feedback
        if echo "$review_output" | grep -q "REVIEW_FAIL"; then
            feedback=$(echo "$review_output" | sed -n '/REVIEW_FAIL/,$p' | tail -n +2)
        elif echo "$review_output" | grep -q "REVISE"; then
            feedback=$(echo "$review_output" | sed -n '/REVISE/,$p' | tail -n +2)
        else
            feedback=""
        fi

        if [ -n "$feedback" ]; then
            echo "$feedback" > "$PROJECT_DIR/.ralph/review-feedback.txt"
        else
            rm -f "$PROJECT_DIR/.ralph/review-feedback.txt" 2>/dev/null || true
        fi

        # Append to progress.txt
        {
            echo ""
            echo "=== REVIEW FAIL at task $task_index ($(date '+%Y-%m-%d %H:%M')) ==="
            echo "$feedback"
        } >> "$PROJECT_DIR/progress.txt"

        return 1
    else
        log_warn "Review: no clear signal, continuing"
        return 0
    fi
}

# ============================================================================
# Agent Execution
# ============================================================================
build_work_prompt() {
    local spec_dir="$1"
    local task_index="$2"
    local task_body="$3"
    local iteration="$4"
    local feedback_file="$PROJECT_DIR/.ralph/review-feedback.txt"

    # Add working directory line for worktree mode (T07)
    # IMPORTANT: the worktree section is a HARD CONSTRAINT, not a hint.
    # Claude CLI resolves the project root via .git, which in a worktree points
    # back to the main repo. Without explicit absolute paths the agent will edit
    # files in the main branch instead of the worktree.
    local worktree_section=""
    local constitution_path="$PROJECT_DIR/.specify/memory/constitution.md"
    local tests_cmd="pytest tests/ -x --tb=short"
    local lint_cmd="ruff check src/"
    local progress_file="$PROJECT_DIR/progress.txt"
    if [[ "$WORKTREE_ENABLED" == "true" ]]; then
        constitution_path="$WORKTREE_PATH/.specify/memory/constitution.md"
        tests_cmd="cd $WORKTREE_PATH && pytest tests/ -x --tb=short"
        lint_cmd="cd $WORKTREE_PATH && ruff check src/"
        progress_file="$PROJECT_DIR/progress.txt"
        worktree_section="
## ⚠ WORKTREE MODE — MANDATORY CONSTRAINTS
- Your working directory is: $WORKTREE_PATH
- **ALL file reads and writes MUST use this absolute path as base.**
- DO NOT edit any files outside $WORKTREE_PATH (the main repo at $PROJECT_DIR is OFF-LIMITS).
- When running shell commands use: cd $WORKTREE_PATH before any relative path.
- git commits must be made from $WORKTREE_PATH (already on branch: $WORKTREE_BRANCH).
"
    fi

    local feedback_section=""
    if [[ -f "$feedback_file" ]]; then
        feedback_section="
## Review Feedback (ADDRESS THIS FIRST)
$(cat "$feedback_file")
"
    fi

    local progress_tail=""
    if [[ -f "$PROJECT_DIR/progress.txt" ]]; then
        progress_tail="
## Recent Progress (last 30 lines)
$(tail -30 "$PROJECT_DIR/progress.txt")
"
    fi

    # Load Speckit Implement Agent instructions for fluid integration
    local speckit_implement_instructions=""
    if [[ -f "$SPECKIT_IMPLEMENT_AGENT" ]]; then
        speckit_implement_instructions="
## Speckit Implement Agent Instructions
$(cat "$SPECKIT_IMPLEMENT_AGENT")
"
    fi

    cat <<PROMPT_EOF
# Ralph Loop — Work Phase (Iteration $iteration)
$worktree_section
You are the SpecKit Implementation running inside a Ralph Loop.
You are 100% autonomous. Your work persists through FILES ONLY.

## CRITICAL: Read these files FIRST
1. $constitution_path (project rules — NON-NEGOTIABLE)
2. $spec_dir/plan.md (architectural design)
3. $spec_dir/spec.md (feature specification)
4. $spec_dir/tasks.md (task list with checkboxes)

## Your Current Task (index $task_index)
\`\`\`
$task_body
\`\`\`
$feedback_section
$progress_tail
$speckit_implement_instructions

## Execution Rules
1. Implement EXACTLY this one task
2. Follow constitution.md rules strictly (typing, headers, naming, etc.)
3. Follow the architecture in plan.md
4. Run tests: $tests_cmd
5. Run lint: $lint_cmd
6. If the task has [VERIFY] tag: run the verification command and report results
7. Commit (from $WORKTREE_PATH) with a descriptive message referencing the task ID

## When Done
- Mark the task as [x] in $spec_dir/tasks.md
- Append your progress to $progress_file:
  \`\`\`
  === $(date '+%Y-%m-%d %H:%M') | Task $task_index ===
  Task: <task ID and description>
  Files changed: <list>
  Status: DONE
  \`\`\`
- Output: TASK_COMPLETE

## If ALL tasks in tasks.md are now [x]:
- Output: ALL_TASKS_COMPLETE

## If you CANNOT complete the task:
- Do NOT output TASK_COMPLETE
- Document what blocked you in $progress_file
- The loop will retry with a fresh context

## FORBIDDEN
- Do not mark tasks [x] unless they are actually verified working
- Do not skip tests or lint checks
- Do not edit files outside $WORKTREE_PATH
- Do not hallucinate dependencies not in plan.md
- Do not ask for human input — you are fully autonomous
PROMPT_EOF
}

run_work_agent() {
    local prompt="$1"
    local log_file="$2"
    local output=""
    local exit_code=0

    set +e
    case "$RALPH_AGENT" in
        claude)
            local flags="-p"
            [[ "$RALPH_YOLO" == "true" ]] && flags="$flags --dangerously-skip-permissions"
            output=$(echo "$prompt" | "$CLAUDE_CMD" $flags 2>&1 | tee "$log_file")
            exit_code=$?
            ;;
        goose)
            # Goose: pass prompt directly via stdin (like claude -p flag)
            # Write to temp file for logging reference and sync to worktree
            mkdir -p "$PROJECT_DIR/.goose/ralph"
            echo "$prompt" > "$PROJECT_DIR/.goose/ralph/task.md"
            
            # Also copy to worktree for goose to find
            if [[ "$WORKTREE_ENABLED" == "true" && -n "$WORKTREE_PATH" ]]; then
                mkdir -p "$WORKTREE_PATH/.goose/ralph"
                cp "$PROJECT_DIR/.goose/ralph/task.md" "$WORKTREE_PATH/.goose/ralph/task.md"
            fi
            
            # If vLLM is configured, set OpenAI environment variables for goose
            # Note: goose uses CUSTOM_VLLM_API_KEY as defined in custom provider config
            if [[ -n "${RALPH_VLLM_URL:-}" ]]; then
                log_info "Using vLLM backend: $RALPH_VLLM_URL with model: $RALPH_VLLM_MODEL"
                output=$(
                    echo "$prompt" | \
                    OPENAI_HOST="$RALPH_VLLM_URL" \
                    OPENAI_API_KEY="$CUSTOM_VLLM_API_KEY" \
                    CUSTOM_VLLM_API_KEY="$CUSTOM_VLLM_API_KEY" \
                    GOOSE_MODEL="$RALPH_VLLM_MODEL" \
                    goose run -i - 2>&1 | tee "$log_file"
                )
                exit_code=$?
            else
                output=$(echo "$prompt" | goose run -i - 2>&1 | tee "$log_file")
                exit_code=$?
            fi
            ;;
        custom)
            if [[ -z "${RALPH_CUSTOM_CMD:-}" ]]; then
                log_error "RALPH_CUSTOM_CMD not set"
                exit 1
            fi
            output=$(echo "$prompt" | eval "$RALPH_CUSTOM_CMD" 2>&1 | tee "$log_file")
            exit_code=$?
            ;;
    esac
    set -e

    echo "$output"
    return $exit_code
}

# ============================================================================
# Progress Logging
# ============================================================================
log_progress() {
    local task_index="$1"
    local task_desc="$2"
    local status="$3"
    local iteration="$4"

    {
        echo ""
        echo "=== $(date '+%Y-%m-%d %H:%M') | Iteration $iteration | Task $task_index ==="
        echo "Task: $task_desc"
        echo "Status: $status"
    } >> "$PROJECT_DIR/progress.txt"
}

# ============================================================================
# Preflight Checks (T02)
# ============================================================================
run_preflight_checks() {
    # Skip guard
    if [[ "$SKIP_PREFLIGHT" == "true" ]]; then
        log_warn "[WARN] Preflight checks omitidos"
        return 0
    fi

    # Check 1: worktree list trust (also detects dirty indirectly)
    local wt_out
    wt_out=$(git -C "$PROJECT_DIR" worktree list --porcelain 2>&1)
    if [[ $? -ne 0 ]]; then
        log_error "git worktree list falló (posible safe.directory error)"
        log_info  "Fix: git config --global --add safe.directory $PROJECT_DIR"
        exit 1
    fi

    # Check 2: dirty working tree
    local dirty
    dirty=$(git -C "$PROJECT_DIR" status --porcelain 2>&1)
    if [[ -n "$dirty" ]]; then
        log_error "Hay archivos sin commit en el repo principal:"
        echo "$dirty" | head -10 >&2
        log_info  "Fix: git add -A && git commit -m 'wip: save work before ralph'"
        exit 1
    fi

    # Check 3: in-progress git operations
    for sentinel in MERGE_HEAD REBASE_HEAD CHERRY_PICK_HEAD; do
        if [[ -f "$PROJECT_DIR/.git/$sentinel" ]]; then
            local op="${sentinel//_HEAD/}"
            log_error "${op} en curso detectado (.git/${sentinel})"
            log_info  "Fix: git ${op,,} --abort"
            exit 1
        fi
    done

    log_ok "Preflight checks: OK"
}

# ============================================================================
# Test concurrency guard
# Ensure the loop doesn't launch test-heavy runs when other pytest processes
# are already consuming RAM/swap. This provides a soft guard and a lockfile
# to serialize test executions initiated by the loop.
# ============================================================================

count_pytest_processes() {
    # Count processes that look like pytest runs. Use a forgiving matcher.
    local cnt
    cnt=$(pgrep -fc pytest || true)
    echo "${cnt:-0}"
}

wait_for_test_slot() {
    local max=${RALPH_TEST_CONCURRENCY:-1}
    local interval=5

    while true; do
        local running
        running=$(count_pytest_processes)
        if [[ -z "$running" ]]; then
            running=0
        fi
        if (( running < max )); then
            return 0
        fi
        log_info "Waiting for test slot: $running running, max $max"
        sleep $interval
    done
}

# ============================================================================
# .gitignore Check (T03)
# ============================================================================
check_gitignore_worktrees() {
    local gitignore="$PROJECT_DIR/.gitignore"
    if ! grep -qxF '.worktrees/' "$gitignore" 2>/dev/null; then
        echo '.worktrees/' >> "$gitignore"
        log_info "Añadido .worktrees/ a .gitignore"
    fi
}

# ============================================================================
# Worktree Creation Functions (T04)
# ============================================================================

# Get the git dir for a worktree (resolves .git file)
get_worktree_git_dir() {
    local wt_path="$1"
    local git_file="$wt_path/.git"
    if [[ -f "$git_file" ]]; then
        sed 's/^gitdir: //' "$git_file"
    else
        echo "$wt_path/.git"
    fi
}

# Configure sparse-checkout to exclude specs/ (FR-008, FR-009, FR-010)
configure_sparse_checkout() {
    local wt_path="$1"
    local git_dir
    git_dir=$(get_worktree_git_dir "$wt_path")

    mkdir -p "$git_dir/info"
    git -C "$wt_path" config core.sparseCheckout true
    git -C "$wt_path" config core.sparseCheckoutCone false
    printf '/*\n!/specs/\n!/specs/**\n' > "$git_dir/info/sparse-checkout"
    git -C "$wt_path" read-tree -mu HEAD

    # Add specs/ to exclude as second layer of protection
    if ! grep -qxF 'specs/' "$git_dir/info/exclude" 2>/dev/null; then
        echo 'specs/' >> "$git_dir/info/exclude"
    fi

    # Remove specs/ directory if it still exists on disk (FR-010)
    if [[ -d "$wt_path/specs" ]]; then
        rm -rf "$wt_path/specs"
    fi
}

# Generate a unique worktree name (FR-001, FR-002)
generate_worktree_name() {
    local slug="$1"
    local candidate="ralph/${slug}-$(date '+%Y%m%d_%H%M%S')"

    # If branch already exists, add random suffix for collision avoidance
    if [[ -n "$(git -C "$PROJECT_DIR" branch --list "$candidate" 2>/dev/null)" ]]; then
        candidate="${candidate}-$(printf '%04d' $((RANDOM % 10000)))"
    fi

    echo "$candidate"
}

# Initialize a new worktree (FR-001, FR-002, FR-007)
init_worktree() {
    local spec_dir="$1"
    local slug
    slug=$(basename "$spec_dir")

    WORKTREE_BRANCH=$(generate_worktree_name "$slug")
    WORKTREE_PATH="$PROJECT_DIR/.worktrees/$(echo "$WORKTREE_BRANCH" | sed 's|ralph/||')"
    BASE_BRANCH=$(git -C "$PROJECT_DIR" branch --show-current)
    WORKTREE_CREATED_AT=$(date --iso-8601=seconds)

    mkdir -p "$PROJECT_DIR/.worktrees"

    log_info "Creating worktree: $WORKTREE_PATH"
    git -C "$PROJECT_DIR" worktree add "$WORKTREE_PATH" -b "$WORKTREE_BRANCH" \
        || { log_error "git worktree add falló"; exit 1; }

    configure_sparse_checkout "$WORKTREE_PATH"

    # Write worktree fields to state.json
    python3 "$MERGE_SCRIPT" "$STATE_FILE" \
        --set "worktreePath=$WORKTREE_PATH" \
        --set "worktreeBranch=$WORKTREE_BRANCH" \
        --set "worktreeCreatedAt=$WORKTREE_CREATED_AT" \
        --set "baseBranch=$BASE_BRANCH"

    log_ok "Worktree created: $WORKTREE_PATH (branch: $WORKTREE_BRANCH)"
}

# ============================================================================
# ensure_sparse_checkout per iteration (T05)
# ============================================================================
ensure_sparse_checkout() {
    local wt_path="$1"
    local git_dir
    git_dir=$(get_worktree_git_dir "$wt_path") || return 0
    local sc_file="$git_dir/info/sparse-checkout"
    local expected
    expected="$(printf '/*\n!/specs/\n!/specs/**\n')"
    local actual
    actual="$(cat "$sc_file" 2>/dev/null || true)"
    if [[ "$actual" != "$expected" ]]; then
        configure_sparse_checkout "$wt_path"
    fi
}

# ============================================================================
# detect_and_recreate_worktree (T06)
# Edge case: directory deleted during execution
# ============================================================================
detect_and_recreate_worktree() {
    if [[ -n "$WORKTREE_PATH" && ! -d "$WORKTREE_PATH" ]]; then
        log_warn "[WARN] Worktree directory missing; recreating: $WORKTREE_PATH"
        git -C "$PROJECT_DIR" worktree prune
        git -C "$PROJECT_DIR" worktree add "$WORKTREE_PATH" "$WORKTREE_BRANCH" \
            || { log_error "No se pudo recrear el worktree"; exit 1; }
        configure_sparse_checkout "$WORKTREE_PATH"
        log_ok "Worktree recreado: $WORKTREE_PATH"
    fi
}

# ============================================================================
# print_merge_instructions (T09)
# Print merge instructions at loop exit
# ============================================================================
print_merge_instructions() {
    [[ "$WORKTREE_ENABLED" != "true" || -z "$WORKTREE_BRANCH" ]] && return 0
    local slug
    slug=$(basename "$WORKTREE_PATH")
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Worktree:  $WORKTREE_PATH"
    log_info "Branch:    $WORKTREE_BRANCH"
    log_info "To merge (squash — recommended):"
    log_info "  git merge --squash $WORKTREE_BRANCH && git commit -m \"feat($slug): <description>\""
    log_info "Or (preserve full history):"
    log_info "  git merge $WORKTREE_BRANCH"
    log_info "To clean up after merge:"
    log_info "  .ralph/ralph-loop.sh --clean $slug"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ============================================================================
# --clean subcommand (T10)
# ============================================================================

# Detect base branch (main or master)
detect_base_branch() {
    local ref
    ref=$(git -C "$PROJECT_DIR" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
    if [[ -n "$ref" ]]; then
        echo "${ref##*/}"
        return 0
    fi
    for b in main master; do
        if git -C "$PROJECT_DIR" branch --list "$b" | grep -q "$b"; then
            echo "$b"
            return 0
        fi
    done
    return 1
}

# Run clean for a given slug
run_clean() {
    local slug="$1"

    # If no slug provided, read from state.json
    if [[ -z "$slug" ]]; then
        if [[ -f "$STATE_FILE" ]]; then
            slug=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['name'])" "$STATE_FILE")
        else
            log_error "No slug provided and no state.json found"
            exit 1
        fi
    fi

    # Detect base branch
    local base_branch
    base_branch=$(detect_base_branch) || {
        log_error "Could not detect base branch"
        log_info "Hint: Use --base-branch <branch> to specify"
        exit 1
    }

    log_info "Cleaning worktrees for slug: $slug (base: $base_branch)"

    # Find worktrees for this slug
    local wt_pattern="$PROJECT_DIR/.worktrees/${slug}-*"
    local wt_list
    wt_list=$(ls -d $wt_pattern 2>/dev/null || true)

    if [[ -z "$wt_list" ]]; then
        log_info "No worktrees found for slug: $slug"
        git -C "$PROJECT_DIR" worktree prune
        return 0
    fi

    local merged_count=0
    local unmerged_count=0

    for wt_path in $wt_list; do
        local wt_branch
        wt_branch=$(git -C "$PROJECT_DIR" worktree list --porcelain | awk "/^worktree.*$(basename "$wt_path")/{f=1} f && /^branch/{print \$2; f=0}")

        if [[ -z "$wt_branch" ]]; then
            log_warn "Could not determine branch for worktree: $wt_path"
            continue
        fi

        # Check if merged
        if git -C "$PROJECT_DIR" branch --merged "$base_branch" | grep -q "^[* ][[:space:]]*$wt_branch$"; then
            log_info "[MERGED] $wt_path ($wt_branch)"
            log_info "  Removing worktree and branch..."
            git -C "$PROJECT_DIR" worktree remove --force "$wt_path" 2>/dev/null || true
            git -C "$PROJECT_DIR" branch -d "$wt_branch" 2>/dev/null || true
            merged_count=$((merged_count + 1))
        else
            log_warn "[NOT MERGED] $wt_path ($wt_branch)"
            unmerged_count=$((unmerged_count + 1))
            read -rp "Delete unmerged worktree $wt_path? [y/N] " confirm
            if [[ "$confirm" == [yY] ]]; then
                git -C "$PROJECT_DIR" worktree remove --force "$wt_path" 2>/dev/null || true
                git -C "$PROJECT_DIR" branch -d "$wt_branch" 2>/dev/null || true
            fi
        fi
    done

    git -C "$PROJECT_DIR" worktree prune

    log_ok "Clean complete: $merged_count merged worktrees removed, $unmerged_count not merged"
}

# ============================================================================
# Main Loop
# ============================================================================
main() {
    parse_args "$@"

    # Trap EXIT for cleanup
    trap 'rm -f "$PROJECT_DIR/.ralph/state.json.tmp"' EXIT

    # Convert relative SPEC_DIR to absolute path
    if [[ -n "$SPEC_DIR" && "$SPEC_DIR" != /* ]]; then
        local old_spec_dir="$SPEC_DIR"
        SPEC_DIR="$PROJECT_DIR/$SPEC_DIR"
        log_info "Converted relative path '$old_spec_dir' to absolute '$SPEC_DIR'"
    fi

    cd "$PROJECT_DIR"

    # Handle --clean subcommand (T10)
    if [[ "${CLEAN_MODE:-false}" == "true" ]]; then
        run_clean "${CLEAN_SLUG:-}"
        exit 0
    fi

    # Validate agent
    case "$RALPH_AGENT" in
        claude)
            if ! command -v "$CLAUDE_CMD" &>/dev/null; then
                log_error "Claude CLI not found: $CLAUDE_CMD"
                exit 1
            fi ;;
        goose)
            if ! command -v goose &>/dev/null; then
                log_error "Goose CLI not found"
                exit 1
            fi ;;
        custom)
            if [[ -z "${RALPH_CUSTOM_CMD:-}" ]]; then
                log_error "RALPH_CUSTOM_CMD not set for custom agent"
                exit 1
            fi ;;
        *)
            log_error "Unknown agent: $RALPH_AGENT (supported: claude, goose, custom)"
            exit 1 ;;
    esac

    # Initialize or resume state
    if [[ "$RESUME_MODE" == "true" ]]; then
        if [[ ! -f "$STATE_FILE" ]]; then
            log_error "No state file found at $STATE_FILE — cannot resume"
            exit 1
        fi
        log_info "Resuming from existing state"

        # Restore worktree fields from state.json (T11)
        if [[ "$WORKTREE_ENABLED" == "true" ]]; then
            WORKTREE_PATH=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('worktreePath',''))" "$STATE_FILE")
            WORKTREE_BRANCH=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('worktreeBranch',''))" "$STATE_FILE")
            BASE_BRANCH=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('baseBranch',''))" "$STATE_FILE")
        fi
    else
        if [[ -z "$SPEC_DIR" ]]; then
            log_error "Spec directory required. Usage: .ralph/ralph-loop.sh specs/001-feature"
            show_help
            exit 1
        fi
        init_state "$SPEC_DIR"

        # Worktree setup for new execution (T11)
        if [[ "$WORKTREE_ENABLED" == "true" ]]; then
            log_info "Setting up worktree mode..."
            check_gitignore_worktrees
            log_info "Running preflight checks..."
            run_preflight_checks
            log_info "Creating worktree..."
            init_worktree "$SPEC_DIR"
        else
            log_info "Running in legacy mode (no worktree)"
        fi
    fi

    log_info "Worktree setup complete. Proceeding to main loop..."

    # Read initial state
    local spec_dir tasks_file
    spec_dir=$(read_state "basePath")
    tasks_file="$spec_dir/tasks.md"
    local feature_name
    feature_name=$(read_state "name")

    # Create log dir
    local log_dir="$PROJECT_DIR/logs"
    mkdir -p "$log_dir"

    # Touch progress.txt
    touch "$PROJECT_DIR/progress.txt"

    # Session log
    local session_log="$log_dir/ralph_session_$(date '+%Y%m%d_%H%M%S').log"

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}      RALPH LOOP — SpecKit Integrated Edition               ${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BLUE}Feature:${NC}      $feature_name"
    echo -e "  ${BLUE}Spec dir:${NC}     $spec_dir"
    echo -e "  ${BLUE}Agent:${NC}        $RALPH_AGENT"
    # Show vLLM info if configured
    if [[ -n "${RALPH_VLLM_URL:-}" ]]; then
        echo -e "  ${BLUE}vLLM URL:${NC}    $RALPH_VLLM_URL"
        echo -e "  ${BLUE}vLLM Model:${NC}  $RALPH_VLLM_MODEL"
    fi
    echo -e "  ${BLUE}Max iter:${NC}     $RALPH_MAX_ITER"
    echo -e "  ${BLUE}Review every:${NC} $RALPH_REVIEW_EVERY tasks"
    echo -e "  ${BLUE}Max retries:${NC}  $RALPH_MAX_RETRIES per task"
    echo -e "  ${BLUE}YOLO:${NC}         $RALPH_YOLO"
    echo -e "  ${BLUE}Log:${NC}          $session_log"

    # Add worktree info to banner if enabled (T11)
    if [[ "$WORKTREE_ENABLED" == "true" ]]; then
        echo -e "  ${BLUE}Worktree:${NC}    $WORKTREE_PATH"
        echo -e "  ${BLUE}Branch:${NC}      $WORKTREE_BRANCH"
    fi

    echo ""
    echo -e "  $(get_task_counts "$tasks_file")"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""

    local global_iter=0
    local consecutive_failures=0

    while true; do
        global_iter=$((global_iter + 1))

        # Safety cap
        if (( global_iter > RALPH_MAX_ITER )); then
            log_warn "Global iteration cap reached ($RALPH_MAX_ITER)"
            break
        fi

        # Worktree per-iteration checks (T05, T06)
        if [[ "$WORKTREE_ENABLED" == "true" ]]; then
            ensure_sparse_checkout "$WORKTREE_PATH"
            detect_and_recreate_worktree
        fi

        # Re-read task counts each iteration (tasks.md may have changed)
        local counts_json
        # Always recalculate from tasks.md to get fresh counts
        counts_json=$(python3 "$COUNT_SCRIPT" "$tasks_file")
        local total completed incomplete next_idx percent
        total=$(echo "$counts_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])")
        completed=$(echo "$counts_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['completed'])")
        incomplete=$(echo "$counts_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['incomplete'])")
        next_idx=$(echo "$counts_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['next_index'])")
        percent=$(echo "$counts_json" | python3 -c "import json,sys; print(json.load(sys.stdin)['percent'])")

        # All done?
        if (( incomplete == 0 )); then
            echo ""
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}  ✓ ALL TASKS COMPLETE ($completed/$total) in $global_iter iterations${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            update_state --set "phase=done"
            log_progress "$next_idx" "ALL COMPLETE" "ALL_TASKS_COMPLETE" "$global_iter"
            print_merge_instructions
            exit 0
        fi

        # Update state
        update_state \
            --set "globalIteration=$global_iter" \
            --set "taskIndex=$next_idx" \
            --set "totalTasks=$total"

        # Get current task
        local task_body
        task_body=$(get_task_at_index "$tasks_file" "$next_idx" 2>/dev/null || echo "UNKNOWN TASK")
        local task_id
        task_id=$(echo "$task_body" | head -1 | grep -oP '[TV]\d+' | head -1 || echo "T???")
        local task_desc
        task_desc=$(echo "$task_body" | head -1 | sed 's/^- \[.\] //')

        echo ""
        echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
        echo -e "${PURPLE}  Iteration $global_iter | Task $next_idx/$total ($percent% done) | $task_id${NC}"
        echo -e "${PURPLE}════════════════════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}$task_desc${NC}"
        echo ""

        # Check per-task retry limit
        local task_iter
        task_iter=$(read_state "taskIteration")
        if (( task_iter > RALPH_MAX_RETRIES )); then
            log_error "Task $task_id exceeded max retries ($RALPH_MAX_RETRIES)"
            log_error "Skipping to next task (marking as blocked)"
            log_progress "$next_idx" "$task_desc" "BLOCKED (max retries)" "$global_iter"
            # Force-mark as done to unblock (with BLOCKED note)
            mark_task_done "$tasks_file" "$next_idx"
            update_state --set "taskIteration=1"
            continue
        fi

        # Build prompt
        local work_prompt
        work_prompt=$(build_work_prompt "$spec_dir" "$next_idx" "$task_body" "$global_iter")

        # Run work agent
        local iter_log="$log_dir/ralph_iter_${global_iter}_$(date '+%Y%m%d_%H%M%S').log"
        echo -e "${YELLOW}▶ WORK PHASE${NC}"

        local agent_output=""
        local agent_exit=0

        set +e
        # cd to worktree before running agent (T07)
        [[ "$WORKTREE_ENABLED" == "true" ]] && cd "$WORKTREE_PATH"

        # --- Capture pre-agent git state for diagnostics ---
        local pre_wt_head pre_wt_status pre_wt_tasks_sha pre_repo_tasks_sha rel_spec worktree_tasks
        pre_wt_head=""
        pre_wt_status=""
        pre_wt_tasks_sha=""
        pre_repo_tasks_sha=""
        worktree_tasks=""
        rel_spec=""
        if [[ "$WORKTREE_ENABLED" == "true" && -n "$WORKTREE_PATH" ]]; then
            # derive relative path of spec_dir inside project (strip PROJECT_DIR prefix)
            rel_spec="${spec_dir#${PROJECT_DIR}/}"
            worktree_tasks="$WORKTREE_PATH/$rel_spec/tasks.md"
            pre_wt_head=$(git -C "$WORKTREE_PATH" rev-parse --verify HEAD 2>/dev/null || echo "")
            pre_wt_status=$(git -C "$WORKTREE_PATH" status --porcelain 2>/dev/null || echo "")
            if [[ -f "$worktree_tasks" ]]; then
                pre_wt_tasks_sha=$(compute_sha1 "$worktree_tasks")
            fi
        fi

        pre_repo_tasks_sha=$(compute_sha1 "$tasks_file")

        # Wait for a test slot to avoid saturating RAM/swap with parallel pytest runs
        wait_for_test_slot

        # Purge any orphaned pytest processes left by previous agents before
        # launching a new agent. The agent may have launched pytest in background
        # (isBackground=true) without waiting; those become orphans consuming RAM.
        local orphans_before
        orphans_before=$(pgrep -fc pytest 2>/dev/null || true)
        if (( ${orphans_before:-0} > 0 )); then
            log_warn "Purging $orphans_before orphaned pytest process(es) before agent start"
            python3 "$RALPH_DIR/kill_pytest_orphans.py" --timeout 5 || true
        fi

        # Log memory before agent execution
        log_memory "before_agent"

        # Acquire test lock to serialize test-heavy agent runs initiated by this loop
        if (( RALPH_TEST_CONCURRENCY > 0 )); then
            exec 9>/tmp/ralph-test.lock
            flock -x 9
            agent_output=$(run_work_agent "$work_prompt" "$iter_log")
            agent_exit=$?
            flock -u 9
            exec 9>&-
        else
            agent_output=$(run_work_agent "$work_prompt" "$iter_log")
            agent_exit=$?
        fi

        # Log memory after agent execution
        log_memory "after_agent"

        # Purge any orphaned pytest processes the agent may have left running in
        # background. Without this, isBackground=true pytest calls accumulate.
        local orphans_after
        orphans_after=$(pgrep -fc pytest 2>/dev/null || true)
        if (( ${orphans_after:-0} > 0 )); then
            log_warn "Purging $orphans_after orphaned pytest process(es) after agent exit"
            python3 "$RALPH_DIR/kill_pytest_orphans.py" --timeout 5 || true
        fi

        # cd back to project dir after agent
        [[ "$WORKTREE_ENABLED" == "true" ]] && cd "$PROJECT_DIR"

        # --- Capture post-agent git state for diagnostics ---
        local post_wt_head post_wt_status post_wt_tasks_sha post_repo_tasks_sha
        post_wt_head=""
        post_wt_status=""
        post_wt_tasks_sha=""
        post_repo_tasks_sha=""
        if [[ "$WORKTREE_ENABLED" == "true" && -n "$WORKTREE_PATH" ]]; then
            post_wt_head=$(git -C "$WORKTREE_PATH" rev-parse --verify HEAD 2>/dev/null || echo "")
            post_wt_status=$(git -C "$WORKTREE_PATH" status --porcelain 2>/dev/null || echo "")
            if [[ -f "$worktree_tasks" ]]; then
                post_wt_tasks_sha=$(compute_sha1 "$worktree_tasks")
            fi
        fi
        post_repo_tasks_sha=$(compute_sha1 "$tasks_file")

        # Summarize commit activity (concise)
        if [[ "$WORKTREE_ENABLED" == "true" ]]; then
            if [[ -n "$pre_wt_head" && -n "$post_wt_head" && "$pre_wt_head" != "$post_wt_head" ]]; then
                log_info "Worktree branch HEAD changed: $pre_wt_head -> $post_wt_head"
                git -C "$WORKTREE_PATH" --no-pager log --oneline "$pre_wt_head..$post_wt_head" | sed 's/^/  /' || true
            else
                log_info "No new commits in worktree branch ($WORKTREE_BRANCH)"
            fi
            if [[ -n "$pre_wt_status" || -n "$post_wt_status" ]]; then
                log_info "Worktree status (pre/post):"
                echo "PRE: $pre_wt_status"
                echo "POST: $post_wt_status"
            fi
            if [[ -n "$pre_wt_tasks_sha" || -n "$post_wt_tasks_sha" ]]; then
                if [[ "$pre_wt_tasks_sha" != "$post_wt_tasks_sha" ]]; then
                    log_info "Worktree tasks.md changed: $worktree_tasks"
                fi
            fi
        fi
        if [[ "$pre_repo_tasks_sha" != "$post_repo_tasks_sha" ]]; then
            log_info "Repo canonical tasks.md changed: $tasks_file"
            git -C "$PROJECT_DIR" --no-pager log --pretty=oneline -n 5 -- "$tasks_file" | sed 's/^/  /' || true
        fi

        set -e

        if [[ $agent_exit -ne 0 ]]; then
            log_error "Agent failed (exit $agent_exit)"
            consecutive_failures=$((consecutive_failures + 1))
            update_state --set "taskIteration=$((task_iter + 1))"
            log_progress "$next_idx" "$task_desc" "AGENT_ERROR (exit $agent_exit)" "$global_iter"

            if (( consecutive_failures >= 3 )); then
                log_warn "3 consecutive failures — check logs at $log_dir"
                consecutive_failures=0
            fi
            sleep 2
            continue
        fi

        # ──────────────────────────────────────────────────────────────
        # THREE-LAYER VERIFICATION
        # ──────────────────────────────────────────────────────────────

        echo ""
        echo -e "${YELLOW}▶ VERIFICATION PHASE${NC}"

        # Layer 1: Contradiction detection
        local contradiction_msg=""
        if ! contradiction_msg=$(check_contradictions "$agent_output"); then
            log_warn "Layer 1 FAIL: $contradiction_msg"
            update_state --set "taskIteration=$((task_iter + 1))"
            log_progress "$next_idx" "$task_desc" "CONTRADICTION_DETECTED" "$global_iter"
            consecutive_failures=$((consecutive_failures + 1))
            sleep 2
            continue
        fi
        log_ok "Layer 1: No contradictions"

        # Layer 2: Completion signal
        if check_all_complete_signal "$agent_output"; then
            log_ok "Layer 2: ALL_TASKS_COMPLETE signal detected"
            # Verify by re-counting
            local verify_counts
            verify_counts=$(python3 "$COUNT_SCRIPT" "$tasks_file")
            local verify_incomplete
            verify_incomplete=$(echo "$verify_counts" | python3 -c "import json,sys; print(json.load(sys.stdin)['incomplete'])")
            if (( verify_incomplete == 0 )); then
                echo ""
                echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "${GREEN}  ✓ SHIPPED — All tasks complete in $global_iter iterations${NC}"
                echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                update_state --set "phase=done"
                log_progress "$next_idx" "$task_desc" "ALL_TASKS_COMPLETE" "$global_iter"
                exit 0
            else
                log_warn "Agent claims ALL_TASKS_COMPLETE but $verify_incomplete tasks still incomplete"
                log_info "DIAGNOSTIC: mismatch at Iteration $global_iter TaskIndex $next_idx (task $task_id)"
                log_info "Spec dir (state basePath): $spec_dir"
                log_info "Repo tasks path: $tasks_file"
                log_info "Repo tasks SHA1 (pre/post): ${pre_repo_tasks_sha:-} / ${post_repo_tasks_sha:-}"
                if [[ -n "$worktree_tasks" ]]; then
                    log_info "Worktree tasks path: $worktree_tasks"
                    log_info "Worktree tasks SHA1 (pre/post): ${pre_wt_tasks_sha:-} / ${post_wt_tasks_sha:-}"
                else
                    log_info "No worktree tasks file path computed (rel_spec='$rel_spec')"
                fi
                log_info "Worktree HEAD (pre/post): ${pre_wt_head:-} / ${post_wt_head:-}"
                if [[ -n "$pre_wt_head" && -n "$post_wt_head" && "$pre_wt_head" != "$post_wt_head" ]]; then
                    log_info "Recent commits in worktree:"
                    git -C "$WORKTREE_PATH" --no-pager log --oneline "$pre_wt_head..$post_wt_head" | sed 's/^/  /' || true
                fi
                log_info "Last commits touching repo tasks.md:"
                git -C "$PROJECT_DIR" --no-pager log --pretty=oneline -n 5 -- "$tasks_file" | sed 's/^/  /' || true
                if [[ -f "$tasks_file" && -f "$worktree_tasks" ]]; then
                    log_info "Short diff (repo vs worktree tasks.md):"
                    diff -u "$tasks_file" "$worktree_tasks" | sed -n '1,200p' | sed 's/^/  /' || true
                fi
                log_warn "Continuing loop to handle remaining tasks"
            fi
        elif check_completion_signal "$agent_output"; then
            log_ok "Layer 2: TASK_COMPLETE signal detected"

            # Verify the task was actually marked [x]
            local verify_counts2
            verify_counts2=$(python3 "$COUNT_SCRIPT" "$tasks_file")
            local new_completed
            new_completed=$(echo "$verify_counts2" | python3 -c "import json,sys; print(json.load(sys.stdin)['completed'])")

            if (( new_completed > completed )); then
                log_ok "Task verified: checkbox updated in tasks.md"
            else
                log_warn "Signal found but task not marked [x] — forcing mark"
                mark_task_done "$tasks_file" "$next_idx"
            fi

            # Reset per-task counter
            update_state --set "taskIteration=1"
            consecutive_failures=0

            # Remove review feedback if it was addressed
            rm -f "$PROJECT_DIR/.ralph/review-feedback.txt"

            log_progress "$next_idx" "$task_desc" "DONE" "$global_iter"

            # Layer 3: Periodic artifact review
            local last_review review_interval
            last_review=$(read_state "lastReviewAt" 2>/dev/null || echo "0")
            review_interval=$(read_state "reviewInterval" 2>/dev/null || echo "$RALPH_REVIEW_EVERY")

            if should_run_review "$next_idx" "$total" "${last_review:-0}" "${review_interval:-$RALPH_REVIEW_EVERY}"; then
                if ! run_artifact_review "$spec_dir" "$task_desc" "$next_idx"; then
                    log_warn "Artifact review failed — next iteration will address feedback"
                fi
                update_state --set "lastReviewAt=$next_idx"
            fi
        else
            log_warn "Layer 2: No completion signal found"
            update_state --set "taskIteration=$((task_iter + 1))"
            log_progress "$next_idx" "$task_desc" "NO_SIGNAL (retry $((task_iter + 1)))" "$global_iter"
            consecutive_failures=$((consecutive_failures + 1))

            if (( consecutive_failures >= 3 )); then
                log_warn "3 consecutive no-signal iterations — agent may be stuck"
                log_warn "Check logs: $log_dir"
                consecutive_failures=0
            fi
        fi

        # Push if there are unpushed commits (T08 - RALPH_PUSH conditional)
        if [[ "${RALPH_PUSH:-false}" == "true" ]]; then
            if git -C "$PROJECT_DIR" remote get-url origin &>/dev/null; then
                local push_branch
                if [[ "$WORKTREE_ENABLED" == "true" ]]; then
                    push_branch="$WORKTREE_BRANCH"
                else
                    push_branch=$(git -C "$PROJECT_DIR" branch --show-current)
                fi
                if [[ "$PUSH_TRACKING_SET" != "true" ]]; then
                    git -C "$PROJECT_DIR" push -u origin "$push_branch" 2>/dev/null || true
                    PUSH_TRACKING_SET=true
                else
                    git -C "$PROJECT_DIR" push 2>/dev/null || true
                fi
            fi
        fi

        # Brief pause
        sleep 2
    done

    # Print merge instructions at loop exit (T09)
    print_merge_instructions

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Ralph Loop finished ($global_iter iterations)${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    local final_counts
    final_counts=$(get_task_counts "$tasks_file")
    echo -e "  $final_counts"
}

main "$@"
