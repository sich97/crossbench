# 📊 CrossBench: Specification Document
**Version:** 6.1 | **Date:** 2026-04-05 | **Status:** `Ready for Implementation`

---

## 1. Executive Summary & Design Philosophy
This framework is designed to be a comprehensive, open-source tool for LLM performance and quality evaluation, prioritizing **simplicity** and **leverage of existing tools**.

### 💡 The "Ultimate Simplicity" Rules
* **Single-Field Variable Logic:** The `variables` field is the only source of truth.
    * `[value]` (Single element) = **Static** (no iteration).
    * `[val1, val2]` (Multi-element) = **Dimensions** (iterate/benchmark).
* **Dynamic Command Construction:** Use the `{{ benchmark_params }}` placeholder to automatically inject all resolved variables. **No template updates required** when adding new parameters.
* **Folder-Based Discovery:** Models are organized manually into directories. The framework discovers `.gguf` files automatically—no complex regex or pattern matching.
* **Leverage, Don't Build:** Use mature libraries for YAML templating, SQLite for storage, and Streamlit/Plotly for the Web UI.

---

## 2. Core Objectives
1.  **Speed**: Measure TTFT, TPOT, and throughput across varying context lengths.
2.  **Memory**: Capture **peak** VRAM/RAM during full-load inference.
3.  **Quality**: Evaluate Coding, Reasoning, and Long-Context (Needle in Haystack) capabilities.
4.  **Reproducibility**: Ensure a single config file defines the entire environment.
5.  **Analytics**: Interactive Web UI for cross-model and cross-backend comparisons.

---

## 3. Speed & Memory Methodology
> **Critical Requirement:** All speed and memory benchmarks must be performed at **100% Context Fill**. Partial context benchmarks are prohibited as they mask performance degradation and peak memory spikes.

### 3.1 Mandatory Metrics
| Metric | Description | Requirement |
| :--- | :--- | :--- |
| **Full Context Fill** | Generate prompt to 100% of configured `--ctx-size`. | ✅ **Mandatory** |
| **TTFT** | Time to First Token at maximum context. | ✅ **Mandatory** |
| **TPOT** | Time Per Output Token at maximum context. | ✅ **Mandatory** |
| **Peak VRAM** | Maximum VRAM observed (sampled every 1s). | ✅ **Mandatory** |
| **System RAM** | CPU memory usage during max inference (read memory usage from docker) | ✅ **Mandatory** |

### 3.2 Quality Evaluation Categories
| Category | Focus Area |
| :--- | :--- |
| **Coding Skill** | Performance across established coding frameworks. |
| **Instruction Following** | Strict adherence to complex prompt constraints. |
| **Tool Use** | Function calling and API integration accuracy. |
| **Long Context** | "Needle in a Haystack" and long-form reasoning. |

---

## 4. Variable Resolution & Hierarchy
The framework follows a strict **Override Cascade**. The most specific definition always wins.

### 4.1 Resolution Precedence
1.  **Backend Version** (Highest - e.g., `v0.36-cuda`)
2.  **Backend Group** (e.g., `llama.cpp`)
3.  **Model Group** (e.g., `moe_models`)
4.  **Global** (Lowest - Default settings)

### 4.2 Resolution Example
| Variable | Global | Backend | Version | **Final Resolved Value** |
| :--- | :--- | :--- | :--- | :--- |
| `--ctx-size` | `[4096, 8192]` | - | - | `[4096, 8192]` (Iterate) |
| `--batch-size` | `[512]` | `[2048]` | - | `[2048]` (Static) |
| `--flash-attn` | - | `[true, false]` | `[true]` | `[true]` (Static Override) |

---

## 5. Command Construction Algorithm
For every model discovered in a folder, the framework executes the following:

1.  **Discover**: Find all `.gguf` files in the group path.
2.  **Collect**: Gather `variables` from all hierarchy levels.
3.  **Merge**: Apply the override cascade (Specific beats General).
4.  **Expand**: Create Cartesian product combinations for all multi-element lists.
5.  **Render**: Construct the `benchmark_params` string and inject it into the `command_template`.

### 🛠️ Example Template Rendering
**Template:**
```bash
llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}
```
**Resulting Command:**
```bash
llama-server --port 1234 -m /models/model.gguf --ctx-size 8192 --batch-size 2048 --flash-attn true
```

---

## 6. Data Storage & Web UI

### 6.1 Results Database (SQLite)
* **Extensible Schema:** Must accept new metrics (e.g., new quality scores) without migrations.
* **Metadata:** Store timestamps, hardware specs, config hashes, and the **actual rendered command** used for the run.
* **Reproducibility:** Every entry must contain a copy of the configuration file that was used.

### 6.2 Interactive Dashboard (Streamlit/Dash)
* **Individual Runs:** Drill down into timeline views of VRAM and TPOT.
* **Comparisons:** * Compare the same model across different variables (e.g., `--flash-attn` on vs off).
    * Compare different models on identical hardware configurations.
* Comparisons must support comparison across seperate benchmark runs
* **Exports:** Support for Markdown, CSV, PNG (charts), and PDF reports.

---

## 7. Docker usage
* **Docker run command:** For each benchmark, a fresh docker container is spawned with the specified image and templated run command
* **Connectivity:** Since container runs on the same host, no port mapping is necessary, but this framework must detect the IP of the spawned container in order to make API requests to its 1234 port
* **RAM usage monitoring:** Docker should provide necessary RAM usage metrics.
* **VRAM usage monitoring:** Docker container comes with rocm-smi in shell, which can be used to extract VRAM usage (but be aware that other processes on the host might use some VRAM in the background as the benchmark begins and that this amount might change during the benchmark)

---

## 8. Implementation Roadmap & Success Criteria

### ✅ Definition of Done
* [ ] **One Field Rule:** All configuration happens inside the `variables` block.
* [ ] **Zero Regex Discovery:** Models are sourced solely via folder organization.
* [ ] **Automatic Parameters:** Adding a new variable to the YAML automatically includes it in the CLI command.
* [ ] **Test isolation:** New docker container per test combination
* [ ] **Peak Monitoring:** VRAM/RAM captured as "Maximum Observed" rather than a final snapshot.
* [ ] **Unified UI:** Results from all backends and models viewable in a single dashboard.

---

## 9. Quick Start Configuration Example
```yaml
# benchmark-config.yaml
variables:
  --ctx-size: [4096, 8192]        # Benchmark these two sizes

model_groups:
  moe_models:
    path: ./models/moe/           # Discovers all .gguf files here
    variables:
      --n-cpu-moe: [4, 8, 16]     # Benchmark these offload levels

llama.cpp:
  command_template: |
    llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}
  variables:
    --batch-size: [2048]          # Static override
    --flash-attn: [true, false]   # Benchmark toggle
```

---
**Document End - Ready for Implementation**
