from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_main() -> object:
    script_path = Path("tools/check_duplicate_constructor_keywords.py")
    spec = importlib.util.spec_from_file_location("check_duplicate_constructor_keywords", script_path)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load duplicate keyword checker script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.main


def test_duplicate_constructor_keywords_check_passes_for_runtime_module() -> None:
    main = _load_main()
    assert main([]) == 0


def test_duplicate_constructor_keywords_check_detects_duplicate_keywords(tmp_path: Path) -> None:
    main = _load_main()
    sample = tmp_path / "sample.py"
    sample.write_text("value = TransportConfig(serial_timeout_s=0.1, serial_timeout_s=0.2)\n", encoding="utf-8")

    assert main([str(sample)]) == 1
