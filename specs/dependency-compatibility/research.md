# Research: Dependency Compatibility (Epic 0: Infrastructure Setup)

**Date:** 2026-04-23
**Environment:** Python 3.14.3 / pip 26.0.1 / Linux x86_64 / venv: `.venv/` (189MB base)

---

## Executive Summary

All four new dependencies (dspy, langgraph, torch, openai) are compatible with existing project dependencies. A full combined install (dspy==3.2.0 + langgraph==0.2.76 + datasets==2.21.0 + openai==2.32.0 + numpy==2.4.4) succeeds with zero version conflicts. All imports pass. However, the spec's claim that "torch comes via DSPy transitive dep" is incorrect -- dspy 3.2.0 does NOT pull in torch. Torch must be added explicitly if ML workloads are needed. The dspy-ai package (which the spec references at 2.5.x) is a deprecated wrapper that resolves to dspy==3.2.0 anyway, so using dspy>=3.0 directly is cleaner.

---

## Current Dependency Analysis

### Existing dependencies (requirements.txt)

| Package      | Version in file | Installed | In pyproject.toml | Notes                    |
|-------------|----------------|-----------|-------------------|--------------------------|
| PyYAML      | >=6.0          | 6.0.3     | YES (>=6.0)       | Compatible               |
| pydantic    | >=2.0          | 2.12.5    | YES (>=2.0)       | Compatible               |
| requests    | >=2.28         | 2.33.1    | YES (>=2.28)      | Compatible               |
| tqdm        | >=4.64         | 4.67.3    | YES (>=4.64)      | Compatible               |
| httpx       | >=0.27         | 0.28.1    | NO                | pyproject.toml gap       |
| huggingface-hub | >=0.22     | 1.11.0    | NO                | pyproject.toml gap       |
| datasets    | >=2.19         | 2.21.0    | NO                | pyproject.toml gap       |
| tiktoken    | >=0.7          | 0.12.0    | NO                | pyproject.toml gap       |
| click       | >=8.1          | 8.3.3     | NO                | pyproject.toml gap       |
| google-genai| >=1.0          | 1.70.0    | YES (>=1.0)       | Compatible               |
| python-dotenv | >=1.0        | 1.2.2     | YES (>=1.0)       | Compatible               |
| numpy       | MISSING        | 2.4.4     | NO                | BUG: imported in 2 files |

### Dual dependency management gaps

The following packages are in requirements.txt but NOT in pyproject.toml dependencies:
- httpx>=0.27
- huggingface-hub>=0.22
- datasets>=2.19
- tiktoken>=0.7
- click>=8.1

Also, datasets and tiktoken are in requirements.txt but not in pyproject.toml, even though both are used in the codebase.

### numpy BUG

numpy is imported by two files but missing from requirements.txt:
- src/audit/eval_bpb.py:30 (import numpy as np)
- scripts/benchmark/measure_performance.py:34 (import numpy as np)

Both files fail to run without numpy installed.

### openai location

openai>=1.0.0 is in requirements-dev.txt only. It needs to move to requirements.txt because dspy requires it at runtime.

---

## New Dependency Version Recommendations

### dspy

| Metric              | Value             |
|---------------------|-------------------|
| Recommended version | dspy==3.2.0       |
| Latest              | 3.2.0             |
| dspy-ai 2.5.43?     | Resolves to dspy 3.2.0 (wrapper, do not use) |
| Python compat       | 3.14.3 OK         |

**Critical finding:** dspy-ai==2.5.43 is a compatibility wrapper. Its pyproject.toml declares dspy>=2.5.3, which the resolver upgrades to the latest 3.x (3.2.0). Installing dspy-ai brings in the exact same packages as installing dspy directly, plus unnecessary extras (e.g., gepa). Recommendation: use dspy>=3.0 directly.

### langgraph

| Metric              | Value             |
|---------------------|-------------------|
| Recommended version | langgraph==0.2.76 |
| Latest 0.2.x        | 0.2.76            |
| Latest 1.x          | 1.1.9 (breaking changes) |
| Python compat       | 3.14.3 OK         |

**Rationale:** The spec specifies >=0.2.x. Version 0.2.76 is the final 0.2 release. langgraph 1.x has breaking API changes and pulls in langgraph-checkpoint>=3.0. Staying at 0.2.x avoids refactoring the Layer 2 state machine code that will be written later.

