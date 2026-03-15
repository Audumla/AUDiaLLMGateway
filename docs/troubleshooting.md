# Troubleshooting

## Update preserved my local config but something broke

- Run `.\scripts\validate-configs.ps1`
- Inspect `state/install-state.json`
- Review type conflict warnings for `config/local/*.yaml`
- Regenerate config outputs with `.\scripts\generate-configs.ps1`

## Release installer failed to install a dependency

- Check whether the host package manager exists:
  - Windows: `winget`
  - Linux: `apt-get` or `dnf`
  - macOS: `brew`
- If automatic install is unavailable, install the missing dependency manually and rerun the installer or update.

## llama-swap does not start after update

- Confirm `LLAMA_SWAP_EXE` still points to the correct executable.
- Confirm your local overrides did not introduce a type mismatch in `config/local/llama-swap.override.yaml`.
- Inspect `.runtime/logs/llama-swap.log`.

## LiteLLM route aliases changed unexpectedly

- Check `config/project/stack.base.yaml` for project defaults from the new release.
- Check `config/local/stack.override.yaml` for local alias overrides.
- Regenerate configs and verify `config/generated/litellm.config.yaml`.

## nginx was not installed

- `nginx` is optional.
- Re-run install or update with the component explicitly selected.
- On unsupported hosts, install nginx manually and point your operational docs/processes to `config/nginx/nginx.conf`.
