# 🚀 CrossBench Implementation Plan

## Overview
This plan outlines the step-by-step implementation of CrossBench, a high-fidelity LLM benchmarking framework prioritizing "Ultimate Simplicity."

---

## Phase 1: Project Structure & Foundation

### 1.1 Directory Layout
```
crossbench/
├── core/
│   ├── __init__.py
│   ├── config.py          # YAML parsing and hierarchy resolution
│   ├── variable_engine.py # Length-based branching logic
│   ├── cartesian.py       # Multi-value expansion generator
│   ├── command_builder.py # Dynamic command construction
│   ├── tokenizer.py       # Prompt generation for full context fill
│   └── memory_monitor.py  # 1-second interval VRAM/RAM sampling
├── execution/
│   ├── __init__.py
│   ├── docker_runner.py   # Container spawning and IP detection
│   └── metrics_collector.py # TTFT, TPOT, throughput measurement
├── storage/
│   ├── __init__.py
│   ├── database.py        # SQLite schema and queries
│   └── hasher.py          # SHA-256 config hashing
├── ui/
│   ├── __init__.py
│   └── dashboard.py       # Streamlit interactive dashboard
├── models/                # User model folders (dense/, moe/, etc.)
├── tests/
├── config.yaml            # User configuration file
├── main.py                # CLI entry point
├── requirements.txt
└── README.md
```

### 1.2 Dependencies (requirements.txt)
- `pyyaml` or `ruamel.yaml` (YAML parsing)
- `gguf` or `llama-cpp-python` (tokenizer integration)
- `sqlite3` (built-in)
- `streamlit` + `plotly` (Web UI)
- `docker` (Python SDK for container management)
- `psutil` (system RAM monitoring)

---

## Phase 2: Variable Engine (Core Logic)

### 2.1 Length-Based Branching (`core/variable_engine.py`)
**Goal**: Implement single-field variable logic.

**Implementation Steps**:
1. Create function `is_static_variable(value_list)`:
   - Returns `True` if `len(value_list) == 1`
   - Returns `False` if `len(value_list) > 1` (benchmark dimension)

2. Create function `classify_variables(variable_dict)`:
   - Iterates through all variables
   - Classifies each as `static` or `dimension`
   - Returns two separate dictionaries

**Acceptance Criteria**:
- `[4096]` → static (no iteration)
- `[4096, 8192]` → dimension (triggers Cartesian product)

### 2.2 Hierarchy Resolution (`core/config.py`)
**Goal**: Implement override cascade from Global → Model Group → Backend Group → Backend Version.

**Implementation Steps**:
1. Create `merge_dictionaries(dict_list)` function:
   - Accepts list of dictionaries in order of precedence (highest first)
   - Deep merges dictionaries, with later values overriding earlier ones
   - Returns unified variable dictionary

2. Create `resolve_hierarchy(config)` function:
   - Extracts variables from: backend_version → backend_group → model_group → global
   - Applies merge_dictionaries in order
   - Returns resolved variable set

**Acceptance Criteria**:
- Backend version variables override backend group variables
- Backend group variables override model group variables
- Model group variables override global variables

---

## Phase 3: Cartesian Product Generator

### 3.1 Multi-Value Expansion (`core/cartesian.py`)
**Goal**: Generate all test run combinations from benchmark dimensions.

**Implementation Steps**:
1. Create `generate_combinations(variables_dict)` function:
   - Identifies all dimension variables (len > 1)
   - Uses `itertools.product` to create Cartesian product
   - Returns list of dictionaries, each representing one test run

2. Create `group_static_variables(variables_dict)` function:
   - Separates static variables from dimensions
   - Attaches static variables to each combination

**Acceptance Criteria**:
- Input: `{--ctx-size: [4096, 8192], --flash-attn: [true]}`
- Output: `[{--ctx-size: 4096, --flash-attn: true}, {--ctx-size: 8192, --flash-attn: true}]`

---

## Phase 4: Dynamic Command Construction

### 4.1 Command Builder (`core/command_builder.py`)
**Goal**: Transform resolved variables into CLI string with `{{ benchmark_params }}` injection.

