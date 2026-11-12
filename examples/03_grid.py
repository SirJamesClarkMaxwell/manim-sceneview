"""Grid. Run from repository root:

    python -m manim render -qm examples/clips.py Source
    python -m manim render -qm examples/03_grid.py Grid

Source: media/videos/clips/720p30/Source.mp4
Output: media/videos/03_grid/720p30/Grid.mp4
"""

from manim import RIGHT, UP, FadeTransform, Group, Scene, SurroundingRectangle, Text

from manimsceneview import SceneView


class Grid(Scene):
    def construct(self):
        views = Group(
            *[
                SceneView(
                    self, "media/videos/clips/720p30/Source.mp4", height=2, rate=rate, loop=True
                )
                for rate in (0.5, 1, 1.5, 2)
            ]
        ).arrange_in_grid(rows=2, buff=0.3)
        screens = Group(
            *[
                Group(v, SurroundingRectangle(v, buff=0, color="#8da9ce", stroke_width=2))
                for v in views
            ]
        )
        label = Text("Four screens / rates 0.5, 1, 1.5, 2", font_size=32).shift(3 * UP)
        self.add(screens, label)
        self.wait(2)
        self.play(
            screens.animate(suspend_mobject_updating=False).scale(0.8).shift(0.6 * RIGHT),
            FadeTransform(
                label,
                Text("Move the group - each clock keeps playing", font_size=30).move_to(label),
            ),
            run_time=2,
        )
        self.wait(1)
