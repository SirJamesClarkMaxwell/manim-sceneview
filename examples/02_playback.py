"""Playback. Run from repository root:

    python -m manim render -ql examples/clips.py Source
    python -m manim render -ql examples/02_playback.py Control

Source: media/videos/clips/480p15/Source.mp4
Output: media/videos/02_playback/480p15/Control.mp4
"""

from manim import UP, Scene, Text

from manimsceneview import SceneView


class Control(Scene):
    def construct(self):
        view = SceneView(self, "media/videos/clips/480p15/Source.mp4", height=4, rate=2, loop=True)
        label = Text("2x speed / loop", font_size=30).shift(3 * UP)
        self.add(view, label)
        self.wait(3)
        view.pause()
        label.become(Text("Paused", font_size=30).move_to(label))
        self.wait(1)
        view.seek(1)
        label.become(Text("Seek to 1s / resume", font_size=30).move_to(label))
        view.resume()
        self.wait(2)
