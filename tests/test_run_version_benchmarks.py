from __future__ import annotations

import json
from pathlib import Path

import scripts.run_version_benchmarks as version_bench


def test_combination_key_is_stable() -> None:
    assert (
        version_bench._combination_key(
            version_ref="b8759",
            validation_profile="quick",
            acceleration="rocm",
            settings_profile="default",
            target="native-hip",
        )
        == "b8759|quick|rocm|default|native-hip"
    )


def test_resolve_accelerations_prefers_configured_host_capabilities() -> None:
    catalog = {"defaults": {"benchmark": {"accelerations": "auto"}}}
    assert version_bench._resolve_accelerations(catalog, "auto", {"cpu"}) == ["cpu"]
    assert version_bench._resolve_accelerations(catalog, "auto", {"cpu", "vulkan"}) == ["cpu", "vulkan"]


def test_resolve_accelerations_honors_explicit_override() -> None:
    catalog = {"defaults": {"benchmark": {"accelerations": "cpu"}}}
    assert version_bench._resolve_accelerations(catalog, "cpu,rocm,vulkan", {"cpu"}) == ["cpu", "rocm", "vulkan"]


def test_update_history_preserves_latest_and_history() -> None:
    catalog: dict = {}
    run_record = {
        "run_id": "20260412T000000Z",
        "started_at_utc": "2026-04-12T00:00:00Z",
        "version_ref": "b8759",
        "track": "latest-release",
        "acceleration": "rocm",
        "settings_profile": "default",
        "summary": {
            "results": [
                {
                    "target": "native-hip",
                    "experimental": True,
                    "status": "passed",
                    "returncode": 0,
                    "benchmark_output": "x.json",
                    "benchmark": {"top_tok_per_sec": 12.34, "success_count": 3},
                }
            ]
        },
    }

    version_bench.update_history(catalog=catalog, run_record=run_record, validation_profile="quick")

    key = "b8759|quick|rocm|default|native-hip"
    latest = catalog["combinations"][key]["latest"]
    assert latest["top_tok_per_sec"] == 12.34
    assert latest["status"] == "passed"
    assert latest["experimental"] is True
    assert latest["regression_detected"] is False
    assert len(catalog["combinations"][key]["history"]) == 1


def test_update_history_marks_pass_to_fail_as_regression() -> None:
    catalog: dict = {
        "combinations": {
            "b8759|quick|rocm|default|native-hip": {
                "history": [
                    {
                        "version_ref": "b8759",
                        "validation_profile": "quick",
                        "acceleration": "rocm",
                        "settings_profile": "default",
                        "target": "native-hip",
                        "status": "passed",
                        "run_id": "earlier",
                    }
                ],
                "latest": {
                    "version_ref": "b8759",
                    "validation_profile": "quick",
                    "acceleration": "rocm",
                    "settings_profile": "default",
                    "target": "native-hip",
                    "status": "passed",
                    "run_id": "earlier",
                },
            }
        }
    }
    run_record = {
        "run_id": "20260413T000000Z",
        "started_at_utc": "2026-04-13T00:00:00Z",
        "version_ref": "b8759",
        "track": "latest-release",
        "acceleration": "rocm",
        "settings_profile": "default",
        "summary": {
            "results": [
                {
                    "target": "native-hip",
                    "experimental": False,
                    "status": "failed",
                    "returncode": 1,
                    "benchmark_output": "x.json",
                    "benchmark": {},
                }
            ]
        },
    }

    version_bench.update_history(catalog=catalog, run_record=run_record, validation_profile="quick")

    latest = catalog["combinations"]["b8759|quick|rocm|default|native-hip"]["latest"]
    assert latest["previous_status"] == "passed"
    assert latest["ever_passed_before"] is True
    assert latest["regression_detected"] is True


def test_build_markdown_report_renders_versions_accels_and_targets() -> None:
    catalog = {
        "combinations": {
            "b8759|quick|rocm|default|native-hip": {
                "latest": {
                    "version_ref": "b8759",
                    "validation_profile": "quick",
                    "acceleration": "rocm",
                    "settings_profile": "default",
                    "target": "native-hip",
                    "status": "passed",
                    "top_tok_per_sec": 12.34,
                }
            },
            "b8759|quick|vulkan|default|native-vulkan": {
                "latest": {
                    "version_ref": "b8759",
                    "validation_profile": "quick",
                    "acceleration": "vulkan",
                    "settings_profile": "default",
                    "target": "native-vulkan",
                    "status": "failed",
                    "top_tok_per_sec": None,
                }
            },
        }
    }

    report = version_bench.build_markdown_report(catalog, validation_profile="quick")

    assert "| Version | Accel | Settings | native-hip | native-vulkan |" in report
    assert "| b8759 | rocm | default | 12.34 T/s | N/A |" in report
    assert "| b8759 | vulkan | default | N/A | FAILED |" in report


