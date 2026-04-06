# 🤖 CrossBench Implementation Guide for AI Agents

This document provides specific technical guidance for implementing the **CrossBench** benchmarking framework as defined in the version 6.1 specification. Your goal is to build a lean, automated pipeline that prioritizes the "Ultimate Simplicity" philosophy.

The specification for the framework is defined in SPECIFICATION.md, and you are encouraged to read that before beginning implementing anything.
Remember to regularly check the SPECIFICATION.md to see if your ongoing implementation is in alignment.
When you believe you are finished with the implementation, you **must** analyze the SPECIFICATION.md one last time to verify that you did not miss anything.

---

## 1. The Variable Engine (Core Logic)

The heart of CrossBench is the logic governing the `variables` field. 

### Logic Requirements:
* **Length-Based Branching**: 
    * If `len(list) == 1`: Treat as a **Static Parameter**. It overrides higher-level defaults but does not create new test runs.
    * If `len(list) > 1`: Treat as a **Benchmark Dimension**. This triggers a Cartesian product expansion for the test suite.
* **Resolution Order**: Implement a merge-dictionary function that follows this strict hierarchy (highest priority first):
    1. **Backend Version** variables.
    2. **Backend Group** variables.
    3. **Model Group** variables.
    4. **Global** variables.

> **Agent Note**: Use an established YAML library (like `ruamel.yaml` or `PyYAML`) for parsing. Do not write custom regex parsers for the hierarchy resolution.

---

## 2. Dynamic Command Construction

The framework must transform resolved variables into a CLI string for `llama-server`.

### Implementation Steps:
1. **Placeholder Injection**: Look for the `{{ benchmark_params }}` placeholder in the `command_template`.
2. **String Formatting**: Convert the final resolved variable dictionary into a space-separated string of flags (e.g., `{"--ctx-size": 4096}` becomes `--ctx-size 4096`).
3. **Model Path**: Note that the model path `-m /models/model.gguf` is often hardcoded in the template because it is expected to be bind-mounted via Docker.

---

## 3. High-Fidelity Metric Collection

Accuracy is paramount. You must implement specific measurement behaviors for speed and memory.

### Mandatory Execution Flow:
| Task | Implementation Detail |
| :--- | :--- |
| **Tokenizer Integration** | Use `gguf` library to read the model's internal metadata. You **must** generate a prompt that gets as close as possible to 100% of the `--ctx-size`. |
| **Peak Memory Sampling** | Start a background thread/process that polls VRAM (ROCm) and System RAM **every 1 second** during the entire run. |
| **Record Maximums** | Do not record the final memory state; record the **highest value observed** during the lifecycle of the process. |

---

## 4. Data Architecture & Storage

Use **SQLite** for the results database to ensure portability and simplicity.

### Schema Design Principles:
* **Extensibility**: Use a schema that can accept new columns (like new "Quality" metrics) without breaking existing data.
* **Reproducibility**: Every row in the database must include:
    * The SHA-256 hash of the `config.yaml` used.
    * The **actual rendered command** that was executed.
    * Hardware metadata (GPU type, RAM total, CPU info).

---

## 5. Web UI & Visualization

Do not build a custom front-end from scratch. Use **Streamlit** or **Plotly Dash**.

### Feature Priorities:
1. **Interactive Comparison**: Allow users to select a model and toggle variables (e.g., "Compare Llama-3 with Flash Attention ON vs OFF" or "Compare GPT-OSS on new vs old llama.cpp build" or "Compare Devstral vs GLM 4.7 Flash coding capabilities).
2. **Automatic Detection**: The UI should automatically detect and display new variables added to the database without requiring a code update to the dashboard.
3. **Export Engine**: Implement "Save as Image" and "Export to Markdown/CSV" for every generated chart or table.

---

## 6. Implementation Checklist for Agents

* [ ] Implement folder-based model discovery (ignore non-`.gguf` files).
* [ ] Create the Cartesian product generator for multi-value variables.
* [ ] Write the Docker wrapper to pull and run specific backend versions.
* [ ] Build the 1-second interval memory monitor.
* [ ] Ensure the prompt generator uses model-specific tokenizer logic.

---
**Reference Specification**: `SPECIFICATION.md`
