# Running Validation and Benchmarking Locally and in Docker

This guide explains how to execute the AUDiaLLMGateway test suite, the
end-to-end validation flow, and the separate benchmarking capability. The
project uses `pytest` for unit testing, a custom `smoke_runner.py` for
integration validation, and dedicated benchmark runners for throughput and lane
comparison.

---

## 1. Running Python Unit Tests Locally

Unit tests verify configuration generation, routing logic, and core utilities without requiring a full environment boot.

### Prerequisites
Ensure your local Python environment (3.11+) is active and dependencies are installed:
```bash
pip install -r requirements.txt
pip install pytest
```

### Execute Unit Tests
Run the main test suite, ignoring the Docker-specific CI directories:
```bash
PYTHONPATH=. pytest tests/ -v --ignore=tests/docker
```

To run the monitoring API specific tests:
```bash
PYTHONPATH=. pytest src/monitoring/tests/ -v --tb=short
```

---

## 2. Running the System Validation Smoke Test

The gateway includes an end-to-end validation script (`scripts/smoke_runner.py`).
This script provisions the environment, generates configurations, boots the
`llama-swap` and `litellm` servers, and verifies that HTTP routing works
correctly.

### Run the Smoke Test
```bash
python scripts/smoke_runner.py
```

*Note: The smoke validation runs in stages. It resolves binaries, generates
configs, starts the servers on temporary ports, validates `/v1/models`
routing, and then safely shuts down the processes.*

---

## 3. Running Benchmarks

Benchmarking is not a test. It is a first-class gateway capability that measures
throughput, route overhead, and backend device behavior for a pinned build or
deployment profile.

### Version Benchmark Catalog

Run the reusable benchmark surface that tracks versions, settings profiles, and
route metrics across history:

```bash
python scripts/run_version_benchmarks.py
```

The benchmark catalog writes:
- `test-work/version-benchmarks/benchmark_metrics.md`
- `test-work/version-benchmarks/benchmark_metrics.json`
- historic copies alongside the current report

### Validation Matrix Benchmarks

Run the config-driven validation matrix across every target that matches the
current platform:

```bash
python scripts/run_backend_validation_matrix.py
```

Add `--include-experimental` to include forked lanes such as
`native-vulkan-turboquant`.

---

## 4. Running Tests in Docker (CI Parity)

If you want to validate exactly what the GitHub Actions CI pipeline runs, you can execute the Docker-based tests locally.

### Distro-Specific Smoke Tests
The project tests installation across multiple Linux distributions (Ubuntu, Debian, Fedora, Rocky, Tumbleweed). To test one locally (e.g., Ubuntu):

```bash
docker build -f tests/docker/Dockerfile.ubuntu -t audia-smoke-ubuntu .
docker run --rm audia-smoke-ubuntu
```

### End-to-End (E2E) Mock Test
This test builds a full gateway routing environment using a mocked `llama-swap` backend to ensure reverse proxy and LiteLLM configurations work.

```bash
docker build -f tests/docker/Dockerfile.e2e -t audia-e2e .
docker run --rm audia-e2e
```

### Real Inference Integration Test
This test pulls a tiny model (e.g., SmolLM2-135M) and runs actual inference through the containerized gateway.

```bash
# Ensure the model directory exists
mkdir -p test-work/models

# Build the integration image
docker build --network=host -f tests/docker/Dockerfile.integration -t audia-integration .

# Run the integration test
docker run --rm \
  -v "$(pwd)/test-work/models:/models" \
  -e MODEL_DIR=/models \
  -e LITELLM_MASTER_KEY=sk-ci-test \
  audia-integration
```

---

## 5. GitHub Actions CI

The full test suite runs automatically via GitHub Actions (`.github/workflows/tests.yml`). The CI pipeline includes:
1. **Pytest**: Validates all Python logic.
2. **Smoke Validation**: Validates installation across 5 different Linux distributions.
3. **E2E Mock**: Verifies container routing.
4. **Integration**: Performs a real inference validation (runs weekly or upon manual dispatch).
5. **Docker Build**: Validates that all production Dockerfiles (`gateway`, `unified-backend`, `vllm`, `monitoring`) compile successfully.
