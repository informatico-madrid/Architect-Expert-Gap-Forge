# Real-World Case Study: Bridging the "2026 Knowledge Cutoff" in Mission-Critical Domotics 🏠🧠

While **Architect-Expert-Gap-Forge (AEGF)** is a domain-agnostic framework, its architecture was forged in one of the most unforgiving, undocumented, and rapidly evolving codebases: **Home Assistant (HA) Core & HACS (2026 Standards).**

This document serves as an engineering log and practical demonstration of how AEGF was used to transform a generalist LLM (anchored in 2023 knowledge) into a specialized 2026 HA Architect, operating entirely on sovereign, constrained consumer hardware.

## 1. The Business & Technical Problem

Modern Large Language Models (LLMs) suffer from **Parametric Amnesia** (Knowledge Cutoff). 
When tasked with writing modern Home Assistant integrations, base models (like Qwen 2.5/3 or Llama 3) confidently hallucinate deprecated 2023 paradigms:
- Using `hass.data` instead of the mandated `entry.runtime_data`.
- Using singular `async_forward_entry_setup` instead of the pluralized awaitable `async_forward_entry_setups`.
- Failing to implement strict `DataUpdateCoordinator` typing.

**The Mission:** Force a 30-Billion parameter Mixture of Experts (MoE) model to "forget" its deprecated training and adhere strictly to a synthetic set of "2026 HA Laws" without losing its general reasoning capabilities.

## 2. Engineering Constraints & The "Bunker" Node

The training and inference had to be executed locally (Zero-Trust/Sovereign AI) on a "Prosumer" High-Performance Computing (HPC) node. This forced strict resource management:
- **Compute:** Dual NVIDIA RTX 5090 (Blackwell sm_120) - 64GB Total VRAM.
- **CPU:** AMD Threadripper 7960X (Affinities isolated for I/O).
- **RAM:** 128GB ECC (A critical bottleneck for a 30B MoE with DeepSpeed ZeRO-3 states).

## 3. How AEGF Solved the Use Case (The 4-Stage Pipeline)

To override the model's fundamental weights, we deployed the 4-stage AEGF pipeline:

1. **Stage 1 (Ingestion & Abstraction):** Parsed the raw Home Assistant integration repositories. Replaced deprecated function bodies with high-seniority docstrings via AST parsing, forcing the LLM to *deduce* logic rather than rote-copying.
2. **Stage 2 (Inverse-Instruct):** Injected the `HA_MASTER_GUIDE_2026.md`. Forced the Teacher LLM to explicitly reason about deprecations: *"The user asks for X, but under 2026 laws, Y is deprecated. I must use Z."*
3. **Stage 3 (UQI Filtering):** Rejected any synthetic sample containing legacy strings like `hass.data`, ensuring 100% "Gold" purity for the SFT dataset.
4. **Stage 4 (The Quality Gate):** Implemented a Teacher-Student Inversion. An external LLM (Gemini 1.5) was used as a dynamically constrained "Judge" to validate the newly trained 5090 model against a multi-dimensional rubric (Structural Fidelity, API Modernity).

## 4. Engineering Timeline & "War Stories"

Training a 30B MoE locally is not a straightforward API call. The development of AEGF was driven by sequentially overcoming severe systemic hardware and cognitive failures:

### Phase 1: Infrastructure & Inference Stabilization
* **The Initial OOM & Blackwell Deadlocks:** Attempting to load a 32B model in BF16 caused an immediate Out of Memory crash. Furthermore, early Blackwell (sm_120) P2P driver incompatibilities triggered Kernel deadlocks. **The Fix:** Pivoted to AWQ 4-bit quantization and bypassed P2P kernel bugs by forcing `NCCL_DMABUF_ENABLE=1` on Linux Kernel 6.14.
* **The 80B Trap & GSP Lockup:** Attempting to scale to an 80B model destroyed the KV Cache and locked the GPU System Processor (GSP), requiring a physical cold boot. **The Fix:** Strategic retreat. Abandoned 80B for a 30B Sparse MoE architecture, locking native context window at a stable 262,144 tokens.
* **Thermal Threats:** Sustained inference pushed GDDR7 memory close to the 95°C critical threshold. **The Fix:** Engineered `monitor_gddr7.py`, a hardware watchdog using Linux `SIGTSTP/SIGCONT` signals to dynamically pause/resume compute processes based on thermal hysteresis without losing VRAM state.

