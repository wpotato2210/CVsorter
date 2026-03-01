from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


class CalibrationError(ValueError):
    """Raised when calibration values are inconsistent or tampered with."""


@dataclass(frozen=True)
class Calibration:
    mm_per_pixel: float
    calibration_hash: str

    def px_to_mm(self, pixel_value: float) -> float:
        return pixel_value * self.mm_per_pixel


def expected_calibration_hash(mm_per_pixel: float) -> str:
    payload = f"{mm_per_pixel:.12f}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_calibration(calibration_path: str | Path) -> Calibration:
    raw = json.loads(Path(calibration_path).read_text(encoding="utf-8"))
    mm_per_pixel = float(raw["mm_per_pixel"])
    calibration_hash = str(raw["calibration_hash"])

    expected_hash = expected_calibration_hash(mm_per_pixel)
    if calibration_hash != expected_hash:
        raise CalibrationError(
            "Invalid calibration hash: expected deterministic SHA-256 of mm_per_pixel"
        )

    return Calibration(mm_per_pixel=mm_per_pixel, calibration_hash=calibration_hash)
