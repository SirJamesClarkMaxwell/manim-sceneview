# API reference

The public exports are `SceneView`, `FrameSource` and `ChildView`. Importing
`manimsceneview` does not import either engine. Views are factories returning the
selected engine's mobject, rather than public classes to subclass.

## SceneView

`SceneView(scene, file: Path | str, height: float | None = None, loop: bool = False, rate: float = 1.0, **kwargs)`

- `scene`: host CE or manimgl Scene; its class selects the engine.
- `file`: finished constant-frame-rate video; paths are relative to the working directory.
- `height`: scene units. With `None`, CE uses ImageMobject sizing from the resolution;
  GL defaults to 4 units.
- `loop`: wrap frame indices instead of holding the last frame.
- `rate`: clip seconds per host second, default 1. No validation or rate setter is provided.
- `kwargs`: forwarded to the engine's ImageMobject.

Methods on the returned view:

| Method | Result |
| --- | --- |
| `pause()` | Freeze the playback clock; return the view. Repeated calls are harmless. |
| `resume()` | Resume the clock without counting paused time; return the view. |
| `seek(t: float)` | Set position in clip seconds, independent of rate; return the view. |
| `current_frame() -> numpy.ndarray` | Current RGBA uint8 frame, rows from the top. |

Playback starts at the first clock read (normally its first update), uses absolute host
time, and continues during waits and geometry animations. Commands are immediate;
do not use `.animate.pause()` or `.animate.seek()`. Copies share playback and decoder.
Independently constructed views have independent playback. `become` and `Transform`
between views transfer geometry and opacity, not the source video.

CE replaces image pixels on updates, including while ordinary updaters are suspended.
GL uploads frames to an image texture, using a temporary PNG for its first frame.
There is no public SceneView `close()`; decoders remain registered for the render process.

Errors: unsupported hosts raise `TypeError`; without either engine installed engine
selection raises `ImportError`. File/decoder errors are those described under FrameSource;
ImageMobject keyword errors propagate from the selected engine.

## FrameSource

`FrameSource(file: Path | str, loop: bool = False)`

A decoder independent of Manim, using the first video stream. `file` is resolved to an
absolute path. `loop` wraps indices, including negative times; otherwise times clamp to
the first or last frame. Constant-frame-rate input only.

| Method | Result |
| --- | --- |
| `index_at(t: float) -> int` | Zero-based frame index: floor of seconds × fps with a small boundary epsilon, then wrap/clamp. |
| `rgba(t: float) -> numpy.ndarray` | Decode to that frame; RGBA uint8, shape `(height, width, 4)`, rows from top. |
| `close() -> None` | Close the decoder; a later `rgba()` can reopen it. Safe to call repeatedly. |

Attributes: `file` (resolved Path), `loop`, `duration` (seconds), `fps`, `count` (frame count),
`key` (path/size/mtime identity), `index` (last decoded index), `array` (last decoded frame
or None). Treat returned arrays as read-only: repeated reads may return the same array.
Only the current frame is retained. Backward seeks reopen and decode from the beginning.
Copies made through deepcopy return the same source. There is no context-manager API.

Errors propagate: missing paths raise `FileNotFoundError`; PyAV errors cover invalid or
unreadable media; missing duration/time base/frame rate raises `ValueError`. A missing
video stream can raise `IndexError`, and an empty stream can raise `StopIteration`.
Nonfinite times are not supported (floor raises `ValueError` or `OverflowError`).

## ChildView

`ChildView(host, child_class, *, height=4.0)`

- `host`: ordinary CE Cairo or manimgl Scene.
- `child_class`: Scene class from the same engine, instantiated internally; it receives
  `self.host`. No extra constructor arguments are accepted.
- `height`: finite positive height in host scene units, default 4.

Returns an image mobject on CE and a textured mobject on GL. Ordinary geometry and opacity
animations work. `close()` permanently stops the child and releases resources, returning
None. Removing the original view (also inside a group) or ending the host render closes it.
Host removal/tear_down overrides are preserved. Animation copies share the child; add the
original to the host. A completed child's final image remains visible.

The child runs cooperatively on the host thread. Its setup/construct/tear_down lifecycle
runs without a child movie writer. It must yield regularly through play/wait; Python work
between yields blocks the host. Each distinct host time advances it by one host frame,
including host waits. First sample is at `1 / host_fps`, without an extra sample at zero.
Each child play/wait rounds up to a whole frame and includes its final sample. Repeated
updates at the same host time do not step it. Python/NumPy RNG states are isolated;
configure the child's normal seed for reproducibility.

CE uses its configured fixed Cairo camera at the initial view pixel size, so later
enlargement can soften the image. Host cache is disabled at first ChildView creation with
one warning per host, restored after render. GL uses a framebuffer in the host GPU context
and the ManimGL 1.7.2 initialization/shader API. Background color is retained with opacity
forced to zero. No child audio, sections, nested ChildView, MovingCameraScene,
ThreeDScene, or GL camera frame motion is supported; configure the camera before animation.

Errors: `TypeError` for mismatched/invalid child classes, unsupported host, nesting,
nonfixed CE child camera or non-Cairo CE rendering; `ValueError` for nonpositive/nonfinite
height. Missing engines raise `ImportError`. Child code and engine errors propagate.
Calling the internal child's independent `render()` (CE) or `run()` (GL) raises
`RuntimeError`; use the host render instead.
