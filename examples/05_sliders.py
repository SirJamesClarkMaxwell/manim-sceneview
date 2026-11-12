"""Sliders. Run from repository root:

    python -m manim render -ql examples/clips.py Source
    python -m manim render -ql examples/05_sliders.py Sliders

Source: media/videos/clips/480p15/Source.mp4.
Output: media/videos/05_sliders/480p15/Sliders.mp4
"""

import numpy as np
from manim import (
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
            return VMobject(color=RED).set_points_as_corners(
                np.column_stack((x, np.sin((1 + 2 * k) * x), np.zeros_like(x)))
            )

        self.add(always_redraw(curve))
        self.wait(60)


class Spinner(Scene):
    def construct(self):
        square = Square(side_length=3, color=BLUE, fill_opacity=0.5)
        square.add_updater(
            lambda mob: mob.become(
                Square(side_length=3, color=BLUE, fill_opacity=0.5).rotate(
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
        number = DecimalNumber(0, num_decimal_places=2, mob_class=Text).next_to(line, RIGHT)
        number.add_updater(lambda mob: mob.set_value(self.k.get_value()))
        self.add(line, marker, number)
        views = Group(
            ChildView(self, Wave, height=2.8), ChildView(self, Spinner, height=2.8)
        ).arrange(RIGHT, buff=0.5)
        self.play(FadeIn(views), run_time=0.5)
        self.wait(0.5)
        self.play(self.k.animate.set_value(0.75), run_time=1, rate_func=linear)
        self.wait(0.5)
        self.play(
            self.k.animate.set_value(0.25),
            views.animate.scale(0.8).shift(UP),
            run_time=1,
            rate_func=linear,
        )
        self.wait(0.5)