def test_build_table_report_exports_json_friendly_rows() -> None:
    catalog = {
        "combinations": {
            "b8759|quick|rocm|default|native-hip": {
                "latest": {
                    "version_ref": "b8759",
                    "validation_profile": "quick",
                    "acceleration": "rocm",
                    "settings_profile": "default",
                    "target": "native-hip",
                    "status": "passed",
                    "top_tok_per_sec": 12.34,
                    "backend_top_tok_per_sec": 15.67,
                    "benchmark_context": {"host": {"platform": "Windows"}},
                }
            }
        }
    }

    report = version_bench.build_table_report(catalog, validation_profile="quick")

    assert report["versions"] == ["b8759"]
    assert report["accelerations"] == ["rocm"]
    assert report["settings_profiles"] == ["default"]
    assert report["targets"] == ["native-hip"]
    assert report["rows"][0]["cells"]["native-hip"]["display"] == "12.34 T/s"
    assert report["rows"][0]["cells"]["native-hip"]["backend_top_tok_per_sec"] == 15.67
    assert report["rows"][0]["cells"]["native-hip"]["lane_source"] == "github_release"
    assert report["rows"][0]["cells"]["native-hip"]["repo_or_artifact"] == "ggml-org/llama.cpp"
    assert report["rows"][0]["cells"]["native-hip"]["benchmark_output"] is None
    assert report["route_details"] == []
    assert report["suspicious_runs"] == []
    assert "rows_by_key" in report

    exported = version_bench._json_table_report(report)
    assert "rows_by_key" not in exported
    assert exported["rows"][0]["cells"]["native-hip"]["benchmark_context"]["host"]["platform"] == "Windows"