### torch

| Metric              | Value             |
|---------------------|-------------------|
| Recommended version | Add explicitly if ML workloads needed |
| Latest              | 2.11.0            |
| Comes from dspy?    | NO (see below)    |
| Python compat       | 3.14.3 OK         |

**Critical correction:** The spec states "torch comes via DSPy transitive dep." This is INCORRECT. Neither dspy 3.2.0 nor any of its dependencies (litellm, datasets, etc.) pull in torch. DSPy removed its torch dependency in v3.x. If the project needs torch (for ML training workloads, PyTorch models, etc.), it must be added explicitly.

**NOTE:** This was an error in the original BMAD epic.md v4.0 (Party Mode created it). Smart Ralph's research correctly identified it.

If added, recommend: torch>=2.9.0 (CPU-only variant available to avoid GPU drivers, ~1.5GB vs ~3GB full install).

### openai

| Metric              | Value             |
|---------------------|-------------------|
| Recommended version | openai==2.32.0    |
| Latest              | 2.32.0            |
| Current location    | requirements-dev.txt (must move to requirements.txt) |
| Python compat       | 3.14.3 OK         |

---

## Compatibility Findings

### No conflicts detected

Combined dry-run and real install of all dependencies succeeded:

```
dspy==3.2.0 + langgraph==0.2.76 + datasets==2.21.0 + openai==2.32.0 + numpy==2.4.4
```

All imports verified:
```
dspy 3.2.0       OK
langgraph        OK
numpy 2.4.4      OK
datasets         OK (load_dataset importable)
tiktoken 0.12.0  OK
openai 2.32.0    OK
```

### Packages pulled in (new installs)

| Package              | Version     | Source              |
|----------------------|-------------|---------------------|
| dspy                   | 3.2.0       | dspy==3.2.0         |
| litellm               | 1.82.6      | dspy==3.2.0         |
| openai                | 2.32.0      | openai==2.32.0      |
| langgraph             | 0.2.76      | langgraph==0.2.76   |
| langchain-core        | 0.3.84      | langgraph==0.2.76   |
| langgraph-checkpoint  | 2.1.2       | langgraph==0.2.76   |
| langgraph-sdk         | 0.1.74      | langgraph==0.2.76   |
| langsmith             | 0.7.33      | langgraph==0.2.76   |
| datasets              | 2.21.0      | (already listed)    |
| pandas                | 3.0.2       | datasets==2.21.0    |
| pyarrow               | 24.0.0      | datasets==2.21.0    |
| tokenizers            | 0.22.2      | litellm==1.82.6     |
| orjson                | 3.11.8      | dspy==3.2.0         |
| json-repair           | 0.59.4      | dspy==3.2.0         |
| typeguard             | 4.4.3       | dspy==3.2.0         |
| asyncer               | 0.0.8       | dspy==3.2.0         |
| gepa                  | 0.0.27      | dspy==3.2.0         |
| diskcache             | 5.6.3       | dspy==3.2.0         |
| cloudpickle           | 3.1.2       | dspy==3.2.0         |
| click                 | 8.3.3       | litellm==1.82.6     |

### Downgrades observed

| Package      | Before   | After        | Reason                          |
|-------------|----------|-------------|---------------------------------|
| packaging   | 26.0     | 25.0        | langgraph requires <26.0        |
| fsspec      | 2026.3.0 | 2024.6.1    | datasets pins fsspec<2025        |

Both downgrades are safe:
- packaging is a utility with stable API; 25.0 provides all needed features.
- fsspec is already compatible at 2024.6.1 for huggingface-hub, datasets, and litellm (via tokenizers).

### Version matrix

| Package          | Current  | Required by  | New version | Compatible |
|------------------|----------|-------------|-------------|------------|
| dspy             | --       | --          | 3.2.0       | YES        |
| langgraph        | --       | --          | 0.2.76      | YES        |
| numpy            | 2.4.4    | dspy>=1.26  | 2.4.4       | YES        |
| openai           | 2.30.0   | dspy>=0.28  | 2.32.0      | YES        |
| pydantic         | 2.12.5   | dspy>=2.0   | 2.12.5      | YES        |
| tiktoken         | 0.12.0   | litellm>=0.7| 0.12.0      | YES        |
| datasets         | --       | --          | 2.21.0      | YES        |
| huggingface-hub  | 1.11.0   | datasets>=0.16| 1.11.0    | YES        |
| click            | 8.1      | litellm     | 8.3.3       | YES        |
| tqdm             | 4.67.3   | dspy>=4.66  | 4.67.3      | YES        |

