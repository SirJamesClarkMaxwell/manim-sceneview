"""Four-second orbit clip: python -m manim render -qm examples/clips.py Source."""

import numpy as np
from manim import (
    DOWN,
    RED,
    RIGHT,
    UP,
    YELLOW,
    Circle,
    DecimalNumber,
    Dot,
    Scene,
    Text,
    TracedPath,
    ValueTracker,
    VGroup,
    linear,
)


class Source(Scene):
    def construct(self):
        self.camera.background_color = "#1c2533"
        clock = ValueTracker(0)
        orbit = Circle(radius=2.3, color="#536b89").stretch(1.7, 0)
        sun = Dot(radius=0.5, color=YELLOW)
        planet = Dot([3.91, 0, 0], radius=0.32, color=RED)
        planet.add_updater(
            lambda m: m.move_to(
                [
                    3.91 * np.cos(clock.get_value() * np.pi / 2),
                    2.3 * np.sin(clock.get_value() * np.pi / 2),
                    0,
                ]
            )
        )
        trail = TracedPath(planet.get_center, stroke_color="#4ddbd0", stroke_width=7)
        title = Text("ORBIT / recorded video", font_size=34).to_edge(UP)
        number = DecimalNumber(0, num_decimal_places=2, mob_class=Text, font_size=64)
        number.add_updater(lambda m: m.set_value(clock.get_value()))
        label = VGroup(Text("t =", font_size=64), number, Text("s", font_size=64))
        label.arrange(RIGHT, buff=0.18).to_edge(DOWN)
        self.add(orbit, sun, trail, planet, title, label)
        self.play(clock.animate.set_value(4), run_time=4, rate_func=linear)
