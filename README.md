# manim-sceneview

Use a rendered Manim scene as a mobject inside another scene. A `SceneView` plays a finished
video inside your scene and you can move, scale, fade and animate it like any other mobject,
while the video keeps playing in sync with the host scene's clock.

Works with both [Manim Community](https://github.com/ManimCommunity/manim) (Cairo renderer) and
[manimgl](https://github.com/3b1b/manim). The engine is picked from your scene's class, and
importing `manimsceneview` loads neither engine.

## Install

```bash
pip install "manim-sceneview[ce]"   # Manim Community 0.22
pip install "manim-sceneview[gl]"   # manimgl 1.7
```

## Usage

```python
from manim import UL, FadeIn, Scene

from manimsceneview import SceneView


class Host(Scene):
    def construct(self):
        view = SceneView(self, "media/videos/orbit/480p15/Orbit.mp4", height=4, loop=True)
        self.play(FadeIn(view))
        self.play(view.animate.scale(0.5).to_corner(UL), run_time=2)  # the video keeps playing
        view.pause()
        self.wait(1)
        view.resume()
        self.wait(1)
```

With manimgl, import `Scene` and the rest from `manimlib` instead; the `SceneView` call is the
same.

`SceneView(scene, file, height=None, loop=False, rate=1.0, **kwargs)`:

- `scene`: the host scene (usually `self`). Its class decides the engine.
- `file`: a video file, for example the output of an earlier `manim render`.
- `height`: height in scene units. Without it, Manim Community sizes the view from the video
  resolution, like `ImageMobject`, and manimgl uses 4 units.
- `loop`: start again from the first frame after the last one.
- `rate`: playback speed relative to the host scene's time.
- Extra keyword arguments go to the engine's `ImageMobject`.

The view's time is the host scene's absolute time since the view was first drawn, so the
video does not drift across many `play()` calls. Copies of a view, such as `.animate` targets
and `copy()`, share its playback and decoder and show the same frame.

Commands, which act at once and are not animations:

- `view.pause()` and `view.resume()`.
- `view.seek(t)` jumps to `t` seconds of the video, before the playback rate is applied.
- `view.current_frame()` returns the current RGBA frame as a NumPy array.

`FrameSource(file, loop=False)` is the decoder behind a view: `rgba(t)` returns the frame shown
at video time `t`, without Manim.

## Limitations

- Constant-frame-rate videos only.
- Seeking backwards decodes again from the start of the file.
- `become` or `Transform` between two views keeps geometry and opacity, but not the video
  source.
- Manim Community support is tested on 0.22 only, manimgl on 1.7.

## Author, credits and license

manim-sceneview is created and maintained by
[SirJamesClarkMaxwell](https://github.com/SirJamesClarkMaxwell), who conceived the project.
It is released under the [MIT License](LICENSE).

- It was first developed inside [manim-cue](https://github.com/SirJamesClarkMaxwell/manim-cue),
  the author's presentation tool, which is built on
  [manim-slides](https://github.com/jeertmans/manim-slides) by Jérome Eertmans.
- **[Manim Community](https://github.com/ManimCommunity/manim)** and
  **[manimgl](https://github.com/3b1b/manim)** by Grant Sanderson (3Blue1Brown) are the
  animation engines it builds on.
- **[PyAV](https://github.com/PyAV-Org/PyAV)** decodes the video frames.

## Development

```bash
uv sync --all-extras
uv run pytest            # the manimgl render tests carry the `gpu` marker
```