---

## Risk Assessment

### Low Risk

| Risk                          | Likelihood | Impact  | Mitigation                          |
|-------------------------------|-----------|---------|-------------------------------------|
| Version conflicts             | None      | None    | Verified with pip dry-run           |
| Import errors                 | None      | None    | All imports pass in Python 3.14     |
| Test breakage                 | Low       | Low     | New deps are additive, not replacing|
| fsspec downgrade              | Low       | Low     | Already stable at 2024.6.1          |
| packaging downgrade           | Low       | Low     | No code uses packaging directly     |

### Medium Risk

| Risk                          | Likelihood | Impact  | Mitigation                          |
|-------------------------------|-----------|---------|-------------------------------------|
| Python 3.14 compatibility     | Medium    | Medium  | Most deps have 3.14 wheels; edge cases possible with C extensions (tokenizers, pyarrow) |
| gepa dependency               | Medium    | Low     | gepa==0.0.27 is pulled by dspy as an extra dep -- monitor for abandonment |
| litellm broad scope           | Medium    | Medium  | litellm 1.82.6 pulls 50+ providers -- large install surface, potential for breaking changes |

### High Risk

| Risk                          | Likelihood | Impact  | Mitigation                          |
|-------------------------------|-----------|---------|-------------------------------------|
| numpy build from source (Python 3.12 fallback) | Medium | High | numpy 2.2.x is last to support Python 3.12; Python 3.14 uses 2.4.4. If pyproject.toml says requires-python>=3.12, pin numpy<2.4.0 for CI on 3.12 |
| pyarrow wheels for Python 3.14| Medium    | Medium  | pyarrow 24.0.0 has 3.14 wheels but may lag for new Python releases |

### dspy-ai package risk

The dspy-ai package is essentially deprecated. Installing it brings in the dspy package anyway (which is the real package). Using dspy-ai directly is discouraged because:
1. It adds a meaningless wrapper layer
2. It pulls in gepa as an unnecessary dependency
3. The version 2.x is just a compatibility shim over dspy 3.x

---

## Installation Strategy Recommendation

### Phase 1: Fix bugs first

```bash
pip install numpy>=1.26.0 openai>=2.0
```

### Phase 2: Install new dependencies

```bash
pip install dspy==3.2.0 langgraph==0.2.76
```

### Phase 3: Verify

```bash
python -c "import dspy; import langgraph; print('OK')"
python -c "import numpy; print('numpy OK')"
```

### Phase 4: Optional -- if ML workloads need torch

```bash
# CPU-only variant (~2.1 GB total with all deps)
pip install torch --index-url https://download.pytorch.org/whl/cpu
# Full GPU variant: ~3.6 GB total
```

### Updated requirements.txt recommendation (with strict pinning from deep audit)

```txt
# AEGF -- Runtime dependencies
PyYAML>=6.0
pydantic>=2.0
requests>=2.28
tqdm>=4.64
httpx>=0.27
huggingface-hub>=0.22

# Pin below 3.0 to avoid silent upgrade to 4.x (breaking API changes)
datasets==2.21.0
tiktoken>=0.7,<0.13          # Pin below 0.13 until Python 3.14 wheels available
click>=8.1
google-genai>=1.0
python-dotenv>=1.0

# Bug fix: numpy is imported but was missing
numpy==2.4.4                 # Pin exact for ABI stability

# DSPy and LangGraph Layer 2
dspy==3.2.0                  # Pin exact until 4.0 stabilizes
langgraph==0.2.76            # Pin exact; 1.x has breaking changes

# openai: moved from requirements-dev.txt (required by dspy at runtime)
openai==2.32.0               # Pin exact; rapid release cadence

# Pin transitive dependencies with known risks
packaging>=25.0,<26.0        # Pin due to langgraph exclusion list
fsspec>=2023.1.0,<2025.0.0  # Pin to match datasets 2.x constraint

# Optional: torch (uncomment if ML workloads needed)
# CPU-only variant (~2.1 GB total with all deps)
# pip install torch --index-url https://download.pytorch.org/whl/cpu
# torch>=2.9.0
```

