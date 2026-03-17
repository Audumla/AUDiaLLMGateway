# Spec 251: vLLM Runtime

## Scope

`vLLM` is a high-throughput, memory-efficient inference engine for LLMs. It should be supported as an alternative or parallel backend to `llama.cpp`. Unlike `llama.cpp` which is managed via `llama-swap` for model residency and swapping, `vLLM` is typically deployed as a long-lived service for a specific model or model set.

## Requirements

- **Model Compatibility**: Support for HF-style models that `vLLM` can serve directly.
- **Hardware Support**: First-tier support for NVIDIA GPUs via CUDA, AMD GPUs via ROCm, and generic GPU acceleration via Vulkan (where supported by `vLLM`).
- **Managed Lifecycle**: The `AUDiaLLMGateway` orchestrator should be able to start and stop `vLLM` instances.
- **Configurable Runtime**: Parameters such as `tensor_parallel_size`, `max_model_len`, `quantization`, and `gpu_memory_utilization` should be configurable per deployment.
- **LiteLLM Integration**: LiteLLM should route to `vLLM` instances as OpenAI-compatible endpoints.
- **Shared Catalog**: `vLLM` deployments should be defined within the existing `models.base.yaml` structure.

## Configuration

### Stack Config (`stack.base.yaml`)

A new `vllm` section should be added to the stack configuration to manage global `vLLM` settings, such as the default executable path or Docker image.

```yaml
vllm:
  executable: python -m vllm.entrypoints.openai.api_server
  # or via docker
  # docker_image: vllm/vllm-openai:latest
```

### Model Catalog (`models.base.yaml`)

`vLLM` deployments will use the `vllm` framework.

```yaml
model_profiles:
  qwen2.5-72b:
    deployments:
      vllm_cuda:
        framework: vllm
        transport: direct
        backend_model_name: Qwen/Qwen2.5-72B-Instruct
        port: 8001
        vllm_options:
          tensor_parallel_size: 2
          max_model_len: 32768
          gpu_memory_utilization: 0.95
      vllm_rocm:
        framework: vllm
        transport: direct
        backend_model_name: Qwen/Qwen2.5-72B-Instruct
        port: 8002
        vllm_options:
          tensor_parallel_size: 4
          max_model_len: 32768
          gpu_memory_utilization: 0.90
          device: rocm
      vllm_vulkan:
        framework: vllm
        transport: direct
        backend_model_name: Qwen/Qwen2.5-72B-Instruct
        port: 8003
        vllm_options:
          max_model_len: 32768
          gpu_memory_utilization: 0.85
          device: vulkan
```

## Integration

### Orchestrator (`process_manager.py`)

The orchestrator must be extended to:
- Detect `vllm` deployments in the active load groups.
- Start `vLLM` server processes with the specified options and ports.
- Wait for `vLLM` health/readiness before signaling stack readiness.
- Properly terminate `vLLM` processes during stack shutdown.

### Configuration Generator (`config_loader.py`)

The generator must be updated to:
- Include `vLLM` upstreams in the generated LiteLLM config.
- Map logical model names to the specific `vLLM` endpoint for that model.
- Handle `transport: direct` deployments where LiteLLM talks directly to the inference server (bypassing `llama-swap`).

### Reverse Proxy (`nginx.conf`)

If enabled, Nginx should include upstreams for any active `vLLM` instances to provide a unified front-door for all backends.