**Implementation Steps**:
1. Create `variables_to_flags(variables_dict)` function:
   - Iterates through variable dictionary
   - Converts `{--ctx-size: 4096}` → `"--ctx-size 4096"`
   - Handles boolean values (`true`/`false`) without values
   - Returns space-separated string

2. Create `render_command(template, variables_dict)` function:
   - Replaces `{{ benchmark_params }}` placeholder with flags string
   - Returns final executable command

**Acceptance Criteria**:
- Template: `"llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}"`
- Variables: `{--ctx-size: 8192, --batch-size: 2048, --flash-attn: true}`
- Result: `"llama-server --port 1234 -m /models/model.gguf --ctx-size 8192 --batch-size 2048 --flash-attn true"`

---

## Phase 5: Tokenizer Integration & Full Context Fill

### 5.1 Prompt Generator (`core/tokenizer.py`)
**Goal**: Generate prompts that fill ~100% of configured context size.

**Implementation Steps**:
1. Create `load_model_metadata(model_path)` function:
   - Uses `gguf` or `llama-cpp-python` library
   - Reads tokenizer vocabulary and context size from model file
   - Returns token ID for common start tokens (e.g., "The")

2. Create `generate_full_context_prompt(ctx_size, model_path)` function:
   - Calculates target token count based on `--ctx-size`
   - Generates repetitive text that tokenizes to target count
   - Returns prompt string for benchmark execution

3. Create `get_token_count(prompt, model_path)` helper:
   - Tokenizes prompt using model's tokenizer
   - Returns actual token count for verification

**Acceptance Criteria**:
- For `--ctx-size 8192`, generates prompt with 8000-8200 tokens
- Prompt uses model-specific tokenizer logic
- Token count verification before execution

---

## Phase 6: Memory Monitoring

### 6.1 Peak Memory Sampler (`core/memory_monitor.py`)
**Goal**: Sample VRAM and System RAM every 1 second, record maximum observed.

**Implementation Steps**:
1. Create `MemoryMonitor` class:
   - Background thread that polls memory every 1 second
   - Maintains `peak_vram`, `peak_system_ram` attributes
   - Starts/stops via `start()` and `stop()` methods

2. Create `get_vram_usage_rocm()` function:
   - Executes `rocm-smi --query-memory-used` via subprocess
   - Parses output to extract VRAM usage in MB
   - Returns current VRAM usage

3. Create `get_system_ram_usage()` function:
   - Uses `psutil` library to read `/proc/meminfo` or `psutil.virtual_memory()`
   - Returns current system RAM usage in MB

4. Create `get_docker_memory_usage(container_id)` function:
   - Executes `docker stats --no-stream --format '{{.MemUsage}}' <container_id>`
   - Parses output to extract memory usage

**Acceptance Criteria**:
- Samples every 1 second during benchmark run
- Records highest VRAM and RAM values observed
- Does not record final snapshot (peak only)

---

## Phase 7: Docker Integration

### 7.1 Container Runner (`execution/docker_runner.py`)
**Goal**: Spawn fresh Docker container per test combination, detect container IP.

**Implementation Steps**:
1. Create `spawn_container(image, command)` function:
   - Uses Python Docker SDK to create and start container
   - Binds model folder to `/models` inside container
   - Executes rendered benchmark command inside container
   - Returns container object with ID

2. Create `detect_container_ip(container)` function:
   - Executes `docker inspect --format '{{ .NetworkSettings.IPAddress }}' <container_id>`
   - Returns container IP for API requests

3. Create `stop_container(container)` function:
   - Gracefully stops and removes container after benchmark

4. Create `extract_metrics_docker(container_id)` function:
   - Runs `docker stats --no-stream` to get RAM usage
   - Runs `rocm-smi` inside container to get VRAM usage

**Acceptance Criteria**:
- Fresh container per test combination
- Container IP detected automatically for API requests
- Models bind-mounted at `/models/model.gguf`
- Container cleaned up after benchmark

---

## Phase 8: Metrics Collection

### 8.1 Benchmark Executor (`execution/metrics_collector.py`)
**Goal**: Measure TTFT, TPOT, throughput at full context.

**Implementation Steps**:
1. Create `measure_ttft(container_ip, prompt)` function:
   - Sends API request to container's 1234 port
   - Records time from request start to first token received
   - Returns TTFT in milliseconds

