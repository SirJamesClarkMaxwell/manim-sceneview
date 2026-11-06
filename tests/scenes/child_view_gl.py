"""Sceny odbiorowe ChildView GL, bez importu manimgl w procesie pytesta."""

import sys
from pathlib import Path
from typing import ClassVar

import manimlib
from manimlib import Scene

sys.path.insert(0, str(Path(__file__).parent))
from child_view_cases import install_cases


class ConfiguredChild(Scene):
    random_seed = 17
    default_camera_config: ClassVar[dict] = {
        "frame_config": {"frame_shape": (10, 6), "center_point": [1, 0, 0]},
        "resolution": (600, 360),
        "background_color": "#00FF00",
    }


install_cases(globals(), "gl", manimlib)