**Known risk:** litellm 1.82.6 (transitive from dspy) has 6 CVEs (2 Critical, 4 High). All patched in litellm>=1.83.7, but dspy 3.2.0 pins `litellm<=1.82.6`, blocking the fix. Mitigation strategies: (a) Accept the risk and monitor dspy for updates that lift the upper bound, (b) Use `pip install --no-deps litellm>=1.83.7` to override (risky), (c) Pin dspy exact and track dspy releases weekly.

### Updated requirements-dev.txt recommendation

```txt
# AEGF -- Development & test dependencies
-r requirements.txt
pytest>=9.0
pytest-cov>=7.0
pytest-randomly>=3.0
pytest-asyncio>=0.24
psutil>=5.9
ruff>=0.9
```

(openai removed from dev deps since it is now in runtime)

### Updated pyproject.toml recommendation

Add missing runtime dependencies to match requirements.txt. Note: pyproject.toml currently has only 6 deps while requirements.txt has 12+. All must be synchronized with exact pins or ranges where upper bounds are needed:

```toml
dependencies = [
    "PyYAML>=6.0",
    "pydantic>=2.0",
    "requests>=2.28",
    "google-genai>=1.0",
    "python-dotenv>=1.0",
    "tqdm>=4.64",
    "httpx>=0.27",
    "huggingface-hub>=0.22",
    "datasets>=2.19,<3.0",       # Pin below 3.0 to prevent 4.x breaking API changes
    "tiktoken>=0.7,<0.13",        # Pin below 0.13 until Python 3.14 wheels available
    "click>=8.1",
    "numpy==2.4.4",               # Pin exact for ABI stability
    "dspy==3.2.0",                # Pin exact; rapid release cadence
    "langgraph==0.2.76",          # Pin exact; 1.x has breaking changes
    "openai==2.32.0",             # Pin exact; rapid release cadence
    "packaging>=25.0,<26.0",      # Pin due to langgraph exclusion list
    "fsspec>=2023.1.0,<2025.0.0", # Pin to match datasets 2.x constraint
]
```

**Why pyproject.toml uses ranges while requirements.txt uses exact pins:** `requirements.txt` is the runtime install file — exact pins (`==`) ensure reproducible installs. `pyproject.toml` dependencies are used by the build system (`pip install .`), and some packages (like datasets) legitimately need an upper bound to prevent major-version upgrades. The two files serve different purposes.

---

## Deep Research Addendum — What the Surface Install Check Missed

A deeper security and stability audit (see `deep-research.md`) revealed **5 critical findings** the surface `pip install` check completely missed:

### Critical Finding 1: litellm 1.82.6 has 6 CVEs (2 Critical + 4 High)

The installed litellm version is vulnerable to:
- **GHSA-r75f-5x8p-qvmc** (Critical): SQL injection in Proxy API key verification
- **GHSA-jjhc-v7c2-5hh6** (Critical): Auth bypass via OIDC userinfo cache key collision
- **GHSA-v4p8-mg3p-g94g** (High): Authenticated command execution via MCP stdio
- **GHSA-xqmj-j6mv-4862** (High): SSTI in `/prompts/test` endpoint
- **GHSA-69x8-hrgq-fjj8** (High): Password hash exposure and pass-the-hash
- **GHSA-53mr-6c8q-9789** (High): Privilege escalation via proxy config endpoint

All patched in litellm>=1.83.7, but dspy 3.2.0 pins `litellm<=1.82.6`, permanently blocking security upgrades.

### Critical Finding 2: dspy locks litellm to a dead version

litellm releases every **2.4 days** (20 releases in 46 days). dspy's upper bound `<=1.82.6` will permanently block security patches. The project is locked unless dspy is also updated.

### Critical Finding 3: tokenizers has NO Python 3.14 wheels

`tokenizers==0.22.2` is a Rust C-extension with no Python 3.14 wheels. In CI environments without Rust installed, `pip install` will fail or timeout. tiktoken has the same issue.

### Critical Finding 4: datasets jumped from 2.x to 4.x with breaking API changes

`datasets==2.21.0` (current) vs latest `4.8.4`. The spec says `datasets>=2.19` which could resolve to 4.x and silently break `load_dataset()` streaming behavior in `src/curation/anchor_dataset_downloader.py:140`.

### Critical Finding 5: langchain-core 0.3.84 is in langgraph 0.2.76's exclusion list