2. Create `measure_tpot(container_ip, output_tokens)` function:
   - Measures time from first token to last token
   - Divides by number of output tokens
   - Returns TPOT in milliseconds per token

3. Create `calculate_throughput(tpot, ctx_size)` function:
   - Computes tokens per second from TPOT
   - Returns throughput metric

4. Create `run_benchmark(container, command, prompt, variables)` function:
   - Starts memory monitor before execution
   - Executes benchmark command
   - Measures TTFT and TPOT via API
   - Stops memory monitor after completion
   - Returns dictionary of all metrics

**Acceptance Criteria**:
- TTFT measured at full context utilization
- TPOT measured for output tokens
- Memory monitor runs throughout entire benchmark lifecycle
- All metrics recorded with timestamps

---

## Phase 9: Data Storage

### 9.1 Database Schema (`storage/database.py`)
**Goal**: SQLite database with extensible schema for results.

**Implementation Steps**:
1. Create `init_database(db_path)` function:
   - Creates SQLite database if not exists
   - Creates `benchmarks` table with columns:
     - `id` (INTEGER PRIMARY KEY)
     - `config_hash` (TEXT) - SHA-256 of config.yaml
     - `model_path` (TEXT)
     - `model_group` (TEXT)
     - `backend_name` (TEXT)
     - `backend_version` (TEXT)
     - `rendered_command` (TEXT)
     - `variables_json` (TEXT) - JSON of all variables
     - `config_yaml` (TEXT) - Full config file content
     - `ttft_ms` (REAL)
     - `tpot_ms` (REAL)
     - `throughput_toks_s` (REAL)
     - `peak_vram_mb` (REAL)
     - `peak_system_ram_mb` (REAL)
     - `hardware_metadata_json` (TEXT)
     - `timestamp` (DATETIME)

2. Create `insert_benchmark(run_data)` function:
   - Inserts new benchmark result into database
   - Handles JSON serialization of variables and metadata

3. Create `query_benchmarks(filters)` function:
   - Supports filtering by model, backend, variables
   - Returns list of benchmark results

4. Create `get_hardware_metadata()` function:
   - Collects GPU type (ROCm), RAM total, CPU info
   - Returns dictionary for hardware_metadata_json

### 9.2 Config Hasher (`storage/hasher.py`)
**Goal**: Generate SHA-256 hash of config.yaml for reproducibility.

**Implementation Steps**:
1. Create `hash_config(config_path)` function:
   - Reads config.yaml file content
   - Computes SHA-256 hash
   - Returns hexadecimal hash string

**Acceptance Criteria**:
- Same config file always produces same hash
- Hash stored with every benchmark run

---

## Phase 10: Web UI

### 10.1 Streamlit Dashboard (`ui/dashboard.py`)
**Goal**: Interactive exploration and comparison of benchmark results.

**Implementation Steps**:
1. Create `load_data_from_database()` function:
   - Queries all benchmarks from SQLite
   - Returns pandas DataFrame

2. Create `get_all_variable_names(df)` function:
   - Extracts unique variable names from `variables_json` column
   - Returns list of all variables ever used

3. Create `filter_dataframe(df, filters)` function:
   - Filters by model, backend, variable values
   - Returns filtered DataFrame

4. Create `comparison_chart(df, x_var, y_var, group_by)` function:
   - Uses Plotly to create bar/line chart
   - X-axis: selected variable (e.g., --ctx-size)
   - Y-axis: selected metric (e.g., TPOT)
   - Grouped by: model or backend

5. Create `individual_run_view(run_id)` function:
   - Shows timeline view of VRAM and TPOT
   - Displays full rendered command
   - Shows hardware metadata

6. Create `export_functions(df)` functions:
   - `export_to_csv(df, path)` - Save as CSV
   - `export_to_markdown(df, path)` - Generate report
   - `save_chart_as_png(fig, path)` - Save Plotly chart

**Acceptance Criteria**:
- Automatic detection of new variables (no code update needed)
- Cross-run comparison support
- Export to Markdown, CSV, PNG, PDF

---

## Phase 11: Model Discovery

### 11.1 Folder-Based Discovery
**Goal**: Automatically find `.gguf` files in model folders.