### Phase 2: The Data Factory & Cognitive Resistance
* **The Tool-Call Trap:** vLLM's internal parsers were stripping the `<think>` and `<tool_call>` tags, preventing reasoning dataset generation. **The Fix:** Engineered a custom raw-text pipeline that bypassed standard parsers and validated output structural integrity via AST.
* **"El Modelo Rebelde" (The Cognitive Anchor):** Iterations V1 (Rank 8) and V2 (Rank 32) failed structural tests. The MoE architecture stubbornly preferred the frozen 2023 weights over the LoRA adapter. **The Fix:** Escalated to RSLoRA (Rank-Stabilized LoRA) with Rank 64. Crucially, expanded SFT `target_modules` to include the `gate_proj` (expert routers), forcing the model to rewire its decision tree at the routing layer.

### Phase 3: Hardware Limits & Enterprise Enforcement
* **The OOM Death & I/O Stall (Swap Saturation):** DeepSpeed ZeRO-3 optimizer states for Rank 64 choked the 128GB physical RAM. The Docker daemon executed a `SIGKILL (Signal 9)`. The OS forced offloading to a single NVMe, causing massive `iowait` bottlenecks.
* **The AEGF Fix:** Architected **Parallel Striping Swap**. Routed the VRAM offload through the Threadripper's PCIe Gen 5 bus directly into two Samsung 990 PRO NVMe drives configured with identical priorities (`pri=100`) in `/etc/fstab`. This tricked the Linux kernel into a round-robin PCIe traffic distribution, recovering throughput to ~143 tokens/s despite heavy swap reliance.

## 5. Final Results & Metrics (V3 Checkpoint)

*(NOTE: Awaiting final Epoch 2 completion for concrete values)*

- **Baseline Model (Qwen3-30B) API Modernity Score:** `[PENDING]` / 100
- **AEGF Fine-Tuned Model API Modernity Score:** `[PENDING]` / 100
- **Knowledge Delta (Improvement):** `[PENDING]`%
- **Training Efficiency:** Successfully stabilized MoE training at `[X]` loss, maintaining local data sovereignty.

---
## Stage 3.5 — Backtracking Alignment (Real run example)

During the V3 evaluation we executed the Stage 3.5 rewriter as a DISTINCT auditing step over
the distilled dataset (`v11_DISTILLED.jsonl`) to inject self-correction trajectories into the
`<think>` blocks while preserving the SACRED action text after `</think>` byte-for-byte.

Example run (recommended):

```bash
python src/curation/backtracking_rewriter.py \
	--input data/synthetic/v11_DISTILLED.jsonl \
	--output data/synthetic/v11_backtracking_aligned.jsonl \
	--config configs/stage_3_curation/backtracking_alignment.yaml \
	--audit-dir data/reports/backtracking_audit \
	--log-level INFO
```

What this run does:
- Rewrites only the content inside `<think>...</think>` and leaves the code/action block untouched.
- Emits compact, human-readable progress lines to the terminal every `batch_size` eligible records.
- For each processed record the terminal shows a short excerpt (≤300 chars) and the rewrite strategy.
- If `--audit-dir` is provided a timestamped subdirectory is created and the FULL rewritten `<think>`
	text for each record is saved as a separate pretty-printed `.json` file for offline inspection and auditing.

Sample audit / smoke-run summary (50-record sample executed during validation):

- Input records: 50
- Filtered out (not eligible): 9
- Rewritten: 41
	- `error_first`: 6
	- `trace_reconstruction`: 26
	- `full_backtracking`: 9
- Failed rewrites: 0

The terminal shows a rolling progress line such as:

```
Processed 10/13257 eligible (0.1%) — rewritten=10 pass=0 failed=0 elapsed=12.3s rate=0.81/s
```

And a per-record audit line (trimmed excerpt) like:

```
INFO  src.curation.backtracking_rewriter: id=r123 strategy=trace_reconstruction new_think_len=842 excerpt=Start by avoiding the legacy pattern that uses hass.data and instead...
```

If the text is long the terminal will include an additional pointer:

```
INFO  src.curation.backtracking_rewriter: Full text saved to data/reports/backtracking_audit/backtracking_20260306_142130/r123.json
```

This combination (concise terminal + per-record full-text audit) lets an engineer monitor
the ongoing rewriting in real time while retaining a complete, auditable record for later
manual review or compliance checks.

*This use case demonstrates that AEGF is not just a scripting tool, but a production-grade pipeline capable of overcoming extreme hardware limitations to enforce strict structural compliance in Enterprise LLM deployments.*