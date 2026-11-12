"""Child. Run from repository root:

    python -m manim render -qm examples/clips.py Source
    python -m manimlib examples/gl/04_child.py Host -w -m

Source: media/videos/clips/720p30/Source.mp4
Output: videos/Host.mp4
"""

from manimlib import BLUE, RIGHT, UP, Group, Scene, Square, SurroundingRectangle, Text

from manimsceneview import ChildView


class Child(Scene):
    def construct(self):
        square = Square(color=BLUE, fill_opacity=0.9)
        self.add(square)
        self.play(square.animate.shift(RIGHT), run_time=1)
        self.wait_until(lambda: self.host.time >= 2)
        self.play(square.animate.shift(UP), run_time=1)


class Host(Scene):
    def construct(self):
        view = ChildView(self, Child, height=4)
        panel = SurroundingRectangle(
            view, buff=0, color="#8da9ce", stroke_width=2, fill_color="#1c2533", fill_opacity=1
        )
        screen = Group(panel, view)
        label = Text("Live child / host moves the panel", font_size=32).shift(3 * UP)
        self.add(screen, label)
        self.play(
            screen.animate(suspend_mobject_updating=False).scale(0.8).shift(RIGHT), run_time=2
        )
        self.wait(2)
