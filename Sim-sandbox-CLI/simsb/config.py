"""路径与默认配置。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURES = PKG_ROOT / "fixtures"
DEFAULT_CALIBRATION = PKG_ROOT / "config" / "calibration.yml"


@dataclass(frozen=True)
class Settings:
    fixtures_dir: Path
    calibration_path: Path
    brand_aliases: tuple[str, ...] = ()


def load_settings(
    *,
    fixtures_dir: str | Path | None = None,
    calibration_path: str | Path | None = None,
) -> Settings:
    fx = Path(
        fixtures_dir
        or os.environ.get("SIMSB_FIXTURES_DIR")
        or DEFAULT_FIXTURES
    ).expanduser().resolve()
    cal = Path(
        calibration_path
        or os.environ.get("SIMSB_CALIBRATION_PATH")
        or DEFAULT_CALIBRATION
    ).expanduser().resolve()
    return Settings(fixtures_dir=fx, calibration_path=cal)