**Implementation Steps**:
1. Create `discover_models(group_path)` function:
   - Scans directory for `.gguf` files
   - Ignores non-`.gguf` files
   - Returns list of model file paths

2. Create `get_model_metadata(model_path)` function:
   - Reads model name from filename
   - Extracts architecture info from GGUF metadata
   - Returns model information dictionary

**Acceptance Criteria**:
- No regex or pattern matching required
- Simple folder organization (dense/, moe/, etc.)
- Only `.gguf` files discovered

---

## Phase 12: CLI Entry Point

### 12.1 Main Runner (`main.py`)
**Goal**: Command-line interface to orchestrate entire benchmark pipeline.

**Implementation Steps**:
1. Create `parse_args()` function:
   - `--config` (path to config.yaml)
   - `--db` (path to SQLite database)
   - `--ui` (flag to launch Web UI)
   - `--model-group` (optional filter)

2. Create `run_benchmarks(config_path, db_path)` function:
   - Loads and parses config.yaml
   - Discovers models in all model_groups
   - For each model:
     - Resolves variable hierarchy
     - Generates Cartesian product combinations
     - For each combination:
       - Renders command
       - Spawns Docker container
       - Generates full context prompt
       - Runs memory monitor
       - Measures TTFT/TPOT
       - Stores results in database
       - Cleans up container

3. Create `launch_ui(db_path)` function:
   - Starts Streamlit server
   - Points to specified database

**Acceptance Criteria**:
- Single command runs entire benchmark suite
- CLI supports launching Web UI
- Progress reporting during execution

---

## Phase 13: Testing & Validation

### 13.1 Test Suite
**Goal**: Ensure correctness of all components.

**Implementation Steps**:
1. Create `tests/test_variable_engine.py`:
   - Test length-based branching
   - Test hierarchy resolution

2. Create `tests/test_cartesian.py`:
   - Test Cartesian product generation
   - Test static variable grouping

3. Create `tests/test_command_builder.py`:
   - Test variable-to-flags conversion
   - Test template rendering

4. Create `tests/test_tokenizer.py`:
   - Test prompt generation for various context sizes
   - Test token count verification

5. Create `tests/test_memory_monitor.py`:
   - Test peak memory recording
   - Test sampling interval

6. Create `tests/test_database.py`:
   - Test insert and query operations
   - Test schema extensibility

---

## Implementation Order Summary

1. **Week 1**: Project structure, variable engine, hierarchy resolution
2. **Week 2**: Cartesian product, command builder, tokenizer integration
3. **Week 3**: Memory monitor, Docker integration, metrics collection
4. **Week 4**: Database schema, config hasher, model discovery
5. **Week 5**: Streamlit dashboard, export functions
6. **Week 6**: CLI entry point, integration testing, documentation

---

## Success Criteria Checklist

- [x] **One Field Rule**: All configuration inside `variables` block
- [x] **Zero Regex Discovery**: Models sourced via folder organization
- [x] **Automatic Parameters**: Adding new variable auto-includes in CLI command
- [x] **Test Isolation**: Fresh Docker container per test combination
- [x] **Peak Monitoring**: VRAM/RAM captured as "Maximum Observed"
- [x] **Unified UI**: Results from all backends viewable in single dashboard
- [x] **Full Context Fill**: All benchmarks use ~100% context utilization
- [x] **Reproducibility**: Config hash and rendered command stored with every run

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Docker SDK compatibility issues | Use official Python Docker SDK, test on target platform |
| ROCm VRAM monitoring unreliable | Fall back to system RAM monitoring if ROCm unavailable |
| Tokenizer library incompatibility | Support both `gguf` and `llama-cpp-python` libraries |
| Streamlit performance with large datasets | Implement pagination and server-side filtering |
| Container IP detection delays | Add retry logic with exponential backoff |

---

## Notes for Implementation

1. **Start Simple**: Implement variable engine and command builder first, then add complexity
2. **Test Early**: Write tests for each component as you build it
3. **Use Established Libraries**: Don't reinvent YAML parsing or SQLite handling
4. **Document Assumptions**: Clearly document any platform-specific assumptions (e.g., ROCm requirement)
5. **Iterate on UI**: Get basic functionality working before polishing the dashboard
