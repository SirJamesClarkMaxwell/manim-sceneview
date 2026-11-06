"""Sceny odbiorowe ChildView CE, uruchamiane wyłącznie rendererem natywnym."""

import sys
from pathlib import Path

import manim
from manim import Camera, Scene

sys.path.insert(0, str(Path(__file__).parent))
from child_view_cases import install_cases


class ChildCamera(Camera):
    def __init__(self, **kwargs):
        super().__init__(
            frame_height=6,
            frame_width=10,
            frame_center=[1, 0, 0],
            pixel_width=500,
            pixel_height=300,
            background_color="#00FF00",
            **kwargs,
        )


class ConfiguredChild(Scene):
    def __init__(self, **kwargs):
        super().__init__(camera_class=ChildCamera, random_seed=17, **kwargs)


install_cases(globals(), "ce", manim)
