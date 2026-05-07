---
spec: module-discovery-strategy-auto
phase: research
created: 2026-04-26T00:00:00Z
---

# Research: DSPy 3.2.0 API Reference

## Executive Summary

DSPy 3.2.0 uses Pydantic-based `Signature` classes where `InputField`/`OutputField` delegate to `pydantic.Field`. Typed outputs (`int`, `float`, `list[str]`, `Optional[...]`, `dict`) are supported natively and the model must produce parsable output. `ChainOfThought` is a `Predict` wrapper that prepends a `reasoning` field. MIPROv2 compiles via bootstrap -> instruction proposal -> Bayesian optimization. There is no built-in `.example.yaml` loader; demos are `dspy.Example` objects managed as a `.demos` list on predictors. All verified against installed `dspy==3.2.0` source.

---

## 1. Signature Definition with Typed Fields

**Source**: `dspy/signatures/signature.py`, `dspy/signatures/field.py`

Signatures are Pydantic `BaseModel` subclasses. `InputField` and `OutputField` are thin wrappers around `pydantic.Field` with `__dspy_field_type` metadata.

```python
import dspy
from typing import Optional, Literal

class ModuleAnalyzer(dspy.Signature):
    """Analyze a module's discovery pattern and return structured findings."""

    # Input fields
    module_name: str = dspy.InputField(desc="Name of the module to analyze")
    source_code: str = dspy.InputField(desc="Full source code of the module")

    # Typed output fields
    pattern: Literal["singleton", "builder", "factory", "adapter"] = dspy.OutputField(
        desc="Detected design pattern"
    )
    dependencies: list[str] = dspy.OutputField(desc="List of module dependencies")
    quality_score: float = dspy.OutputField(
        ge=0.0, le=1.0, desc="Quality assessment score"
    )
    confidence: int = dspy.OutputField(
        ge=0, le=100, desc="Confidence percentage"
    )
    optional_notes: Optional[str] = dspy.OutputField(
        desc="Additional notes if any"
    )
    metadata: dict[str, str] = dspy.OutputField(
        desc="Key-value metadata extracted"
    )
```

**Key observations from source inspection:**

| Aspect | Detail |
|--------|--------|
| `InputField` source | `pydantic.Field(**kwargs)` with `__dspy_field_type="input"` |
| `OutputField` source | Same, with `__dspy_field_type="output"` |
| Type preservation | Field annotations (`int`, `float`, `list[str]`, `Optional`) are preserved on Pydantic fields |
| Auto-prefix | Fields get auto prefixes like `"Question:"` based on field name |
| Field order | Determined by Pydantic field order (declaration order) |

**Typed output behavior**: The LM receives the type annotation as part of the prompt schema. The output is parsed against the Pydantic type. For `int`, the model must emit a parsable integer. For `list[str]`, it must emit a valid list representation.

---

## 2. Prompts Attached to Signatures

**Source**: `dspy/signatures/signature.py`, `dspy/predict/predict.py`

### 2a. Instructions via docstring or `with_instructions()`

```python
# Option 1: Docstring becomes default instructions
class BasicQA(dspy.Signature):
    """Answer the question concisely."""
    question: str = dspy.InputField()
    answer: str = dspy.OutputField()

# Option 2: Override instructions dynamically
OptimizedQA = BasicQA.with_instructions(
    "Read the question carefully. Provide a one-sentence answer only."
)

# Option 3: Set instructions on signature class via with_updated_fields
```

**Important**: The docstring of a Signature class becomes the **default instructions** for every predictor using that signature. MIPROv2 optimizes these instructions.

### 2b. Few-shot demos on Predictors

```python
# Demo storage is on the predictor module, not the signature
predictor = dspy.Predict(BasicQA)
predictor.demos = [
    dspy.Example(question="What is 2+2?", answer="4"),
    dspy.Example(question="What is blue?", answer="A color"),
]

# Or manually append
predictor.demos.append(dspy.Example(question="?", answer="?"))
```

### 2c. External `.example.yaml` pattern

**DSPy has NO built-in YAML example loader.** The pattern is manual:

```python
import yaml

def load_examples(yaml_path: str, input_keys: list[str]) -> list[dspy.Example]:
    with open(yaml_path) as f:
        data = yaml.safe_load(f)  # list of dicts
    return [
        dspy.Example(**row).with_inputs(*input_keys)
        for row in data
    ]
```

Demos can then be loaded from YAML and set on `predictor.demos` directly, or stored in an anchor dataset schema and converted at runtime.

---

## 3. MIPROv2 Compilation with Bootstrap Dataset

**Source**: `dspy/teleprompt/mipro_optimizer_v2.py`

### Constructor params (verified from `__init__` signature)

```python
optimizer = dspy.MIPROv2(
    metric=your_metric_fn,          # Callable(predicted, ground_truth) -> score
    prompt_model=None,              # Optional: separate model for instruction generation
    task_model=None,                # The model used during evaluation (or use dspy.configure)
    teacher_settings=None,          # Dict, e.g., dict(lm=gpt4o) for teacher
    max_bootstrapped_demos=4,       # Max auto-generated traces per predictor
    max_labeled_demos=4,            # Max pre-labeled examples in final prompt
    auto="light",                   # "light" | "medium" | "heavy" | None
    num_threads=None,               # Parallel evaluation threads
    max_errors=None,                # Error tolerance during compilation
    seed=9,                         # Random seed
    init_temperature=1.0,           # Starting temperature
    log_dir=None,                   # Optional: directory for optimization logs
)
```

### Compile method

```python
compiled = optimizer.compile(
    student=your_program,           # dspy.Module instance
    trainset=trainset,              # list[dspy.Example], REQUIRED
    teacher=None,                   # Optional teacher module for bootstrapping
    valset=None,                    # Optional validation split
    max_bootstrapped_demos=None,    # Override constructor default
    max_labeled_demos=None,         # Override constructor default
    minibatch=True,                 # Use minibatch evaluation (default True)
    minibatch_size=35,              # Mini-batch size
    minibatch_full_eval_steps=5,    # Full eval interval
)
```

### Compilation flow (verified from source)

```
Phase 1: Bootstrap few-shot examples
  -> create_n_fewshot_demo_sets(student, trainset, metric, teacher)
  -> Runs student on trainset, keeps high-scoring traces
  -> Produces N demo_candidates (sets of demonstrations)

Phase 2: Grounded instruction proposal
  -> Generates instruction candidates per predictor
  -> Uses program code + bootstrapped demos + data properties

Phase 3: Bayesian optimization (Optuna)
  -> For each trial:
      a. Select instruction index from instruction_candidates[i]
      b. Select demo set from demo_candidates[i]
      c. Insert into candidate program
      d. Evaluate on minibatch
  -> Surrogate model updates continuously
  -> Best full-evaluated program returned
```

### Auto mode settings

```python
AUTO_RUN_SETTINGS = {
    "light":  {"n": 20, "val_size": 50},
    "medium": {"n": 50, "val_size": 100},
    "heavy":  {"n": 100, "val_size": 200},
}
```

### How demos are stored on compiled program

From `_select_and_insert_instructions_and_demos`:
```python
for i, predictor in enumerate(candidate_program.predictors()):
    # Instructions go on the signature
    updated_sig = get_signature(predictor).with_instructions(selected_instruction)
    set_signature(predictor, updated_sig)
    # Demos go on the predictor directly
    predictor.demos = demo_candidates[i][demos_idx]
```

**The compiled program has optimized instructions and demos embedded on its predictors.**

---

## 4. ChainOfThought for Reasoning

**Source**: `dspy/predict/chain_of_thought.py`

`ChainOfThought` is NOT a decorator. It is a module class that wraps `Predict`:

```python
class ChainOfThought(Module):
    def __init__(
        self,
        signature: str | type[Signature],
        rationale_field: FieldInfo | None = None,   # Custom reasoning field
        rationale_field_type: type = str,           # Type of reasoning output
        **config,
    ):
        super().__init__()
        signature = ensure_signature(signature)
        desc = "${reasoning}"
        rationale_field_type = rationale_field.annotation if rationale_field else rationale_field_type
        rationale_field = rationale_field if rationale_field else dspy.OutputField(desc=desc)
        # Prepend "reasoning" field BEFORE other output fields
        extended_signature = signature.prepend(
            name="reasoning", field=rationale_field, type_=rationale_field_type
        )
        self.predict = dspy.Predict(extended_signature, **config)
```

