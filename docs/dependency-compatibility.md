# Dependency Compatibility

> Validated: 2026-04-24 | Spec: `dependency-compatibility` | Epic: `aegf-infrastructure`

## 1. Dependency Tree

### Direct Dependencies

| Package | Version | Type | Source File | Notes |
|---------|---------|------|-------------|-------|
| PyYAML | >=6.0 | existing | requirements.txt | Config parsing |
| pydantic | >=2.0 | existing | requirements.txt | Data validation |
| requests | >=2.28 | existing | requirements.txt | HTTP client |
| tqdm | >=4.64 | existing | requirements.txt | Progress bars |
| httpx | >=0.27 | existing | requirements.txt | Async HTTP |
| huggingface-hub | >=0.22 | existing | requirements.txt | HF dataset/model ops |
| tiktoken | >=0.7 | existing | requirements.txt | LLM token counting |
| click | >=8.1 | existing | requirements.txt | CLI framework |
| google-genai | >=1.0 | existing (optional) | requirements.txt | Gemini API backend |
| python-dotenv | >=1.0 | existing | requirements.txt | Env var loading |
| **dspy** | **==3.2.0** | **new** | requirements.txt | Prompt optimization (MIPROv2) |
| **langgraph** | **==0.2.76** | **new** | requirements.txt | State machine for LLM workflows |
| **openai** | **==2.32.0** | **moved** | requirements.txt | Moved from dev to runtime |
| **numpy** | **==2.4.4** | **new** | requirements.txt | Bugfix: was missing, imported in 2 files |
| **datasets** | **==2.21.0** | **pinned** | requirements.txt | Pinned from >=2.19 to prevent 4.x breakage |
| packaging | >=25.0,<26.0 | bounded | requirements.txt | Transitive with breaking changes |
| fsspec | >=2023.1.0,<2025.0.0 | bounded | requirements.txt | Transitive with breaking changes |

### Key Transitive Dependencies

| Package | Version | Required By | Notes |
|---------|---------|-------------|-------|
| litellm | <=1.82.6,>=1.64.0 | dspy | **6 CVEs** (see Section 2) |
| langchain-core | !=0.3.x, >=0.2.43,<0.4.0 | langgraph | In langgraph 0.2.76 exclusion list but works by pip resolver coincidence |
| langgraph-checkpoint | <3.0.0,>=2.0.10 | langgraph | — |
| tokenizers | present | litellm | **No Python 3.14 wheels** (see Section 5) |
| orjson | >=3.9.0 | dspy | Fast JSON |
| pyarrow | >=15.0.0 | datasets | Parquet support |

## 2. CVE and Security

### litellm 1.82.6 — 6 CVEs (2 Critical, 4 High)

All CVEs are in `litellm<=1.82.6`, a transitive dependency of `dspy==3.2.0`.
Patched versions start at `litellm>=1.83.7` but dspy pins `<=1.82.6`.

| CVE ID | Severity | Description |
|--------|----------|-------------|
| GHSA-r75f-5x8p-qvmc | Critical | — |
| GHSA-jjhc-v7c2-5hh6 | Critical | — |
| GHSA-v4p8-mg3p-g94g | High | — |
| GHSA-xqmj-j6mv-4862 | High | — |
| GHSA-69x8-hrgq-fjj8 | High | — |
| GHSA-53mr-6c8q-9789 | High | — |

### Decision Gate Status

**P0 — Requires human sign-off before merge.**

| Item | Detail |
|------|--------|
| Vulnerable package | `litellm<=1.82.6` (transitive via `dspy==3.2.0`) |
| Patched version | `litellm>=1.83.7` |
| Blocker | `dspy<=3.2.0` pins `litellm<=1.82.6` |
| Options | (A) Accept risk + monitor; (B) Patch dspy pin manually; (C) Block merge; (D) Accept with automated CVE monitoring |

**Decision:** [ ] ACCEPTED — [ ] BLOCKED — [ ] DEFERRED (re-review by: \_\_\_\_)
**Signed by:** \_\_\_\_\_\_\_\_\_\_  **Date:** \_\_\_\_\_\_\_\_\_\_

> The `infrastructure/dependency_check.py` script does **not** check CVEs — this is a human-signed decision.

## 3. Version Pinning Rationale

