---
spec: module-discovery-strategy-auto
phase: research
created: 2026-04-25T00:00:00Z
---

# Research: DSPy MIPROv2 Anchor Dataset Requirements

## Executive Summary

DSPy does **not** use a formal concept called "anchor datasets" as a distinct artifact. What is commonly referred to as "anchors" in MIPROv2 context maps to three DSPy-native concepts: (1) **labeled demonstrations** (pre-provided input-output pairs with ground truth), (2) **bootstrapped demonstrations** (auto-generated traces from running the program on training data), and (3) the **training set** itself (a list of `dspy.Example` objects). The training set format is Python-native (`dspy.Example`), not JSONL or any file format. Ground truth is simply the label fields in each Example, distinguished from input fields via `.with_inputs()`.

## 1. How MIPROv2 Uses Training Data (Anchors)

MIPROv2 operates in **three phases**:

### Phase 1: Bootstrapping
- Executes the program repeatedly on training records using a "teacher model"
- Collects input-output-execution traces
- **Filters**: only keeps traces that achieve high scores according to the evaluation metric
- The retained traces become **bootstrapped few-shot examples**

### Phase 2: Grounded Proposal
- Analyzes program code, training data properties, and the high-scoring bootstrapped traces
- Generates many candidate prompt instructions for each predictor
- Also proposes candidate few-shot demonstrations
- Given a random "tip" to encourage exploration

### Phase 3: Discrete Search (Bayesian Optimization)
- Samples mini-batches from training set to evaluate candidate programs
- Updates a surrogate model continuously
- Selects the best combination of instructions + demonstrations

**Key insight**: "Anchors" are the training data used across all three phases. The bootstrapped demos serve as "ground-truth traces" that inform instruction generation.

## 2. Format Requirements

DSPy uses **Python-native objects**, not JSONL.

### Core Format: `dspy.Example`

```python
# Creation via keyword arguments
example = dspy.Example(
    question="What is DSPy?",
    answer="A programming framework for LLMs"
)

# Tag which fields are inputs (all others become labels/ground truth)
example = example.with_inputs("question")

# Can also be unpacked from dict
example = dspy.Example(**{"question": "...", "answer": "..."}).with_inputs("question")
```

### Dataset Format: List of Examples

```python
trainset = [
    dspy.Example(report="LONG REPORT TEXT 1", summary="short summary 1").with_inputs("report"),
    dspy.Example(report="LONG REPORT TEXT 2", summary="short summary 2").with_inputs("report"),
    # ... more examples
]

devset = trainset[200:500]  # split from same pool
```

**No JSONL required.** DSPy examples are Python objects. If you need to persist to disk, you would serialize the Examples manually (they are dict-like internally).

### Fields Structure

| Category | How Determined | Example |
|----------|---------------|---------|
| **Inputs** | Explicitly tagged via `.with_inputs("field")` | `question`, `report`, `context` |
| **Labels (Ground Truth)** | Everything NOT tagged as input | `answer`, `summary` |
| **Metadata** | Unmarked fields (not used in prompt) | Any extra fields |

You can extract pure input/label views:
```python
pure_inputs = example.inputs()   # only tagged fields
pure_labels = example.labels()   # only untagged fields
```

## 3. Minimum and Typical Anchor Counts

| Scenario | Examples | Source |
|----------|----------|--------|
| **Basic optimization** | ~10 | DSPy docs |
| **Broader search** | ~50 | DSPy docs |
| **Extended instruction optimization** | ~200+ | DSPy docs (prevent overfitting) |
| **Default `max_labeled_demos`** | 16 | DSPy constructor default |
| **Default `max_bootstrapped_demos`** | 4 | DSPy constructor default |
| **Tutorial examples** | 200 train / 300 dev | Multihop Search tutorial |

**Recommended for MIPROv2**:
- **Minimum**: 50 examples in trainset
- **Good**: 200+ examples to support both bootstrapping and labeled demos without overfitting
- **Devset**: Separate 20-30% from training pool for evaluation during optimization

## 4. What "Ground Truth" Means in DSPy

In DSPy, **ground truth is not a separate concept** -- it is simply the label fields within training Examples.

- When you create `dspy.Example(question="...", answer="...").with_inputs("question")`, the field `answer` **is** the ground truth
- The **metric function** is what compares the model's prediction against this ground truth
- Ground truth is used by:
  1. **Bootstrapping**: The teacher model's output is compared against ground truth via the metric
  2. **Evaluation**: The devset examples have ground truth labels that the metric evaluates
  3. **Labeled demos**: Pre-provided input-output pairs that are used directly as few-shot examples

**Ground truth = the label fields in your Examples, evaluated by your metric function.**

## 5. What Makes a "Good" Anchor Dataset

Based on DSPy documentation and patterns from tutorials:

### Good Dataset Characteristics
- **Representative**: Covers the range of inputs the model will see in production
- **Sufficient quantity**: At least 50 examples; 200+ preferred for MIPROv2
- **Correct ground truth**: Labels must be accurate -- the metric can only be as good as the labels
- **Consistent format**: Same field structure across all examples
- **Diverse**: Examples should cover edge cases and different input patterns
- **Clean**: No noise in labels; inconsistent ground truth confuses bootstrapping