**What it does**: Prepends a `reasoning` field to the signature's output, putting it between inputs and other outputs. The model produces step-by-step reasoning before the final answer.

```python
# Basic usage
qa = dspy.ChainOfThought("question -> answer")
result = qa(question="What is the capital of France?")
print(result.reasoning)  # "Step-by-step reasoning..."
print(result.answer)     # "Paris"

# With class signature
class ModuleAnalyzer(dspy.Signature):
    module_path: str = dspy.InputField()
    pattern: str = dspy.OutputField()
    quality_score: float = dspy.OutputField()

analyzer = dspy.ChainOfThought(ModuleAnalyzer)
result = analyzer(module_path="/path/to/module.py")
print(result.reasoning)    # Why this pattern, why this score
print(result.pattern)      # "singleton"
print(result.quality_score)  # 0.85
```

**Key point**: The `reasoning` field is prepended at index 0 of outputs, not appended. This means output order is: `[reasoning, <original_outputs>]`.

---

## 5. DSPy 3.1 -> 3.2 Changes Affecting Signatures

**Source**: Installed `dspy==3.2.0` source inspection

| Area | Change | Impact |
|------|--------|--------|
| `InputField`/`OutputField` | Now delegates to `pydantic.Field` directly | `desc` still works, `ge`/`le`/`gt`/`lt` constraints work |
| `with_instructions()` | Returns new class, does NOT mutate | Existing code using it is compatible |
| `prepend`/`append`/`delete`/`insert` | All work on class level, return new classes | Compatible |
| `with_updated_fields()` | Updates `json_schema_extra` + optional type annotation | Compatible |
| SignatureMeta | Uses frame introspection for custom type resolution in string signatures | `custom_types` param available if introspection fails |
| `requires_permission_to_run` | **REMOVED** in 3.2.0 | If set to `True`, raises error. Remove from any existing calls. |
| `new_signature` kwarg | **REMOVED** from Predict | `assert "new_signature" not in kwargs` in `_forward_preprocess` |
| LM configuration | Must use `dspy.LM("provider/model")` not string | Error if string passed to `dspy.configure(lm=...)` |
| `dspy.Example` | Now uses internal `_store` dict, not dict subclass | `.keys()`, `.values()`, `.items()` work via `__getattr__` |

**Breaking changes to watch for**:
1. `requires_permission_to_run=True` raises error now
2. `new_signature` kwarg removed from Predict
3. `dspy.configure(lm="openai/gpt-4o")` fails -- must use `dspy.LM("openai/gpt-4o")`

---

## 6. Structured Typed Outputs vs Raw Dicts

**Source**: DSPy docs, Context7 examples, source inspection

### Typed outputs (recommended)

```python
class StructuredOutput(dspy.Signature):
    """Extract structured data from text."""
    text: str = dspy.InputField()

    categories: list[str] = dspy.OutputField(desc="Category labels")
    score: float = dspy.OutputField(ge=0.0, le=1.0)
    tags: list[str] = dspy.OutputField(desc="Relevant tags")
    is_valid: bool = dspy.OutputField()
    count: int = dspy.OutputField()
    metadata: dict[str, str] = dspy.OutputField()
```

**Pros**:
- Type hints appear in prompt (model knows to output parsable values)
- Pydantic Field constraints (`ge`, `le`) added to prompt schema
- Easier downstream processing
- Better MIPROv2 optimization (clearer signal)

**Cons**:
- LLMs are less reliable with complex types (nested dicts, custom types)
- Parsing errors silently produce wrong values

### Raw string output with manual parsing

```python
class RawOutput(dspy.Signature):
    """Extract data, output as structured text."""
    text: str = dspy.InputField()
    result: str = dspy.OutputField(desc="JSON-formatted result")
```

**Pros**:
- Maximum flexibility
- Can handle any structure
- Easier to debug (raw text visible)

