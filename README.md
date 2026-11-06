# manim-sceneview

Use a rendered Manim scene as a mobject inside another scene. A `SceneView` plays a finished
video inside your scene and you can move, scale, fade and animate it like any other mobject,
while the video keeps playing in sync with the host scene's clock.

Works with both [Manim Community](https://github.com/ManimCommunity/manim) (Cairo renderer) and
[manimgl](https://github.com/3b1b/manim). The engine is picked from your scene's class, and
importing `manimsceneview` loads neither engine.

`ChildView` goes one step further: it runs an ordinary scene live inside the host, one host
frame at a time, without rendering it to a file first (see [ChildView](#childview)).

## Install

```bash
pip install "manim-sceneview[ce]"   # Manim Community 0.22
pip install "manim-sceneview[gl]"   # manimgl 1.7
```

Requires Python ≥ 3.11; manimgl rendering needs ffmpeg on PATH. Tested with CPython 3.11
and 3.13 on Windows 11; other systems are untested.

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

## ChildView

`ChildView(host, child_class, *, height=4.0)` runs an ordinary child `Scene` inside an
ordinary host `Scene`. Both must use the same engine. It creates no child movie or writer.
The child may read `self.host`, for example in `wait_until`.

Manim Community (Cairo):

```python
from manim import RED, RIGHT, UP, Scene, Square
from manimsceneview import ChildView


class Child(Scene):
    def construct(self):
        square = Square(fill_color=RED, fill_opacity=1)
        self.add(square)
        self.play(square.animate.shift(RIGHT), run_time=1)
        self.wait_until(lambda: self.host.time >= 2)
        self.play(square.animate.shift(UP), run_time=1)


class Host(Scene):
    def construct(self):
        view = ChildView(self, Child, height=4)
        self.add(view)
        self.play(view.animate.scale(0.7).shift(2 * RIGHT), run_time=2)
        self.wait(2)
```

For manimgl use the same classes and replace the engine import with:

```python
from manimlib import RED, RIGHT, UP, Scene, Square
from manimsceneview import ChildView
```

Render with `python -m manim render -ql example.py Host` or
`python -m manimlib example.py Host -w -l`. GL draws the child into its own framebuffer
in the host's GPU context and samples that texture directly.

The child advances once per host frame by `1 / host_fps`, including during `host.wait()`
and animations of the view. The first sample is at `1 / host_fps`; there is no extra output
sample at zero. Each child `play` or `wait` rounds its duration up to a whole host frame,
includes its final sample, and leaves the final image visible after completion. Repeated
updates at the same host time do not advance the child. Python and NumPy RNG states are
kept separately for host and child; set the child's normal random seed for reproducibility.

The view owns its greenlet and resources. Removing it with `host.remove(view)` (also inside
a group), calling `view.close()`, or ending the host render closes it explicitly. Host
`remove` and `tear_down` overrides are preserved. Copies used by animations share the child;
add the original view to its host. Closing is permanent; create a new view to run it again.

ChildView limitations:

- Cooperative execution on one thread: child code between `play()` / `wait()` calls blocks
  the host. A child must yield regularly.
- Fixed child camera only: no `MovingCameraScene`, `ThreeDScene`, or GL camera frame motion.
  Configure the child's camera before its animation instead. The camera's background color
  is retained, with background opacity forced to zero.
- No child audio or sections, and no nested ChildView.
- CE host render cache is disabled from creation of the first ChildView, with one warning
  per host. CE uses the child's configured Cairo camera at the view's initial pixel size;
  enlarging the view later can soften the image.
- GL support uses the ManimGL 1.7.2 scene initialization and shader API.

## Author, credits and license

manim-sceneview is created and maintained by
[SirJamesClarkMaxwell](https://github.com/SirJamesClarkMaxwell), who conceived the project.
It is released under the [MIT License](https://github.com/SirJamesClarkMaxwell/manim-sceneview/blob/main/LICENSE).

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
