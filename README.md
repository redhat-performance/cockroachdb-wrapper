# CockroachDB Benchmark Wrapper

## Description

This wrapper facilitates the automated execution of CockroachDB benchmarks using the `cockroach workload` tool. CockroachDB is used here as a system-level benchmark that stresses CPU, memory, kernel scheduler, and storage subsystems by driving SQL workloads against a single-node cluster. The primary metric is operations per second (ops/sec).

The wrapper provides:
- Automated CockroachDB binary download and execution.
- Support for x86_64 and aarch64 architectures.
- Configurable workloads (KV and MoVR) with adjustable concurrency, duration, and ramp time.
- Configurable CockroachDB version selection.
- Multi-iteration testing with trimmed mean and deviation calculation.
- Result collection, processing, and verification.
- CSV and JSON output formats.
- System configuration metadata capture.
- Integration with test_tools framework.
- Optional Performance Co-Pilot (PCP) integration.

## Command-Line Options

```
CockroachDB Wrapper Options:
  --cockroach_version <value>: CockroachDB version to download (e.g., "v24.3.33").
      Defaults to v22.2.0.  Versions >= v23.2 require x86-64-v2 CPU support.
  --concurrency <value>: Comma-separated list of concurrency levels to test
      (e.g., "128,256,512,1024").  Defaults to 128,256,512,1024.
  --duration <value>: How long each workload runs (e.g., "90s", "120s").
      Defaults to 90s.
  --opts_file <path>: Workload configuration file to use.
      Defaults to test_opts in the script directory.
  --ramp <value>: Ramp-up period before measurement begins (e.g., "10s").
      Defaults to 10s.

General test_tools options:
  --debug: Enables bash -x output, useful for debugging issues with wrappers.
  --home_parent <value>: Parent home directory. If not set, defaults to current working directory.
  --host_config <value>: Host configuration name, defaults to current hostname.
  --iterations <value>: Number of times to run the test, defaults to 1.
  --run_user: User that is actually running the test on the test system. Defaults to current user.
  --sys_type: Type of system working with (aws, azure, hostname). Defaults to hostname.
  --sysname: Name of the system running, used in determining config files. Defaults to hostname.
  --tuned_setting: Used in naming the results directory. For RHEL, defaults to current active tuned profile.
      For non-RHEL systems, defaults to 'none'.
  --use_pcp: Enable Performance Co-Pilot monitoring during test execution.
  --tools_git <value>: Git repo to retrieve the required tools from.
      Default: https://github.com/redhat-performance/test_tools-wrappers
  --usage: Display this usage message.
```

## What the Script Does

The `cockroachdb_run` script performs the following workflow:

1. **Environment Setup**:
   - Clones the test_tools-wrappers repository if not present (default: ~/test_tools).
   - Tries wget, then curl, then git clone to obtain the tools.
   - Sources error codes and general setup utilities.
   - Gathers system hardware information.

2. **Package Installation**:
   - Installs required dependencies via package_tool: bc, zip.
   - Dependencies are defined in cockroachdb.json for different OS variants (RHEL, Ubuntu, SLES, Amazon Linux).

3. **CockroachDB Installation**:
   - Downloads the CockroachDB binary tarball from `binaries.cockroachdb.com`.
   - Selects the correct binary for the system architecture (x86_64 or aarch64).
   - Extracts the binary to `cockroach-build/` in the script directory.
   - Skips download if the binary is already present.

4. **PCP Setup** (optional):
   - If `--use_pcp` is specified, initializes Performance Co-Pilot monitoring.
   - Creates a timestamped PCP data directory at `/tmp/pcp_<timestamp>/`.
   - Resets all OpenMetrics values between workload runs.

5. **Test Execution**:
   - Reads the test configuration file (`test_opts` by default) line by line.
   - Each line defines a workload name and corresponding `cockroach workload run` flags.
   - For each workload and concurrency level:
     - Starts a fresh CockroachDB single-node insecure cluster on localhost.
     - Runs the workload with configured duration and ramp time.
     - Parses ops/sec(cum) from the final summary line of the workload output.
     - Stops CockroachDB and removes the data directory.
   - Records start and end timestamps for each workload run.
   - Runs each configuration for the specified number of iterations (`--iterations`).