**Cons**:
- Need manual JSON parsing
- No type enforcement in prompt
- MIPROv2 has less structure to optimize over

### Recommendation for the 4 project signatures

Given the anchor dataset schema already has typed fields (`float`, `list[str]`, `int`, `dict[str, float]`), **use typed outputs** where the types are simple primitives. For complex nested structures, use `dict[str, Any]` as output and parse manually.

---

## 7. Integration with Existing Anchor Dataset Schema

**Source**: `infrastructure/anchor_dataset/anchor_dataset_schema.py`

The existing schema maps to DSPy fields:

```python
DSPY_FIELD_MAP = {
    "inputs": ["legacy_pattern", "domain_context"],
    "labels": [
        "expected_trajectory",
        "expected_tool_usage_patterns",
        "expected_coherence",
        "expected_overall",
        "expected_quality_score",
        "expected_optimized_parameters",
    ],
}
```

Converting to DSPy examples:
```python
examples = jsonl_to_dspy_examples("anchors.jsonl")
# Each Example has _store dict with all fields
# Need to call .with_inputs("legacy_pattern", "domain_context") to tag inputs
```

**Gap**: The current `jsonl_to_dspy_examples` does NOT call `.with_inputs()`, so DSPy cannot distinguish inputs from labels. This must be fixed.

---

## Recommendations

1. **Use class-based Signatures** (not string syntax) for the 4 DSPy signatures -- provides type safety and IDE support.
2. **Use typed OutputFields** (`float`, `int`, `list[str]`, `Optional[str]`) for all simple primitive outputs. This gives MIPROv2 clearer optimization targets.
3. **Create demos externally** (YAML or JSONL) and load at runtime -- DSPy has no built-in loader. Use `dspy.Example(**row).with_inputs(*input_keys)` pattern.
4. **Fix `jsonl_to_dspy_examples`** to add `.with_inputs()` call for proper input/label distinction.
5. **Remove `requires_permission_to_run`** from any existing MIPROv2 calls.
6. **Use `ChainOfThought`** (not `Predict`) for all 4 signatures to get built-in reasoning capability.
7. **Keep `auto="light"`** for initial compilation; scale to `"medium"` if optimization quality is insufficient.

## Sources

| Source | Key Information |
|--------|----------------|
| Installed `dspy==3.2.0` source (`/mnt/bunker_data/ai/data_factory/.venv/lib/python3.14/site-packages/dspy/`) | All verified APIs, method signatures, constants |
| `dspy/signatures/signature.py` | Signature class, SignatureMeta, with_instructions, prepend/append/delete/insert |
| `dspy/signatures/field.py` | InputField/OutputField implementation |
| `dspy/predict/chain_of_thought.py` | ChainOfThought prepends reasoning field |
| `dspy/predict/predict.py` | Predict demos, _forward_preprocess, adapter calling |
| `dspy/teleprompt/mipro_optimizer_v2.py` | MIPROv2 compile, bootstrap, instruction proposal, Bayesian optimization |
| `dspy/primitives/example.py` | dspy.Example with _store dict |
| `dspy/adapters/two_step_adapter.py` | Demo formatting into messages |
| `dspy/teleprompt/utils.py` | create_n_fewshot_demo_sets signature |
| Context7 `/websites/dspy_ai` | 3105 code examples, typed signature patterns |
| `infrastructure/anchor_dataset/anchor_dataset_schema.py` | Existing project DSPy integration |
| `specs/module-discovery-strategy-auto/research.md` | Prior MIPROv2 research |

## Unresolved Questions

1. **Does DSPy 3.2.0 support `pydantic.Field` constraints** like `ge`/`le`/`regex` on OutputFields? The source shows `InputField` delegates to `pydantic.Field(**kwargs)`, so they should work, but this has not been end-to-end tested with LM inference.
2. **How does DSPy 3.2.0 handle `list[str]` output parsing?** Does it expect JSON array format, newline-separated, or some other convention?
3. **What is the default adapter used in DSPy 3.2.0?** The project has multiple adapters installed (JSON, XML, TwoStep). The default may affect how typed outputs are formatted in prompts.
