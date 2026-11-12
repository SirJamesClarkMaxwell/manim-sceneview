"""Video. Run from repository root:

    python -m manim render -ql examples/clips.py Source
    python -m manim render -ql examples/01_video.py Video

Source: media/videos/clips/480p15/Source.mp4
Output: media/videos/01_video/480p15/Video.mp4
"""

from manim import PI, RIGHT, FadeIn, Scene

from manimsceneview import SceneView


class Video(Scene):
    def construct(self):
        view = SceneView(self, "media/videos/clips/480p15/Source.mp4", height=4, loop=True)
        self.play(FadeIn(view))
        self.play(view.animate.scale(0.7).shift(2 * RIGHT).rotate(PI / 8), run_time=3)
        self.wait(1)