6. **Data Collection**:
   - Extracts ops/sec from each run's raw output.
   - Generates per-iteration CSV files (`cockroachdb_iter_N.csv`) with system metadata header.
   - Optionally records PCP performance data (iteration, concurrency, average).

7. **Verification**:
   - Converts CSV to JSON via `csv_to_json`.
   - Validates results against Pydantic schema (`result_schema.py`) ensuring:
     - All workload names match expected Workload enum values.
     - All Average values are valid floats.
     - Timestamps are valid datetime objects.

8. **Combined Report**:
   - Generates `results_cockroachdb.csv` combining all iterations.
   - Computes average ops/sec across iterations for each workload+concurrency combination.
   - For 5 or more iterations, applies trimmed mean (drops highest and lowest values).
   - Computes deviation as a percentage (standard deviation / average x 100).
   - Includes system metadata header, timestamps, and all result fields.

9. **Output**:
   - Creates timestamped results directory in `${HOME}/export_results/cockroachdb_<YYYY.MM.DD-HH.MM.SS>`.
   - Saves all raw output files, processed CSV/JSON, and system metadata.
   - Optionally saves PCP performance data.
   - Archives results to configured storage location.

## Dependencies

Location of underlying workload: Downloaded from https://binaries.cockroachdb.com.

**General packages required**: bc, zip

To run:
```bash
git clone https://github.com/redhat-performance/cockroachdb-wrapper
cd cockroachdb-wrapper/cockroachdb
./cockroachdb_run
```

The script will automatically detect your CPU architecture and download the appropriate CockroachDB binary.

## The CockroachDB Benchmark

CockroachDB is a distributed SQL database. In this wrapper it is used as a system-level benchmark, not a database benchmark. A single-node insecure cluster runs on localhost and workloads drive SQL operations to stress the system.

### Workloads

The default `test_opts` file defines 5 workload configurations:

**KV Workloads** create a table `kv (k BIGINT PRIMARY KEY, v BYTES)` and run concurrent `SELECT` and `UPSERT` operations with configurable read/write ratios:

| Name | Description |
|------|-------------|
| kv_95pct_reads | KV workload with 95% reads, 5% writes |
| kv_50pct_reads | KV workload with 50% reads, 50% writes |
| kv_60pct_reads | KV workload with 60% reads, 40% writes |
| kv_10pct_reads | KV workload with 10% reads, 90% writes |

**MoVR Workload** simulates a ride-sharing application with 6 tables (users, vehicles, rides, promo_codes, user_promo_codes, vehicle_location_histories):

| Name | Description |
|------|-------------|
| movr | MoVR ride-sharing simulation workload |

### Key Parameters

1. **Concurrency**: Number of concurrent worker goroutines driving SQL operations. Default levels: 128, 256, 512, 1024. Higher concurrency stresses the system more heavily.

2. **Duration**: How long each workload runs after the ramp-up period. Default: 90 seconds.

3. **Ramp**: Warm-up period before measurement begins. Default: 10 seconds. Operations during ramp are not counted in the final ops/sec metric.

4. **Performance Metric**: The primary metric is **ops/sec(cum)** — cumulative operations per second over the measurement period. Higher values indicate better system throughput.

### CockroachDB Version Compatibility

- **v22.2.0** (default): Works on all platforms. Requires glibc >= 2.17, no special CPU instruction requirements.
- **v23.2+**: Requires **x86-64-v2** CPU support (SSE4.2, SSSE3, POPCNT). All modern CPUs (Intel 3rd gen+, AMD Ryzen+) support this, but older hardware will fail with `Fatal glibc error: CPU does not support x86-64-v2`.

## Output Files

The results directory contains:

- **results_cockroachdb.csv**: Combined CSV with system metadata, averaged results, and deviation across iterations.
- **cockroachdb_iter_N.csv**: Per-iteration CSV with individual workload results and timestamps.
- **raw_\<workload\>_c\<concurrency\>_iter\<N\>.out**: Raw output from each `cockroach workload run` invocation.
- **cockroach_start.log**: CockroachDB server startup log.
- **meta_data*.yml**: System metadata (CPU info, memory, NUMA topology, kernel version).
- **PCP data** (if `--use_pcp` option used): Performance Co-Pilot monitoring data.

