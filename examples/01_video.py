"""Video. Run from repository root:

    python -m manim render -qm examples/clips.py Source
    python -m manim render -qm examples/01_video.py Video

Source: media/videos/clips/720p30/Source.mp4
Output: media/videos/01_video/720p30/Video.mp4
"""

from manim import PI, RIGHT, UP, FadeIn, Group, Scene, SurroundingRectangle, Text, Transform

from manimsceneview import SceneView


class Video(Scene):
    def construct(self):
        view = SceneView(self, "media/videos/clips/720p30/Source.mp4", height=4, loop=True)
        screen = Group(view, SurroundingRectangle(view, buff=0, color="#8da9ce", stroke_width=2))
        label = Text("FadeIn", font_size=32).shift(3 * UP)
        self.add(label)
        self.play(FadeIn(screen, suspend_mobject_updating=False), run_time=0.5)
        self.play(
            Transform(label, Text("scale + rotate - still playing", font_size=32).move_to(label)),
            run_time=0.5,
        )
        self.play(
            screen.animate(suspend_mobject_updating=False)
            .scale(0.7)
            .shift(2 * RIGHT)
            .rotate(PI / 8),
            run_time=3,
        )
        self.wait(1)
