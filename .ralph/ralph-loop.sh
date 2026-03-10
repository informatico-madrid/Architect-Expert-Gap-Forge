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

COUNT_SCRIPT="$RALPH_DIR/scripts/count_tasks.py"
MERGE_SCRIPT="$RALPH_DIR/scripts/merge_state.py"
CONSTITUTION="$PROJECT_DIR/.specify/memory/constitution.md"

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
    "not possible"
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
    if echo "$output" | grep -qE "TASK_COMPLETE|<promise>DONE</promise>"; then
        return 0
    fi
    return 1
}

check_all_complete_signal() {
    local output="$1"
    if echo "$output" | grep -qE "ALL_TASKS_COMPLETE|<promise>ALL_DONE</promise>"; then
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
    review_prompt=$(cat <<REVIEW_EOF
You are a CODE REVIEWER (QA Architect) performing an artifact review.

## Context
- Constitution: Read .specify/memory/constitution.md
- Spec: Read $spec_dir/spec.md
- Plan: Read $spec_dir/plan.md  
- Tasks: Read $spec_dir/tasks.md
- Progress: Read $PROJECT_DIR/progress.txt (last 50 lines)
- Current task just completed: $task_desc

## Review Criteria
1. Does the code match the architectural design in plan.md?
2. Does it follow the rules in constitution.md? (naming, typing, headers, etc.)
3. Are there obvious bugs, missing error handling, or broken tests?
4. Run: pytest tests/ -x --tb=short 2>&1 | tail -30
5. Run: ruff check src/ 2>&1 | tail -20

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
            review_output=$(GOOSE_PROVIDER="${RALPH_REVIEWER_PROVIDER:-$GOOSE_PROVIDER}" \
                          GOOSE_MODEL="${RALPH_REVIEWER_MODEL:-$GOOSE_MODEL}" \
                          goose run --recipe "$RALPH_DIR/recipes/ralph-review.yaml" 2>&1)
            exit_code=$?
            ;;
    esac
    set -e

    if [[ $exit_code -ne 0 ]]; then
        log_warn "Review agent failed (exit $exit_code), skipping review"
        return 0
    fi

    if echo "$review_output" | grep -q "REVIEW_PASS"; then
        log_ok "Artifact review: PASS"
        return 0
    elif echo "$review_output" | grep -q "REVIEW_FAIL"; then
        log_warn "Artifact review: FAIL"
        # extract feedback
        local feedback
        feedback=$(echo "$review_output" | sed -n '/REVIEW_FAIL/,$p' | tail -n +2)
        echo "$feedback" > "$PROJECT_DIR/.ralph/review-feedback.txt"

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

    cat <<PROMPT_EOF
# Ralph Loop — Work Phase (Iteration $iteration)

You are the SpecKit Implementation Agent running inside a Ralph Loop.
You are 100% autonomous. Your work persists through FILES ONLY.

## CRITICAL: Read these files FIRST
1. .specify/memory/constitution.md (project rules — NON-NEGOTIABLE)
2. $spec_dir/plan.md (architectural design)
3. $spec_dir/spec.md (feature specification)
4. $spec_dir/tasks.md (task list with checkboxes)

## Your Current Task (index $task_index)
\`\`\`
$task_body
\`\`\`
$feedback_section
$progress_tail

## Execution Rules
1. Implement EXACTLY this one task
2. Follow constitution.md rules strictly (typing, headers, naming, etc.)
3. Follow the architecture in plan.md
4. Run tests: pytest tests/ -x --tb=short
5. Run lint: ruff check src/
6. If the task has [VERIFY] tag: run the verification command and report results
7. Commit with a descriptive message referencing the task ID

## When Done
- Mark the task as [x] in $spec_dir/tasks.md
- Append your progress to progress.txt:
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
- Document what blocked you in progress.txt
- The loop will retry with a fresh context

## FORBIDDEN
- Do not mark tasks [x] unless they are actually verified working
- Do not skip tests or lint checks  
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
            # Write prompt to task.md for goose recipe
            echo "$prompt" > "$PROJECT_DIR/.goose/ralph/task.md"
            output=$(goose run --recipe "$RALPH_DIR/recipes/ralph-work.yaml" 2>&1 | tee "$log_file")
            exit_code=$?
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
# Main Loop
# ============================================================================
main() {
    parse_args "$@"
    cd "$PROJECT_DIR"

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
    else
        if [[ -z "$SPEC_DIR" ]]; then
            log_error "Spec directory required. Usage: .ralph/ralph-loop.sh specs/001-feature"
            show_help
            exit 1
        fi
        init_state "$SPEC_DIR"
    fi

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
    echo -e "  ${BLUE}Max iter:${NC}     $RALPH_MAX_ITER"
    echo -e "  ${BLUE}Review every:${NC} $RALPH_REVIEW_EVERY tasks"
    echo -e "  ${BLUE}Max retries:${NC}  $RALPH_MAX_RETRIES per task"
    echo -e "  ${BLUE}YOLO:${NC}         $RALPH_YOLO"
    echo -e "  ${BLUE}Log:${NC}          $session_log"
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

        # Re-read task counts each iteration (tasks.md may have changed)
        local counts_json
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
        agent_output=$(run_work_agent "$work_prompt" "$iter_log")
        agent_exit=$?
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

        # Push if there are unpushed commits
        local current_branch
        current_branch=$(git branch --show-current 2>/dev/null || echo "main")
        git push origin "$current_branch" 2>/dev/null || true

        # Brief pause
        sleep 2
    done

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Ralph Loop finished ($global_iter iterations)${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    local final_counts
    final_counts=$(get_task_counts "$tasks_file")
    echo -e "  $final_counts"
}

main "$@"
