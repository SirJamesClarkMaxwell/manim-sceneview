"""Shared four-second clip. From repository root:

    python -m manim render -ql examples/clips.py Source

Output: media/videos/clips/480p15/Source.mp4
"""

from manim import (
    LEFT,
    RED,
    RIGHT,
    Dot,
    Line,
    Scene,
    linear,
)


class Source(Scene):
    def construct(self):
        self.add(Line(4 * LEFT, 4 * RIGHT))
        dot = Dot(4 * LEFT, radius=0.3).set_color(RED)
        self.add(dot)
        self.play(dot.animate.shift(8 * RIGHT), run_time=4, rate_func=linear)