langgraph excludes 23 specific 0.3.x patch releases. langchain-core 0.3.84 is one of them. The current install works only by coincidence of pip's resolver. A fresh install may resolve differently.

### Other deep findings:

| Aspect | Surface Finding | Deep Finding |
|--------|----------------|--------------|
| Disk impact | "~3GB for torch" | Without torch: 595 MB. With torch CPU: 2.1 GB. Full: 3.6 GB. |
| Import time | Not checked | dspy: 1.55s, datasets: 0.24s, total ~1.8s |
| Release cadence | Not checked | litellm: every 2.4 days, openai: every 5-7 days, dspy: every 1-3 months |
| Version pinning | `>=3.0`, `>=0.2.76` | Industry standard for ML pipelines: exact pins (`==`) due to rapid release cadences |
| CVEs | Not checked | litellm 1.82.6: 2 Critical + 4 High |
| Python 3.14 | "Edge cases possible" | tokenizers + tiktoken: NO wheels guaranteed CI failure |
| datasets version risk | Not checked | 4.x API changes could break anchor downloader silently |

### Updated Version Pinning Recommendations

For ML pipeline reproducibility with these rapid-release packages:

```txt
dspy==3.2.0                  # Pin exact until 4.0 stabilizes
langgraph==0.2.76            # Pin exact; 1.x has breaking changes
openai==2.32.0               # Pin exact; rapid release cadence
datasets==2.21.0             # Pin exact; 4.x has breaking API changes
numpy==2.4.4                 # Pin exact; ABI stability
tiktoken>=0.7,<0.13         # Pin below 0.13 until Python 3.14 wheels
packaging>=25.0,<26.0        # Pin due to langgraph constraint
fsspec>=2023.1.0,<2025.0.0  # Pin to match datasets 2.x
```

## Key Corrections to Spec Assumptions

### Corrections to BMAD Source (errors in original BMAD epic.md v4.0)

1. **torch does NOT come from DSPy transitive deps.** The original BMAD Party Mode epic.md v4.0 line 300 says `torch (via DSPy)` — this is factually incorrect for dspy 3.x which removed torch entirely. Torch must be added explicitly if ML workloads are needed.

### Corrections by Smart Ralph Research (enrichments — new info BMAD missed)

2. **dspy-ai 2.5.x is a wrapper, not the real package.** The spec references "dspy>=2.5.x" via the dspy-ai package, but dspy-ai==2.5.43 resolves to dspy==3.2.0. Use dspy>=3.0 directly. (BMAD never mentioned dspy-ai.)

3. **numpy is imported in 2 files but missing from requirements.txt.** Both `src/audit/eval_bpb.py:30` and `scripts/benchmark/measure_performance.py:34` import numpy. This is a pre-existing bug discovered by Smart Ralph, not in BMAD.

4. **openai must be moved from dev to runtime.** openai>=1.0.0 is only in requirements-dev.txt but dspy requires it at runtime. BMAD only said "openai (via DSPy)."

5. **litellm has 6 CVEs and is permanently locked.** dspy's `litellm<=1.82.6` constraint blocks all security patches (patched in litellm>=1.83.7). This is a known-risk tradeoff — the project must either accept the vulnerability or monitor dspy for updates that lift the upper bound. (BMAD technical research did not mention litellm or CVEs.)

6. **datasets must be pinned `<3.0`.** Latest datasets is 4.8.4 — 4.x has breaking API changes that could silently break the anchor dataset downloader. (BMAD never mentioned datasets version.)

7. **tokenizers and tiktoken have NO Python 3.14 wheels.** In CI environments without Rust installed, these will fail to build from source. Mitigation: pin `tiktoken<0.13.0`, ensure CI has Rust toolchain, or target Python 3.13 for production.

8. **pyproject.toml is missing 5 runtime dependencies.** requirements.txt has httpx, huggingface-hub, datasets, tiktoken, click — all absent from pyproject.toml. This is a pre-existing inconsistency discovered by Smart Ralph.

### Clarifications

9. **langgraph 0.2.x is the right choice, but 1.x is available.** langgraph 0.2.76 is the latest stable 0.2.x and has no breaking changes from the spec's perspective. 1.x has breaking API changes. **CRITICAL:** Must pin `<1.0` explicitly to prevent accidental upgrade.

