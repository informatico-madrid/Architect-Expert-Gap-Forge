# Architect-Expert-Gap-Forge (AEGF) 🛠️🧠

**Bridging the LLM Knowledge Gap via Synthetic Data Synthesis & Specialized SFT.**

## 📌 Project Overview

AEGF is a high-performance pipeline designed to solve the **Knowledge Cutoff problem** in Large Language Models. While frontier models are excellent generalists, they often hallucinate or fail when dealing with rapidly evolving APIs, legacy-to-modern migrations, or domain-specific architectures (e.g., Home Assistant 2026 standards).

This project provides the infrastructure to:
1. **Extract "Gold Code"** from high-star production repositories.
2. **Inject "API Deltas"**: Real-time context from Changelogs and Breaking Changes.
3. **Synthesize "Platinum-Tier" Trajectories**: Generating `<think>` and `<tool_call>` datasets using Inverse-Instruct methodologies.
4. **MoE-Aware Fine-Tuning**: Specialized SFT protocols for Mixture-of-Experts architectures on NVIDIA Blackwell (sm_120).

---

## 🚀 Key Methodologies

### 🔹 Inverse-Instruct & Gold Injection
Instead of letting the model guess the code, we provide "Gold Standard" production code and force the model to synthesize the **Architectural Reasoning** (`<think>`) that leads to that specific implementation. This guarantees 100% syntactical accuracy in the training target.

### 🔹 API Delta Injection (The Gap Bridge)
We mitigate hallucinations by injecting a **Temporal Context Layer**. By comparing the model's cutoff date with current `CHANGELOG.md` and `Breaking Changes` files, we train the agent to recognize and correct outdated patterns.

### 🔹 Logic Density Index (LDI) Filtering
Our curation pipeline filters out "cognitive noise," ensuring the dataset has a high ratio of reasoning-to-token count, maximizing the learning efficiency of the model.

---

## ⚡ Hardware Stack: "The Bunker"

This pipeline is battle-tested on cutting-edge hardware:
- **Compute:** 2x NVIDIA RTX 5090 (Blackwell Architecture, sm_120).
- **VRAM:** 64GB GDDR7 (High-speed P2P via DMA-BUF).
- **Host:** AMD Threadripper 7960X (24C/48T).
- **Throughput:** ~60 tokens/s on 30B-A3B MoE models.

![AEGF Throughput Proof - 110.1 tok/s](docs/assets/blackwell_performance.png)

---

## 🛠️ Roadmap

- [x] **Phase 1: Infrastructure.** Stable Blackwell vLLM stack with sm_120 support.
- [ ] **Phase 2: Data Synthesis.** Current focus: Generating 1,000+ trajectories for Agentic SFT.
- [ ] **Phase 3: Expert SFT.** Fine-tuning Qwen3-30B-MoE using specialized loss-masking.
- [ ] **Phase 4: Validation.** Public release of the Home Assistant Expert Model.

---

## Technical Implementation of the Synthesis Loop

The "Synthesis Loop" implemented in `production_v9.py` serves as the core of the synthesis and curation pipeline. The process iterates over source files, applies chunking preprocessing, and generates training trajectories via calls to the remote model client; the `system_prompt` injects both the `MASTER_GUIDE` and the `TECHNICAL_CHANGELOG` to force the agent to explicitly reason about temporal deltas (contrast between the old and the new version) before producing a write action.

For code chunking the Python `ast` module is used: the `get_fragments` function parses content with `ast.parse`, extracts imports and top-level definitions (including `AsyncFunctionDef`) and constructs skeletons where bodies are replaced by placeholders. Each fragment is accompanied by metadata (`context`, `skeleton`, `original`, `virtual_filename`) that enable generating coherent implementations with the minimal necessary context.

The integration of Qwen3 reasoning tags is implemented via a controlled hybrid format: the system requires the agent to place its reasoning in the `<think>` tag and the resulting action in `<write_action>` (or `<tool_call>` for compatibility with the gold-injection step). The `parse_raw_response` function robustly extracts the reasoning block and the final content; the logical density (`LDI`) is then validated and a retry loop (`MAX_RETRIES`) is applied before accepting the sample. This design ensures traceability between the architectural reasoning and the generated code, facilitating auditability and automated curation.

## 📄 License
Apache License 2.0.

---
**Lead Architect:** [Joao Maria Arranz Aparicio / informatico-madrid](https://github.com/informatico-madrid)  
**Location:** Spain - Sovereign AI Infrastructure.

## Current Status

Generating 1,000+ samples. Avg speed 107 tok/s. ETA: ~70h.