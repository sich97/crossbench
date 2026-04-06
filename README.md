# CrossBench: The Ultimate LLM Benchmarking Framework

**CrossBench** is an open-source benchmarking framework designed for high-fidelity performance and quality evaluation of Large Language Models. Built on a philosophy of "Ultimate Simplicity," it replaces complex regex and fragmented configuration files with a streamlined, folder-based approach and a single-field variable engine.

## 🌟 Features

- **Full Context Benchmarking**: Mandatory ~100% context fill for all speed and memory tests
- **Folder-Based Discovery**: Simply drop `.gguf` files into organized folders
- **Peak Memory Monitoring**: Samples VRAM and System RAM every second
- **Override Hierarchy**: Sophisticated variable resolution (Global → Model Group → Backend Group → Backend Version)
- **Quality Metrics**: Built-in support for coding, instruction following, tool use, and long-context reasoning
- **Interactive Web UI**: Explore, filter, and compare results using Streamlit dashboard

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/sich97/crossbench.git
cd crossbench

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `config.yaml` file:

```yaml
# Global variables
variables:
  --ctx-size: [4096, 8192]        # Benchmark these context sizes
  --n-predict: [128]              # Static: generate 128 tokens

# Model groups
model_groups:
  dense_models:
    path: ./models/dense/         # Path to model files
    variables:
      --n-gpu-layers: [-1, 35]    # Benchmark full vs partial GPU offload

  moe_models:
    path: ./models/moe/
    variables:
      --n-cpu-moe: [4, 8, 16]     # Benchmark different CPU MoE layers

# Backend configuration
backends:
  llama.cpp:
    command_template: |
      llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}
    variables:
      --batch-size: [512]
      --flash-attn: [true, false]
```

### Running Benchmarks

```bash
# Run entire benchmark suite
python main.py --config config.yaml --db results.db

# Run specific model group
python main.py --config config.yaml --db results.db --model-group dense_models

# Dry run (print commands without executing)
python main.py --config config.yaml --db results.db --dry-run
```

### Launching Web UI

```bash
# After running benchmarks, launch the interactive dashboard
python main.py --ui --db results.db
```

The Web UI will open at `http://localhost:8501` by default.

## 📊 Methodology

### Full Context Fill Standard

CrossBench rejects partial-context benchmarks. All tests use ~100% of configured context size:

| Metric | Requirement |
| :--- | :--- |
| **Full Context Fill** | Use ~100% of configured `--ctx-size` via tokenizer metadata |
| **TTFT** | Time to First Token at maximum context |
| **TPOT** | Time Per Output Token at maximum context |
| **Peak VRAM** | Maximum VRAM observed (sampled every 1s) |
| **System RAM** | CPU memory usage during max inference |

### Variable Resolution Hierarchy

```
Backend Version (highest priority)
    ↓
Backend Group
    ↓
Model Group
    ↓
Global (lowest priority)
```

**Example:**
| Variable | Global | Backend | Version | **Final Value** |
| :--- | :--- | :--- | :--- | :--- |
| `--ctx-size` | `[4096, 8192]` | - | - | `[4096, 8192]` (Iterate) |
| `--batch-size` | `[512]` | `[2048]` | - | `[2048]` (Static) |
| `--flash-attn` | - | `[true, false]` | `[true]` | `[true]` (Static Override) |

## 🔧 Core Concepts

### One Field Rule

All logic lives in the `variables` field:
- `[value]` (single element) = **Static Parameter** (no iteration)
- `[val1, val2]` (multi-element) = **Benchmark Dimension** (triggers iteration)

### Dynamic Command Construction

Use `{{ benchmark_params }}` placeholder in templates. Adding new variables automatically includes them in CLI commands:

**Template:**
```bash
llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}
```

**Variables:** `{--ctx-size: 8192, --batch-size: 2048, --flash-attn: true}`

**Result:**
```bash
llama-server --port 1234 -m /models/model.gguf --ctx-size 8192 --batch-size 2048 --flash-attn true
```

### Docker-Based Test Isolation

Each test combination runs in a fresh Docker container:
- Models bind-mounted at `/models/model.gguf`
- Container IP auto-detected for API requests
- Automatic cleanup after benchmark completion

## 🗂️ Project Structure

```
crossbench/
├── core/                    # Core logic modules
│   ├── variable_engine.py   # Length-based branching
│   ├── config.py           # YAML parsing & hierarchy resolution
│   ├── cartesian.py        # Multi-value expansion
│   ├── command_builder.py  # Dynamic command construction
│   ├── tokenizer.py        # Full context prompt generation
│   ├── memory_monitor.py   # Peak VRAM/RAM sampling
│   └── model_discovery.py  # Folder-based model discovery
├── execution/              # Benchmark execution
│   ├── docker_runner.py    # Container management
│   └── metrics_collector.py # TTFT, TPOT measurement
├── storage/                # Data persistence
│   ├── database.py         # SQLite schema & queries
│   └── hasher.py           # Config hashing
├── ui/                     # Web interface
│   └── dashboard.py        # Streamlit dashboard
├── models/                 # Model directories
│   ├── dense/
│   └── moe/
├── tests/                  # Test suite
├── config.yaml            # Configuration file
├── main.py                # CLI entry point
└── requirements.txt       # Dependencies
```

## 🧪 Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_variable_engine.py -v
```

## 📈 Web UI Features

- **Overview**: Key metrics summary and data table
- **Comparison Charts**: Interactive bar and scatter plots
- **Individual Runs**: Detailed view of each benchmark
- **Export**: Download results as CSV, Markdown, or PNG

## 🛠️ Extensibility

### Adding New Quality Metrics

1. Add new columns to `benchmarks` table in `storage/database.py`
2. Update `run_benchmark()` in `main.py` to collect new metrics
3. Add UI components in `ui/dashboard.py`

### Adding New Backends

1. Add backend configuration in `config.yaml`
2. Update `command_template` for the new backend
3. Ensure model path is bind-mounted correctly

## 📝 Reproducibility

Every benchmark run stores:
- SHA-256 hash of `config.yaml`
- Actual rendered command executed
- Complete configuration file content
- Hardware metadata (CPU, RAM, GPU)

## 📄 License

This project is open-source. Please refer to the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📞 Support

For issues and feature requests, please open an issue on GitHub.

---

**Built with ❤️ for the LLM benchmarking community**