10. **datasets and tiktoken are runtime deps, not just dev.** They are used in src/curation/anchor_dataset_downloader.py and should be in pyproject.toml. **CRITICAL:** datasets must be pinned `<3.0` to avoid 4.x API breakage.

---

## DSPy Externalized Prompt Configuration — Additional Research (2026-04-24)

This section was added to answer the prompt externalization spec's dependency on DSPy capabilities. It addresses whether DSPy can manage externally-loaded prompt templates.

### Critical Finding: `dspy.PromptModule` Does NOT Exist

The spec and requirements reference `dspy.PromptModule` as a DSPy class. **This class does not exist in DSPy 3.2.0.** Verified by inspecting `dir(dspy)`.

### How DSPy Actually Manages Prompts

| Mechanism | What It Is | External Config Support |
|-----------|-----------|------------------------|
| `dspy.Signature` class docstring | Becomes the system prompt sent to the LM | No — must be Python code |
| `dspy.InputField(desc="...")` | Field description becomes part of user prompt | No |
| `dspy.Predict(sig, instructions="...")` | Adds instructions to signature-based prompt | No |
| `dspy.Module.__init__()` | Constructor; can load external YAML here | **Yes** (custom code) |
| `dspy.configure(lm=..., adapter=...)` | Sets global defaults | **No prompt loading** |

### DSPy's Actual Capabilities vs Spec Expectations

| Spec Requirement | DSPy Native Support | Reality |
|-----------------|--------------------|---------|
| YAML prompt files | **No** | Must load YAML externally in custom code |
| `.example.yaml` templates | **No** | Must load at runtime |
| DSPy manages external config | **No** | DSPy manages nothing external — it works with Python objects |
| English translations in prompts | **No built-in management** | Language is whatever you put in Signature docstrings |
| DSPy optimizes loaded prompts | **Yes** (MIPROv2) | Optimizes signature instructions, not YAML files |
| Coexistence with existing taxonomy YAMLs | **No conflict** | DSPy is separate from prompt_builder.py |

### Key Architecture Decision

**DSPy and the existing `PromptManager` serve different purposes:**

- `PromptManager` loads YAML prompts for the Stage 2 Factory pipeline (Spanish prompts, Template-style `$var` substitution)
- DSPy uses Python Signature classes where docstrings are system prompts

**They do not compete.** The recommended pattern is:
1. Keep existing `PromptManager` for Stage 2 Factory
2. Create a parallel `.example.yaml` loading layer for DSPy Signatures
3. Use a factory function: `yaml_to_signatures(path) -> dict[str, dspy.Signature]`

### DSPy Signature Creation from External Data (Feasible)

Since `dspy.Signature` is a Pydantic BaseModel, signatures can be created dynamically:

```python
def load_signatures(yaml_path: str) -> dict[str, type]:
    with open(yaml_path) as f:
        templates = yaml.safe_load(f)["prompts"]
    sigs = {}
    for key, tmpl in templates.items():
        sig = dspy.Signature(
            "question, context -> answer",  # field spec
            instructions=tmpl["system"],     # from YAML
        )
        sigs[key] = sig
    return sigs
```

This is a standard Python pattern and has no DSPy-specific complexity.

### Risks

1. **Optimization output goes to JSON, not YAML** — If DSPy MIPROv2 optimizes prompts, results save to DSPy's JSON format, not back to `.example.yaml` files
2. **No prompt versioning in DSPy** — DSPy has no semantic versioning for prompts
3. **No translation management in DSPy** — No built-in way to track multiple language versions
4. **Signature recreation overhead** — Creating Signatures at import time means fresh objects each time; caching is optional

### Sources

| Source | Key Point |
|--------|-----------|
| `python3 -c "import dspy; print(dir(dspy))"` | No `PromptModule`; only `Module`, `Predict`, `Signature` |
| `dspy.configure` help text | Only configures: `lm`, `adapter`, `callbacks`, `track_usage` |
| `dspy.Signature` help text | Is a Pydantic BaseModel; docstring = system prompt |
| DSPy docs (Context7) | Custom modules load external config in `__init__`; no YAML native support |
| AEGF `prompt_manager.py` | Existing YAML loading with `yaml.safe_load()` + `.format()` |
| AEGF `prompts_taxonomy.yaml` | 999 lines Spanish prompts, `$var` Template syntax |
| AEGF `prompt-externalization/plan.md` | Spec defines 4 `.example.yaml` files with `prompts.{key}.system/user` schema |
