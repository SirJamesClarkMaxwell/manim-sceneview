"""Scrub. Run from repository root:

    python -m manim render -qm examples/clips.py Source
    python -m manimlib examples/gl/06_scrub.py Scrub -w -m

Source: media/videos/clips/720p30/Source.mp4.
Output: videos/Scrub.mp4
"""

from manimlib import (
    DOWN,
    RED,
    RIGHT,
    UP,
    DecimalNumber,
    Dot,
    Group,
    NumberLine,
    Scene,
    SurroundingRectangle,
    Text,
    ValueTracker,
    linear,
)

from manimsceneview import SceneView


class Scrub(Scene):
    def construct(self):
        self.k = ValueTracker(0)
        line = NumberLine(x_range=[0, 1, 0.25]).set_width(6).shift(2.6 * DOWN)
        marker = Dot(color=RED)
        marker.add_updater(lambda mob: mob.move_to(line.n2p(self.k.get_value())))
        number = DecimalNumber(0, num_decimal_places=2).next_to(line, RIGHT)
        number.add_updater(lambda mob: mob.set_value(self.k.get_value()))
        view = SceneView(self, "media/videos/clips/720p30/Source.mp4", height=4).shift(0.5 * UP)
        view.pause()
        view.add_updater(lambda mob: mob.seek(4 * self.k.get_value()))
        screen = Group(view, SurroundingRectangle(view, buff=0, color="#8da9ce", stroke_width=2))
        label = Text("scrub forwards", font_size=32).shift(3.2 * UP)
        self.add(screen, line, marker, number, label)
        self.play(self.k.animate.set_value(1), run_time=2, rate_func=linear)
        self.wait(0.2)
        label.become(Text("scrub backwards", font_size=32).move_to(label))
        self.play(self.k.animate.set_value(0.25), run_time=2, rate_func=linear)
        self.wait(0.4)
        label.become(Text("seek(1) - then forwards", font_size=32).move_to(label))
        self.play(self.k.animate.set_value(0.75), run_time=1, rate_func=linear)
        self.wait(0.2)