def test_build_markdown_report_includes_route_metrics_table(tmp_path: Path) -> None:
    fixture_path = tmp_path / "route-metrics.json"
    fixture_path.write_text(
        json.dumps(
            {
                "benchmark_context": {
                    "host": {
                        "platform": "Windows",
                        "gpu_name": "AMD Radeon RX 7900 GRE",
                        "host_acceleration": "vulkan",
                    },
                    "target": {
                        "native_llama_cpp_profile": "windows-vulkan",
                        "native_backend": "vulkan",
                        "llama_version": "b8759",
                        "model_display_name": "Qwen3.5-2B-Q4_K_M.gguf",
                        "backend_model_name": "qwen3-5-2b-q4-validation-vulkan",
                        "model_filename": "Qwen3.5-2B-Q4_K_M.gguf",
                    },
                    "installation": {
                        "llama_cpp_profile": "windows-vulkan",
                        "llama_cpp_version": "b8759",
                        "llama_cpp_backend": "vulkan",
                    },
                    "targets": [
                        {
                            "benchmark_settings_profile": "default",
                            "backend_device_selection": {
                                "family": "rocm",
                                "raw": "ROCm0",
                                "devices": ["ROCm0"],
                                "device_count": 1,
                            },
                        }
                    ],
                },
                "results": [
                    {
                        "route": "gateway",
                        "model": "Qwen3.5-2B-Q4_K_M.gguf",
                        "observed_model": "local/qwen2b_validation_rocm",
                        "sample_index": 1,
                        "sample_label": "medium-1",
                        "sample_count": 1,
                        "prompt": "Reply with one short sentence confirming this request was handled.",
                        "max_tokens": 48,
                        "tok_per_sec": 54.4,
                        "backend_tok_per_sec": 85.0,
                        "elapsed_seconds": 0.27,
                        "base_url": "http://127.0.0.1:4000",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    catalog = {
        "combinations": {
            "b8759|quick|rocm|default|native-hip": {
                "latest": {
                    "version_ref": "b8759",
                    "validation_profile": "quick",
                    "acceleration": "rocm",
                    "settings_profile": "default",
                    "target": "native-hip",
                    "status": "passed",
                    "top_tok_per_sec": 12.34,
                    "benchmark_output": str(fixture_path),
                }
            }
        }
    }

    report = version_bench.build_markdown_report(catalog, validation_profile="quick")

    assert "## Route Metrics" in report
    assert "Client Avg T/s is the mean end-to-end throughput" in report
    assert "Lane Source | Repo / Artifact | Exact Ref | Build Profile | Backend | Toolchain Version | Executable Path / Package" in report
    assert "AMD Radeon RX 7900 GRE | ggml-org | github_release | ggml-org/llama.cpp | ggml-org/llama.cpp @ b8759 | windows-vulkan | vulkan" in report
    assert "| default | native-hip | gateway | 1/1 | Qwen3.5-2B-Q4_K_M.gguf | local/qwen2b_validation_rocm | passed | ROCm0 | 54.40 T/s | 85.00 T/s | 0.27s | http://127.0.0.1:4000 |" in report
    assert "Backend Device" in report


def test_build_table_report_exposes_regressions_and_markdown_section() -> None:
    catalog = {
        "combinations": {
            "b8763|quick|rocm|default|native-vulkan": {
                "latest": {
                    "version_ref": "b8763",
                    "validation_profile": "quick",
                    "acceleration": "rocm",
                    "settings_profile": "default",
                    "target": "native-vulkan",
                    "status": "failed",
                    "regression_detected": True,
                    "previous_status": "passed",
                }
            }
        }
    }

    report = version_bench.build_table_report(catalog, validation_profile="quick")
    assert report["regressions"][0]["target"] == "native-vulkan"
    assert report["rows"][0]["cells"]["native-vulkan"]["regression_detected"] is True

    markdown = version_bench.build_markdown_report(catalog, validation_profile="quick")
    assert "## Regression Candidates" in markdown
    assert "b8763 / rocm / default / native-vulkan: regressed from `passed` to `failed`" in markdown


def test_host_label_uses_cpu_for_cpu_targets() -> None:
    context = {
        "host": {
            "platform": "Windows",
            "processor": "AMD Ryzen 9 7950X",
            "gpu_name": "AMD Radeon RX 7900 GRE",
            "host_acceleration": "rocm",
        }
    }

    assert version_bench._host_label_from_context(context, "cpu") == "AMD CPU"


def test_profile_identity_prefers_human_git_refs_and_compact_packages() -> None:
    identity = version_bench._profile_identity(
        target_name="native-hip-turboquant",
        target_context={
            "native_llama_cpp_profile": "windows-hip-turboquant",
            "native_backend": "rocm",
        },
        installation_context={
            "llama_cpp_executable_path": r"H:\development\projects\AUDia\AUDiaLLMGateway\test-work\native-backend-validation-matrix\quick\native-hip\tools\llama.cpp\b8763-hip\llama-server.exe",
        },
    )

    assert identity["lane_family"] == "TheTom"
    assert identity["exact_ref"] == "TheTom/llama-cpp-turboquant @ feature/turboquant-kv-cache"
    assert identity["resolved_commit"] == "8590cbff961dbaf1d3a9793fd11d402e248869b9"
    assert identity["executable_path_or_package"] == "b8763-hip/llama-server.exe"
    assert identity["toolchain_hint"] == "ROCm SDK"


def test_collect_anomalies_flags_model_mismatch_and_route_spread(tmp_path: Path) -> None:
    rocm_benchmark = tmp_path / "rocm.json"
    rocm_benchmark.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "route": "gateway",
                        "model": "local/qwen2b_validation_cpu",
                        "tok_per_sec": 21.4,
                        "backend_tok_per_sec": 41.4,
                    },
                    {
                        "route": "direct-llama-swap",
                        "model": "local/qwen2b_validation_cpu",
                        "tok_per_sec": 18.5,
                        "backend_tok_per_sec": 37.6,
                    },
                    {
                        "route": "direct-llama-server",
                        "model": "local/qwen2b_validation_cpu",
                        "tok_per_sec": 24.8,
                        "backend_tok_per_sec": 36.3,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    vulkan_benchmark = tmp_path / "vulkan.json"
    vulkan_benchmark.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "route": "gateway",
                        "model": "local/qwen2b_validation_vulkan",
                        "tok_per_sec": 1.9,
                        "backend_tok_per_sec": 159.1,
                    },
                    {
                        "route": "direct-llama-swap",
                        "model": "local/qwen2b_validation_vulkan",
                        "tok_per_sec": 76.5,
                        "backend_tok_per_sec": 164.3,
                    },
                    {
                        "route": "direct-llama-server",
                        "model": "local/qwen2b_validation_vulkan",
                        "tok_per_sec": 99.9,
                        "backend_tok_per_sec": 180.3,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    catalog = {
        "combinations": {
            "master|quick|rocm|default|native-hip-turboquant": {
                "latest": {
                    "version_ref": "master",
                    "validation_profile": "quick",
                    "acceleration": "rocm",
                    "settings_profile": "default",
                    "target": "native-hip-turboquant",
                    "status": "passed",
                    "benchmark_output": str(rocm_benchmark),
                }
            },
            "b8759|quick|vulkan|default|native-vulkan": {
                "latest": {
                    "version_ref": "b8759",
                    "validation_profile": "quick",
                    "acceleration": "vulkan",
                    "settings_profile": "default",
                    "target": "native-vulkan",
                    "status": "passed",
                    "benchmark_output": str(vulkan_benchmark),
                }
            },
        }
    }

    anomalies = version_bench._collect_anomalies(catalog, validation_profile="quick")

    assert any("model mismatch" in item and "local/qwen2b_validation_rocm" in item for item in anomalies)
    assert any("gateway is" in item and "slower than" in item for item in anomalies)
    assert any("gateway/transport" in item for item in anomalies)
    assert not any("local/qwen2b_validation_vulkan" in item and "model mismatch" in item for item in anomalies)

    report = version_bench.build_markdown_report(catalog, validation_profile="quick")
    assert "## Suspicious Runs" in report
