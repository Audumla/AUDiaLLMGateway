# Spec 621: macOS Install And Runtime

## Scope

macOS is a first-tier platform in the configuration and install model.

## Expectations

- shell bootstrap installers are provided for first-time setup
- the installed operational interface is a single `AUDiaLLMGateway.sh` command with simple actions and optional targets
- `brew` may be used for dependency installation where appropriate
- runtime behavior may differ from the Windows baseline and should be treated as a separate operational profile
- macOS `llama.cpp` install profiles must include `macos-metal` and `macos-cpu`
- `macos-metal` is the default macOS profile
