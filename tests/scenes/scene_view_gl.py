"""Gospodarz `SceneView` dla manimgl — ta sama oś czasu co `scene_view_ce.py`, zwykła `Scene`.

Używane przez `tests/test_scene_view.py`.
"""

import os

from manimlib import LEFT, RIGHT, FadeIn, Scene

from manimsceneview import SceneView


class ViewTimingGL(Scene):
    def construct(self) -> None:
        view = SceneView(self, os.environ["MANIMSCENEVIEW_TEST_CLIP"], height=4, loop=True)
        self.play(FadeIn(view), run_time=0.5)
        self.wait(0.5)
        self.play(view.animate.shift(3 * RIGHT).scale(0.5), run_time=1)
        self.wait(1)
        view.pause()
        self.wait(0.5)
        view.resume()
        self.play(view.animate.set_opacity(1), run_time=0.5)


class TwoViewsGL(Scene):
    """Dwa niezależne widoki jednego klipu: osobne tekstury mimo wspólnego pliku źródła."""

    def construct(self) -> None:
        clip = os.environ["MANIMSCENEVIEW_TEST_CLIP"]
        left = SceneView(self, clip, height=2, loop=True).shift(3 * LEFT)
        right = SceneView(self, clip, height=2, loop=True).shift(3 * RIGHT).seek(1.0)
        self.add(left, right)
        self.wait(0.5)
