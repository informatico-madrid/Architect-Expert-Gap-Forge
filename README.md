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

---

## 🛠️ Roadmap

- [x] **Phase 1: Infrastructure.** Stable Blackwell vLLM stack with sm_120 support.
- [ ] **Phase 2: Data Synthesis.** Current focus: Generating 1,000+ trajectories for Agentic SFT.
- [ ] **Phase 3: Expert SFT.** Fine-tuning Qwen3-30B-MoE using specialized loss-masking.
- [ ] **Phase 4: Validation.** Public release of the Home Assistant Expert Model.

---

## Technical Implementation of the Synthesis Loop

La "Synthesis Loop" implementada en `production_v9.py` actúa como el núcleo del pipeline de síntesis y curación. El proceso itera sobre los ficheros fuente, aplica un preprocesado de chunking y genera trayectorias de entrenamiento mediante llamadas al cliente de modelo remoto; el `system_prompt` inyecta tanto el `MASTER_GUIDE` como el `TECHNICAL_CHANGELOG` para forzar al agente a razonar explícitamente sobre deltas temporales (contraste entre versión vieja y nueva) antes de producir una acción de escritura.

Para el chunking de código se emplea el módulo `ast` de Python: la función `get_fragments` parsea el contenido con `ast.parse`, extrae imports y definiciones top‑level (incluyendo `AsyncFunctionDef`) y construye skeletons en los que los cuerpos se sustituyen por placeholders. Cada fragmento viene acompañado de metadatos (`context`, `skeleton`, `original`, `virtual_filename`) que permiten generar implementaciones coherentes con el mínimo contexto necesario.

La integración de las etiquetas de razonamiento de Qwen3 se realiza mediante un formato híbrido controlado: el sistema exige que el agente coloque su razonamiento en la etiqueta `<think>` y la acción resultante en `<write_action>` (o `<tool_call>` para compatibilidad con el paso de gold injection). La función `parse_raw_response` extrae de forma robusta el bloque de razonamiento y el contenido final; posteriormente se valida la densidad lógica (LDI) y se aplica un bucle de reintentos (`MAX_RETRIES`) antes de aceptar la muestra. Este diseño asegura trazabilidad entre el razonamiento arquitectónico y el código final generado, facilitando auditoría y curación automática.

## 📄 License
Apache License 2.0.

---
**Lead Architect:** [Joao Maria Arranz Aparicio / informatico-madrid](https://github.com/informatico-madrid)  
**Location:** Spain - Sovereign AI Infrastructure.

## Current Status

Generating 1,000+ samples. Avg speed 107 tok/s. ETA: ~70h.