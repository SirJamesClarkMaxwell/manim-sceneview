"""Sliders. Run from repository root:

    python -m manim render -qm examples/clips.py Source
    python -m manimlib examples/gl/05_sliders.py Sliders -w -m

Source: media/videos/clips/720p30/Source.mp4.
Output: videos/Sliders.mp4
"""

import numpy as np
from manimlib import (
    BLUE,
    DOWN,
    PI,
    RED,
    RIGHT,
    UP,
    DecimalNumber,
    Dot,
    FadeIn,
    Group,
    NumberLine,
    Scene,
    Square,
    SurroundingRectangle,
    Text,
    ValueTracker,
    VMobject,
    always_redraw,
    linear,
)

from manimsceneview import ChildView


class Wave(Scene):
    def construct(self):
        def curve():
            x = np.linspace(-5, 5, 160)
            k = self.host.k.get_value()
            return VMobject(color="#ff7777", stroke_width=6).set_points_as_corners(
                np.column_stack((x, np.sin((1 + 2 * k) * x), np.zeros_like(x)))
            )

        self.add(always_redraw(curve))
        self.wait(60)


class Spinner(Scene):
    def construct(self):
        square = Square(side_length=3, color=BLUE, fill_opacity=0.85)
        square.add_updater(
            lambda mob: mob.become(
                Square(side_length=3, color=BLUE, fill_opacity=0.85).rotate(
                    PI * self.host.k.get_value()
                )
            )
        )
        self.add(square)
        self.wait(60)


class Sliders(Scene):
    def construct(self):
        self.k = ValueTracker(0)
        line = NumberLine(x_range=[0, 1, 0.25]).set_width(6).shift(2.6 * DOWN)
        marker = Dot(color=RED)
        marker.add_updater(lambda mob: mob.move_to(line.n2p(self.k.get_value())))
        number = DecimalNumber(0, num_decimal_places=2).next_to(line, RIGHT)
        number.add_updater(lambda mob: mob.set_value(self.k.get_value()))
        self.add(line, marker, number)
        views = Group(
            ChildView(self, Wave, height=2.8), ChildView(self, Spinner, height=2.8)
        ).arrange(RIGHT, buff=0.5)
        screens = Group(
            *[
                Group(
                    SurroundingRectangle(
                        v,
                        buff=0,
                        color="#8da9ce",
                        stroke_width=2,
                        fill_color="#1c2533",
                        fill_opacity=1,
                    ),
                    v,
                )
                for v in views
            ]
        )
        label = Text("slider drives both children", font_size=32).shift(3 * UP)
        self.add(label)
        self.play(FadeIn(screens, suspend_mobject_updating=False), run_time=0.5)
        self.wait(0.5)
        self.play(self.k.animate.set_value(0.75), run_time=1, rate_func=linear)
        self.wait(0.5)
        self.play(
            self.k.animate.set_value(0.25),
            screens.animate(suspend_mobject_updating=False).scale(0.8).shift(UP),
            run_time=1,
            rate_func=linear,
        )
        self.wait(0.5)
