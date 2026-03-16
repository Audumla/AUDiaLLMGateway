from pathlib import Path


def test_windows_cmd_wrapper_targets_powershell_entrypoint() -> None:
    root = Path(__file__).resolve().parents[1]
    cmd_wrapper = root / "scripts" / "AUDiaLLMGateway.cmd"
    ps_entrypoint = root / "scripts" / "AUDiaLLMGateway.ps1"

    content = cmd_wrapper.read_text(encoding="utf-8").lower()

    assert ps_entrypoint.exists()
    assert "powershell" in content
    assert "audiallmgateway.ps1" in content


def test_unix_entrypoint_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    shell_entrypoint = root / "scripts" / "AUDiaLLMGateway.sh"

    assert shell_entrypoint.exists()
