# Spec 251: vLLM Runtime (Dockerized)

## Scope

`vLLM` is a high-throughput, memory-efficient inference engine. In the AUDiaLLMGateway topology, it is deployed as a **persistent backend container** alongside the swappable `llama.cpp` backend.

## Requirements

- **Deployment Mode**: Docker-only. The host should provide GPU passthrough (NVIDIA Toolkit or ROCm/Vulkan devices).
- **Managed Lifecycle**: Orchestrated via `docker-compose.yml`. 
- **Hot Reload**: LiteLLM configuration is updated when a `vLLM` model is added or changed in the catalog.

## Configuration

### Stack Config (`stack.base.yaml`)

```yaml
component_settings:
  vllm:
    provider: docker
    docker_image: vllm/vllm-openai:latest
```

### Model Catalog (`models.base.yaml`)

Models using the `vllm` framework are routed directly from LiteLLM.

```yaml
model_profiles:
  qwen2.5-72b:
    deployments:
      vllm_high_perf:
        framework: vllm
        transport: direct
        port: 41090
        vllm_options:
          tensor_parallel_size: 2
          gpu_memory_utilization: 0.90
```

## Integration

### Gateway Routing
LiteLLM communicates with `vLLM` using the Docker internal hostname `audia-vllm:8000`
when `AUDIA_ENABLE_VLLM=true`. The generator emits direct LiteLLM routes for
`framework: vllm` / `transport: direct` exposures and writes
`config/generated/vllm/vllm.config.json` for the container entrypoint.

### Health Check
The `audia-watcher` service restarts `backend-vllm` when the generated vLLM config
or relevant env values change. nginx proxies `/vllm/` and `/vllm-health` directly
to the backend when enabled.
