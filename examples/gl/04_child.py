"""Child. Run from repository root:

    python -m manim render -ql examples/clips.py Source
    python -m manimlib examples/gl/04_child.py Host -w -l

Source: media/videos/clips/480p15/Source.mp4
Output: videos/Host.mp4
"""

from manimlib import BLUE, RIGHT, UP, Scene, Square

from manimsceneview import ChildView


class Child(Scene):
    def construct(self):
        square = Square(color=BLUE, fill_opacity=0.7)
        self.add(square)
        self.play(square.animate.shift(RIGHT), run_time=1)
        self.wait_until(lambda: self.host.time >= 2)
        self.play(square.animate.shift(UP), run_time=1)


class Host(Scene):
    def construct(self):
        view = ChildView(self, Child, height=4)
        self.add(view)
        self.play(view.animate.scale(0.8).shift(RIGHT), run_time=2)
        self.wait(2)