### Why exact pins (`==`) for direct dependencies?

All four ML pipeline packages have rapid release cadences that make `>=` ranges dangerous:

| Package | Release Cadence | Reason for `==` |
|---------|----------------|-----------------|
| litellm | Every 2.4 days | Extremely fast; `>=` would pull breaking changes |
| openai | Every 5–7 days | API surface changes between minor versions |
| dspy | Every 1–3 months | Moderate cadence but breaking changes between versions |
| langgraph | Fast (weekly-ish) | Bounded with `<1.0.0` to prevent major jumps |

### Why bounded ranges for transitive deps?

| Package | Range | Reason |
|---------|-------|--------|
| packaging | `>=25.0,<26.0` | `langgraph<1.0` constraint forces downgrade from 26.0; older pins needed |
| fsspec | `>=2023.1.0,<2025.0.0` | `datasets==2.21.0` pins an older fsspec; 2025.x breaks the 2.21.x API |

## 4. Expected Downgrades

These are **safe, expected** version drops enforced by the new pins:

| Package | Current | Downgrades to | Cause |
|---------|---------|---------------|-------|
| packaging | 26.0 | 25.0 | Enforced by `langgraph<1.0` constraint |
| fsspec | 2026.3.0 | 2024.6.1 | Enforced by `datasets==2.21.0` pin |

Both are transitive dependencies. The downgrades happen silently during `pip install` and are documented here for awareness. They do not affect functionality.

## 5. Python 3.14 Caveats

### No wheels for C-extension packages

| Package | Status | Mitigation |
|---------|--------|------------|
| tokenizers | No Python 3.14 wheels | CI must have Rust toolchain for source builds |
| tiktoken | No Python 3.14 wheels | Same — Rust toolchain required in CI |

**Impact:** If CI runs on Python 3.14 without Rust installed, `pip install` will fail for `tokenizers` (via litellm) and `tiktoken`.

**Mitigation:** Add Rust toolchain to CI environment, or pin `tiktoken<0.13.0` if a wheel becomes available.

## 6. Installation Instructions

### Base install (no torch)

```bash
pip install -r requirements.txt
```

### Install with torch CPU

```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Full install with torch GPU

```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

## 7. Installation Baselines

### Measured Times

| Scenario | Time |
|----------|------|
| Base (no torch) | 30–60 seconds |
| With torch CPU | 2–5 minutes |

### Disk Usage

| Scenario | Total Size |
|----------|-----------|
| Base install (no torch) | ~595 MB |
| With torch CPU | ~2.1 GB (+1.5 GB) |
| With torch full (GPU) | ~3.6 GB (+3.0 GB) |

## 8. Optional: Torch

`torch` is **NOT** in `requirements.txt`. It is documented here because:

1. It is required for ML training (Capa 1, DSPy)
2. It is optional for inference-only deployments (Capa 2, LangGraph)
3. It adds significant disk space (1.5–3.0 GB)

**Why not in default requirements.txt:**
- Not all deployments need torch (inference-only)
- GPU installs require CUDA drivers (not available on all CI runners)
- CPU-only installs are faster and smaller for validation/testing

**Install when needed:**
```bash
# CPU-only (faster, smaller)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Full GPU (requires CUDA toolkit)
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

## 9. Monitoring and Maintenance

### Updating pins

1. Check package release notes for breaking changes before upgrading
2. Run `python infrastructure/dependency_check.py` after updating any pin
3. Run `pip install -r requirements.txt` and verify zero warnings
4. Re-run the full test suite

### CVE monitoring

- The litellm Decision Gate (Section 2) should be re-reviewed when:
  - dspy releases a version that allows `litellm>=1.83.7`
  - GitHub Dependabot or Snyk reports new CVEs
  - Monthly security review cycle

### Monitoring known fragilities

| Fragility | Package | Risk | Action |
|-----------|---------|------|--------|
| langchain-core exclusion | langgraph 0.2.76 excludes langchain-core 0.3.84 | Works by coincidence of pip resolver | Monitor langgraph releases |
| datasets 4.x API break | datasets 2.21.0 pinned to prevent 4.x | 4.x changes core data format | Pin until upgrade tested |
| tokenizers/tiktoken 3.14 | No Python 3.14 wheels | CI source build failure | Add Rust to CI |
