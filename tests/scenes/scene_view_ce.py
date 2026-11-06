"""Gospodarz `SceneView` dla Manim CE: zwykła `Scene`, klip ze zmiennej MANIMSCENEVIEW_TEST_CLIP.

Oś czasu (s): FadeIn 0-0,5 · wait 0,5-1 · przesunięcie i skala 1-2 · wait 2-3 · pauza 3-3,5 ·
wznowienie 3,5-4 (widok gra dalej od miejsca pauzy).
Używane przez `tests/test_scene_view.py`.
"""

import os

from manim import LEFT, RIGHT, FadeIn, Scene

from manimsceneview import SceneView


class ViewTimingCE(Scene):
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


class TwoViewsCE(Scene):
    """Dwa niezależne widoki jednego klipu: lewy od 0 s, prawy przesunięty o 1 s."""

    def construct(self) -> None:
        clip = os.environ["MANIMSCENEVIEW_TEST_CLIP"]
        left = SceneView(self, clip, height=2, loop=True).shift(3 * LEFT)
        right = SceneView(self, clip, height=2, loop=True).shift(3 * RIGHT).seek(1.0)
        self.add(left, right)
        self.wait(1)
