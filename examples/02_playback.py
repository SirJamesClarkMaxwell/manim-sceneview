"""Playback. Run from repository root:

    python -m manim render -qm examples/clips.py Source
    python -m manim render -qm examples/02_playback.py Control

Source: media/videos/clips/720p30/Source.mp4
Output: media/videos/02_playback/720p30/Control.mp4
"""

from manim import UP, Group, Scene, SurroundingRectangle, Text

from manimsceneview import SceneView


class Control(Scene):
    def construct(self):
        view = SceneView(self, "media/videos/clips/720p30/Source.mp4", height=4, rate=2, loop=True)
        label = Text("rate=2 / loop=True", font_size=30).shift(3 * UP)
        screen = Group(view, SurroundingRectangle(view, buff=0, color="#8da9ce", stroke_width=2))
        self.add(screen, label)
        self.wait(3)
        view.pause()
        label.become(Text("pause() - clock holds", font_size=30).move_to(label))
        self.wait(1)
        view.seek(1)
        label.become(Text("seek(1) / resume()", font_size=30).move_to(label))
        view.resume()
        self.wait(2)