## Examples

### Basic run with defaults
```bash
./cockroachdb_run
```
This runs with:
- CockroachDB v22.2.0
- All 5 workloads from test_opts
- Concurrency levels 128, 256, 512, 1024
- 90 second duration with 10 second ramp
- 1 iteration

### Quick test run
```bash
./cockroachdb_run --concurrency "128" --duration 10s --ramp 5s
```
Runs all workloads at a single concurrency level with short duration for quick validation.

### Run with a newer CockroachDB version
```bash
./cockroachdb_run --cockroach_version v24.3.33
```
Downloads and uses CockroachDB v24.3.33 instead of the default v22.2.0.

### Run multiple iterations
```bash
./cockroachdb_run --iterations 3
```
Runs the full test 3 times and averages results with deviation calculation.

### Run multiple iterations with trimmed mean
```bash
./cockroachdb_run --iterations 5
```
Runs 5 iterations. The highest and lowest values are dropped before averaging (trimmed mean).

### Run with PCP monitoring
```bash
./cockroachdb_run --use_pcp
```
Collects Performance Co-Pilot data during the run.

### Run with debug output
```bash
./cockroachdb_run --debug --concurrency "128" --duration 10s --ramp 5s
```
Enables bash -x output for troubleshooting.

### Combination example
```bash
./cockroachdb_run --cockroach_version v24.3.33 --concurrency "128,256" --duration 60s --iterations 3 --use_pcp
```
Uses CockroachDB v24.3.33, runs 2 concurrency levels, 60 second duration, 3 iterations, with PCP monitoring.

## How Result Averaging Works

The script computes combined results across multiple iterations:

### Average (ops/sec)
1. Collects ops/sec values from each iteration for every workload+concurrency combination.
2. For fewer than 5 iterations: computes a simple arithmetic mean.
3. For 5 or more iterations: applies a **trimmed mean** — drops the highest and lowest values, then averages the remaining samples. This reduces the impact of outliers.

### Deviation
1. Computes standard deviation across all iteration values.
2. Expresses deviation as a percentage of the average: `(stddev / average) x 100`.
3. For single-iteration runs, deviation is 0.
4. Low deviation (< 2%) indicates consistent, reliable results. High deviation suggests system instability or interference from other workloads.

## Return Codes

The script uses standardized error codes from test_tools error_codes:
- **0**: Success
- **101**: Git clone failure (test_tools)
- **102**: CockroachDB binary download failure
- **103**: CockroachDB failed to start

Exit codes indicate specific failure points for automated testing workflows.

## Notes

### Architecture Support
- **x86_64**: Full support. Default binary from `cockroach-<version>.linux-amd64.tgz`.
- **aarch64**: Full support. Uses `cockroach-<version>.linux-3.7.10-gnu-aarch64.tgz`.

### CockroachDB Cluster Configuration
- Runs in **single-node insecure mode** on localhost (127.0.0.1:26257).
- Uses 25% of system memory for CockroachDB cache (`--cache .25`).
- Data directory is created and destroyed for each workload+concurrency combination to ensure a clean state.
- HTTP admin UI is available on port 8080 during test runs.

### Workload Configuration
- Custom workloads can be defined by creating a new test_opts file and using `--opts_file`.
- Each line format: `workload_name,cockroach workload run flags`
- The `--drop` flag is always passed to workload run, which drops and recreates the workload database each time.

### Performance Tips
- Run multiple iterations to verify consistency and get meaningful deviation values.
- Ensure the system is idle (no other workloads) for best results.
- For production benchmarking, use 5+ iterations to enable trimmed mean.
- Consider the active tuned profile on RHEL systems.
- Higher concurrency levels may be limited by available CPU cores.

### Troubleshooting
- If CockroachDB fails to start, check `cockroach_start.log` for errors.
- If download fails, verify internet access to `binaries.cockroachdb.com`.
- If ops/sec is 0, check raw output files for workload errors.
- If using v23.2+, verify CPU supports x86-64-v2 instructions.
- Use `--debug` to enable bash -x output for detailed execution tracing.
- If `save_results` fails, ensure `zip` is installed.
