"""Bench package exports.

Keep imports lazy so lightweight tools like ``coloursorter-bench-cli`` can run
without optional runtime dependencies (e.g. PyTorch model stack).
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AckCode",
    "BenchFrame",
    "BenchLogEntry",
    "BenchMode",
    "BenchRunResult",
    "BenchRunner",
    "BenchSafetyConfig",
    "BenchEvaluation",
    "BenchScenario",
    "BenchSummary",
    "BenchFrameSource",
    "EncoderConfig",
    "EncoderFaultConfig",
    "FaultState",
    "FrameSourceError",
    "LiveConfig",
    "LiveFrameSource",
    "Esp32McuTransport",
    "MockMcuTransport",
    "MockTransportConfig",
    "ReplayConfig",
    "McuTransport",
    "ReplayFrameSource",
    "ScenarioResult",
    "SerialMcuTransport",
    "SerialTransportConfig",
    "SerialTransportError",
    "TransportResponse",
    "TriggerEvent",
    "VirtualEncoder",
    "default_scenarios",
    "scenarios_from_thresholds",
    "AcceptanceExample",
    "AcceptanceMetrics",
    "AcceptanceThresholds",
    "evaluate_acceptance_pack",
    "acceptance_gate_passed",
    "evaluate_logs",
    "write_artifacts",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BenchEvaluation": (".evaluation", "BenchEvaluation"),
    "evaluate_logs": (".evaluation", "evaluate_logs"),
    "write_artifacts": (".evaluation", "write_artifacts"),
    "AcceptanceExample": (".acceptance_pack", "AcceptanceExample"),
    "AcceptanceMetrics": (".acceptance_pack", "AcceptanceMetrics"),
    "AcceptanceThresholds": (".acceptance_pack", "AcceptanceThresholds"),
    "acceptance_gate_passed": (".acceptance_pack", "acceptance_gate_passed"),
    "evaluate_acceptance_pack": (".acceptance_pack", "evaluate_acceptance_pack"),
    "BenchFrameSource": (".frame_source", "BenchFrameSource"),
    "FrameSourceError": (".frame_source", "FrameSourceError"),
    "LiveConfig": (".live_source", "LiveConfig"),
    "LiveFrameSource": (".live_source", "LiveFrameSource"),
    "Esp32McuTransport": (".esp32_transport", "Esp32McuTransport"),
    "MockMcuTransport": (".mock_transport", "MockMcuTransport"),
    "MockTransportConfig": (".mock_transport", "MockTransportConfig"),
    "ReplayConfig": (".replay_source", "ReplayConfig"),
    "ReplayFrameSource": (".replay_source", "ReplayFrameSource"),
    "BenchRunner": (".runner", "BenchRunner"),
    "BenchRunResult": (".runner", "BenchRunResult"),
    "BenchSafetyConfig": (".runner", "BenchSafetyConfig"),
    "BenchScenario": (".scenarios", "BenchScenario"),
    "BenchSummary": (".scenarios", "BenchSummary"),
    "ScenarioResult": (".scenarios", "ScenarioResult"),
    "default_scenarios": (".scenarios", "default_scenarios"),
    "scenarios_from_thresholds": (".scenarios", "scenarios_from_thresholds"),
    "SerialMcuTransport": (".serial_transport", "SerialMcuTransport"),
    "SerialTransportConfig": (".serial_transport", "SerialTransportConfig"),
    "SerialTransportError": (".serial_transport", "SerialTransportError"),
    "McuTransport": (".transport", "McuTransport"),
    "AckCode": (".types", "AckCode"),
    "BenchFrame": (".types", "BenchFrame"),
    "BenchLogEntry": (".types", "BenchLogEntry"),
    "BenchMode": (".types", "BenchMode"),
    "FaultState": (".types", "FaultState"),
    "TransportResponse": (".types", "TransportResponse"),
    "TriggerEvent": (".types", "TriggerEvent"),
    "EncoderConfig": (".virtual_encoder", "EncoderConfig"),
    "EncoderFaultConfig": (".virtual_encoder", "EncoderFaultConfig"),
    "VirtualEncoder": (".virtual_encoder", "VirtualEncoder"),
}


def __getattr__(name: str) -> object:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, symbol = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), symbol)
    globals()[name] = value
    return value
