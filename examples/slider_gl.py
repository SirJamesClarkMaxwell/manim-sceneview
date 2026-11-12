"""One host slider controls two live scenes; another scrubs a finished clip.

Run from the repository root, Source before Scrub:

    manimgl examples/slider_gl.py Source -w -l
    manimgl examples/slider_gl.py Sliders -w -l
    manimgl examples/slider_gl.py Scrub -w -l

Source output (relative to the working directory): videos/Source.mp4
Sliders and Scrub use the same output directory, with their scene names.
The slider spans [0, 1], mapping to [0, 4] seconds; Scrub moves forwards,
backwards to 1 second, then forwards to 3 seconds. Backward seeking decodes
from the start; ChildView itself only steps forwards.
"""

import numpy as np
from manimlib import (
    BLUE,
    DOWN,
    LEFT,
    PI,
    RED,
    RIGHT,
    UP,
    DecimalNumber,
    Dot,
    FadeIn,
    Group,
    Line,
    NumberLine,
    Scene,
    Square,
    ValueTracker,
    VMobject,
    always_redraw,
    linear,
)

from manimsceneview import ChildView, SceneView


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
        number = DecimalNumber(0, num_decimal_places=2).next_to(line, RIGHT)
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


class Source(Scene):
    def construct(self):
        self.add(Line(4 * LEFT, 4 * RIGHT))
        dot = Dot(4 * LEFT, radius=0.3).set_color(RED)
        self.add(dot)
        self.play(dot.animate.shift(8 * RIGHT), run_time=4, rate_func=linear)


class Scrub(Scene):
    def construct(self):
        self.k = ValueTracker(0)
        line = NumberLine(x_range=[0, 1, 0.25]).set_width(6).shift(2.6 * DOWN)
        marker = Dot(color=RED)
        marker.add_updater(lambda mob: mob.move_to(line.n2p(self.k.get_value())))
        number = DecimalNumber(0, num_decimal_places=2).next_to(line, RIGHT)
        number.add_updater(lambda mob: mob.set_value(self.k.get_value()))
        view = SceneView(self, "videos/Source.mp4", height=4).shift(0.5 * UP)
        view.pause()
        view.add_updater(lambda mob: mob.seek(4 * self.k.get_value()))
        self.add(view, line, marker, number)
        self.play(self.k.animate.set_value(1), run_time=2, rate_func=linear)
        self.wait(0.2)
        self.play(self.k.animate.set_value(0.25), run_time=2, rate_func=linear)
        self.wait(0.4)
        self.play(self.k.animate.set_value(0.75), run_time=1, rate_func=linear)
        self.wait(0.2)