### Bad Dataset Characteristics
- **Too small**: < 10 examples leads to overfitting and poor generalization
- **Noisy labels**: Inconsistent or incorrect ground truth causes bootstrapping to accept wrong traces
- **Narrow domain**: Only covers one narrow input pattern, causing poor generalization
- **Missing fields**: Examples that don't have all the fields expected by the signature
- **Inconsistent types**: Mixing string/non-string for same field across examples

## 6. Role of Anchor Quality on Optimization Results

**Critical**: MIPROv2 is explicitly described as "data-aware and demonstration-aware." This means:

1. **Bootstrapping quality depends on trainset quality**: If the trainset has poor ground truth, the bootstrapping phase will either fail to produce valid traces or produce incorrect demonstrations that poison the instruction generation.

2. **Ground proposal quality depends on bootstrapped demos**: The instruction generation phase uses bootstrapped traces as reference. Bad traces = bad instruction proposals.

3. **Discrete search quality depends on both**: Mini-batch evaluation uses training data to score candidates. Unrepresentative data = candidates optimized for the wrong distribution.

4. **The metric is the ultimate signal**: Even with good data, a poorly designed metric will optimize for the wrong thing.

## 7. MIPROv2-Specific Data Considerations

### Hyperparameters That Affect Data Usage
| Parameter | Default | Effect |
|-----------|---------|--------|
| `max_labeled_demos` | 4 | Max pre-labeled examples in final prompt |
| `max_bootstrapped_demos` | 4 | Max auto-generated traces per predictor |
| `auto` | "light" | Optimization mode (light/medium/heavy) |
| `num_threads` | None | Parallel evaluation threads |
| `minibatch_size` | N/A | Size of mini-batches for discrete search |

### Important Notes
- **`max_bootstrapped_demos + max_labeled_demos`** = total demos in final prompt (not per-predictor, but shared budget)
- **`auto="heavy"`** requires more training data than `"light"`
- **`data_aware_proposer=False`** may be needed if your data contains unprocessable content (e.g., audio files)

### Typical MIPROv2 Pattern (from official tutorials)
```python
# 1. Create examples with explicit input/label separation
trainset = [
    dspy.Example(question=q, answer=a).with_inputs("question")
    for q, a in raw_data
]

# 2. Split train/dev
trainset, devset = trainset[:n], trainset[n:]

# 3. Compile with MIPROv2
optimizer = dspy.MIPROv2(
    metric=your_metric,
    prompt_model=gpt4o,
    teacher_settings=dict(lm=gpt4o),
    auto="medium",
)
compiled = optimizer.compile(
    student=your_program,
    trainset=trainset,
    devset=devset,       # for evaluation
    max_bootstrapped_demos=4,
    max_labeled_demos=4,
    minibatch_size=40,
    minibatch_full_eval_steps=4,
)
```

## 8. Patterns to Follow

1. **Always use `.with_inputs()`** -- this is the single most important step. Without it, DSPy cannot distinguish inputs from labels.
2. **Provide some labeled demos** alongside bootstrapped ones for stable baseline performance.
3. **Keep devset separate** -- never mix train and dev data.
4. **Design metric carefully** -- the metric is what drives the entire optimization. A weak metric = weak results regardless of data quality.
5. **Start small, iterate** -- begin with ~50 examples, evaluate, then expand.
6. **Use the teacher model settings** to control which model generates bootstrapped traces (can be different from the task model).

## Open Questions

1. **JSONL persistence**: DSPy doesn't mandate JSONL, but if you need to save/load datasets, what serialization format should we use? (The Examples are dict-like internally.)
2. **External paper references**: The MIPRO paper (arXiv:2310.20411) may contain formal definitions of "anchor" datasets. We couldn't fully parse the PDF. This may need separate investigation.
3. **Anchor quality metrics**: DSPy doesn't provide built-in quality scores for training examples. How should we measure "anchor quality" before running MIPROv2?

## Sources

| Source | Key Information |
|--------|----------------|
| [dspy.ai API: MIPROv2](https://dspy.ai/api/optimizers/MIPROv2) | Constructor params, three-phase process, default values |
| [dspy.ai: Training Data](https://dspy.ai/learn/evaluation/data) | `dspy.Example`, `.with_inputs()`, trainset/devset creation |
| [dspy.ai: Optimization Overview](https://dspy.ai/learn/optimization/optimizers) | Three phases, bootstrapping, labeled vs bootstrapped demos |
| [dspy.ai: Multihop Search Tutorial](https://dspy.ai/tutorials/multihop_search) | Full MIPROv2 compilation example with Hover dataset |
| [GitHub: stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | Bootstrap teleprompter source code, labeled/demo terminology |
| [Context7: DSPy Library Docs](https://dspy.ai/) | 3105 code snippets, 82.82 benchmark score |
| [MIPRO Paper (arXiv:2310.20411)](https://arxiv.org/abs/2310.20411) | Original paper -- PDF could not be fully parsed |
