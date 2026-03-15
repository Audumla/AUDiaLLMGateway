# Troubleshooting

## Update preserved my local config but something broke

- Run `.\scripts\AUDiaLLMGateway.ps1 validate-configs`
- Inspect `state/install-state.json`
- Review type conflict warnings for `config/local/*.yaml`
- Regenerate config outputs with `.\scripts\AUDiaLLMGateway.ps1 generate-configs`

## Release installer failed to install a dependency

- Check whether the host package manager exists:
  - Windows: `winget`
  - Linux: `apt-get` or `dnf`
  - macOS: `brew`
- If automatic install is unavailable, install the missing dependency manually and rerun the installer or update.

## llama-swap does not start after update

- Confirm `LLAMA_SWAP_EXE` still points to the correct executable.
- Confirm the installed `llama.cpp` build in `state/install-state.json` matches the backend you expect.
- Confirm your local overrides did not introduce a type mismatch in `config/local/llama-swap.override.yaml`.
- Inspect `.runtime/logs/llama-swap.log`.

## The wrong llama.cpp build was installed

- Check `component_settings.llama_cpp` in `config/project/stack.base.yaml`.
- Override the version/backend in `config/local/stack.override.yaml`.
- Re-run the update flow.
- Inspect `state/install-state.json` for the resolved asset and executable path.

## The Windows HIP/ROCm build needs extra DLLs

- Add those DLLs to `component_settings.llama_cpp.sidecar_files` in `config/local/stack.override.yaml`.
- Re-run the update flow so the installer copies them next to the selected `llama-server` binary.
- Inspect `state/install-state.json` to confirm which sidecars were copied.

## LiteLLM route aliases changed unexpectedly

- Check `config/project/stack.base.yaml` for project defaults from the new release.
- Check `config/local/stack.override.yaml` for local alias overrides.
- Regenerate configs and verify `config/generated/litellm.config.yaml`.

## nginx was not installed

- `nginx` is optional.
- Re-run install or update with the component explicitly selected.
- On unsupported hosts, install nginx manually and point your operational docs/processes to `config/nginx/nginx.conf`.
