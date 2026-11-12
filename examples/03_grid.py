"""Grid. Run from repository root:

    python -m manim render -ql examples/clips.py Source
    python -m manim render -ql examples/03_grid.py Grid

Source: media/videos/clips/480p15/Source.mp4
Output: media/videos/03_grid/480p15/Grid.mp4
"""

from manim import RIGHT, UP, Group, Scene

from manimsceneview import SceneView


class Grid(Scene):
    def construct(self):
        views = Group(
            *[
                SceneView(
                    self, "media/videos/clips/480p15/Source.mp4", height=2, rate=rate, loop=True
                )
                for rate in (0.5, 1, 1.5, 2)
            ]
        ).arrange_in_grid(rows=2, buff=0.3)
        self.add(views)
        self.wait(2)
        self.play(views.animate.scale(0.8).shift(RIGHT + UP), run_time=2)
        self.wait(1)
