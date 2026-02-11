# AEGF Methodology: High-Fidelity Synthetic Data & Temporal Alignment
**Technical Whitepaper - Blackwell AI Factory V18.0**

## 1. The Gold-to-Platinum Synthesis Loop

### 1.1. Recursive AST Ingestion (V17.6)
AEGF utilizes **Recursive Abstract Syntax Tree (AST) Ingestion** to maintain architectural integrity. Unlike basic RAG, our pipeline parses the source code to identify:
- **AsyncFunctionDef:** Crucial for modern HA asynchronous patterns.
- **Nested Context:** V17.6 explicitly captures async definitions within complex class structures (Coordinators/Platforms).
- **Skeleton Extraction:** Bodies are replaced by high-seniority placeholders, forcing the model to derive the architecture from signatures and imports.

### 1.2. Inverse-Instruct Strategy (Gold Injection)
To eliminate "Architectural Hallucinations," we use a **Ground-Truth Injection** mechanism:
1. The model generates the architectural reasoning (`<think>`).
2. The pipeline discards the model-generated code.
3. It injects the original, verified **Gold Code** from the repository into the final record.
*Outcome: The model learns the exact cognitive path required to reach production-grade implementations.*

---

## 2. Proprietary Metrics & Quality Control

### 2.1. Dynamic Logic Density Index (LDI)
We apply a **Dynamic Saturation Curve (K-Factor = 1200)** to solve the length-bias problem in dataset curation:
$$Threshold = BASE\_THRESHOLD \times \left( \frac{Length(Code)}{Length(Code) + 1200} \right)$$
This allow us to process high-value "Micro-Snippets" (constants, setups) while strictly auditing large files for meta-speech and hallucinations.

### 2.2. Temporal Contextualization (The Gap Bridge)
We mitigate the "Knowledge Cutoff" by injecting the **HA_MASTER_GUIDE_2026** as a **Future Truth Anchor**. This forces the agent into "Controlled Cognitive Dissonance," auditing 2024 code through 2026 laws:
- **Pluralization Law:** Mandatory migration to `async_forward_entry_setups`.
- **Runtime_Data Mandate:** Enforced strict typing via `ConfigEntry[Data]`.

---

## 3. Hardware & Training Specs

### 3.1. Blackwell Optimization (sm_120)
- **Engine:** vLLM in Raw Output mode with **Tensor Parallelism 2 (TP=2)**.
- **Throughput:** 110.1 tokens/s (Stable) on 30B MoE models.
- **Prefix Caching:** 93.7% Cache Hit Rate using static Master Contexts.

### 3.2. Selective Loss Masking
During the SFT phase, we apply **Gradient Isolation**:
- **Active Gradients:** Only calculated on `<think>` and `<tool_call>` tags.
- **Masked Context:** Master Guides and Changelogs are masked (0 gradient), preventing rote memorization and favoring rule-based reasoning.