# CrossBench: The Ultimate LLM Benchmarking Framework

**CrossBench** is an open-source benchmarking framework designed for high-fidelity performance and quality evaluation of Large Language Models. Built on a philosophy of "Ultimate Simplicity," it replaces complex regex and fragmented configuration files with a streamlined, folder-based approach and a single-field variable engine.

---

## 💡 The "Ultimate Simplicity" Philosophy

CrossBench is built to get out of your way so you can focus on the data. Its design is guided by three core rules:

* **ONE Field Only**: All logic lives in the `variables` field—no separate "benchmark_variables" or "static_params" required.
* **Length-Driven Behavior**: A single-element list `[value]` is static; a multi-element list `[val1, val2]` automatically becomes a benchmark dimension to iterate over.
* **Dynamic Command Construction**: Use the `{{ benchmark_params }}` placeholder in your templates. As you add new variables to your config, they are automatically injected into the execution command without needing template updates.

---

## 🚀 Key Features

* **Full Context Benchmarking**: Mandatory 100% context fill for all speed and memory tests to reveal true performance degradation and peak memory spikes.
* **Folder-Based Discovery**: Simply drop your `.gguf` files into organized folders (e.g., `/dense` or `/moe`); the framework discovers them automatically.
* **Peak Memory Monitoring**: Samples VRAM and System RAM every second to capture the maximum value observed, ensuring you see the true peak during initialization and KV cache allocation.
* **Override Hierarchy**: Sophisticated variable resolution that cascades from Global → Model Group → Backend Group → Backend Version.
* **Quality Metrics**: Built-in support for evaluating coding skill, instruction following, tool use, and long-context reasoning (Needle in a Haystack).
* **Interactive Web UI**: Explore, filter, and compare results across different models and parameters using a pre-built dashboard.

---

## 🛠️ Quick Start Configuration

Define your entire benchmark suite in one simple YAML file:

```yaml
variables:
  --ctx-size: [4096, 8192]        # Benchmark these two sizes
  --batch-size: [512]             # Static default

model_groups:
  dense_models:
    path: ./models/dense/         # Automatically benchmarks all .gguf files here
    variables:
      --n-gpu-layers: [-1, 35]    # Benchmark full vs partial offload

llama.cpp:
  command_template: |
    llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}
  variables:
    --flash-attn: [true, false]   # Benchmark with and without Flash Attention
```

---

## 📊 Methodology: The "Full Fill" Standard

CrossBench rejects partial-context benchmarks as they often mask the memory and performance characteristics of production-ready models.

| Metric | Requirement |
| :--- | :--- |
| **Full Context Fill** | Use 100% of configured context size via tokenizer metadata. |
| **TTFT/TPOT** | Measured specifically at full context utilization. |
| **Peak VRAM/RAM** | Maximum memory observed during the entire run. |
| **Scaling** | Automatically measures performance degradation from partial to full context. |

---

## 🖥️ Exploration & Export

Once your runs are complete, use the integrated Web UI to dive into the data:

* **Interactive Filtering**: Select specific variables to build custom comparison charts.
* **Cross-Run Analysis**: Compare the same model across different backends or parameter combinations.
* **Flexible Export**: Generate reports in Markdown, CSV, PNG, or professional PDF formats for sharing results.
