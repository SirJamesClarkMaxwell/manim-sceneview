"""Adapter ChildView dla Cairo Manim CE 0.22."""

import warnings

import numpy as np
from manim import Camera, ImageMobject, MovingCameraScene, Scene, ThreeDScene, config
from manim.renderer.cairo_renderer import CairoRenderer

from manimsceneview.child_view import ChildState, isolated_rng, rng_state


class ChildRenderer(CairoRenderer):
    """Inicjalizacja zwykłej Scene bez tworzenia writera ani plików."""

    def init_scene(self, scene, session_spec, file_writer_settings):
        pass


class WriterlessScene(Scene):
    def __init__(self, *, camera_class=Camera, **kwargs):
        super().__init__(
            renderer=ChildRenderer(camera_class=camera_class), camera_class=camera_class, **kwargs
        )


class StepAdapter:
    def play(self, *args, **kwargs):
        self.compile_animation_data(*args, **kwargs)
        self.begin_animations()
        dt = 1 / self._child_state.host.camera.frame_rate
        count = int(np.ceil(self.duration / dt - 1e-9))
        for index in range(1, count + 1):
            self.renderer.time += dt
            self.update_to_time(index * dt)
            self._child_state.steps += 1
            self._child_state.times.append(self.time)
            self._child_state.task.parent.switch()
            if self.stop_condition is not None and self.stop_condition():
                break
        for animation in self.animations:
            animation.finish()
            animation.clean_up_from_scene(self)
        self.update_mobjects(0)
        self.renderer.num_plays += 1

    def render(self, *args, **kwargs):
        raise RuntimeError("ChildView child cannot render independently")


class ChildViewCE(ImageMobject):
    """Stały ImageMobject: animacje gospodarza nie tracą tożsamości treści."""

    def __init__(self, host, child_class, *, height):
        if issubclass(child_class, (MovingCameraScene, ThreeDScene)):
            raise TypeError("ChildView requires a fixed Cairo child camera")
        if not isinstance(host.renderer, CairoRenderer):
            raise TypeError("ChildView supports Manim Community's Cairo renderer only")
        self.state = ChildState(host)
        state = self.state
        bases = (
            (StepAdapter, child_class, WriterlessScene)
            if child_class is not Scene
            else (StepAdapter, WriterlessScene)
        )
        stepped = type(
            "Stepped" + child_class.__name__, bases, {"_child_state": state, "host": host}
        )
        with isolated_rng(state.child_rng):
            state.child = stepped(always_update_mobjects=True)
            state.child_rng = rng_state()
        child = state.child
        child._child_state = state
        child.host = host
        camera = child.camera
        camera.background_opacity = 0
        pixel_height = max(2, round(height / host.camera.frame_height * host.camera.pixel_height))
        pixel_width = max(2, round(pixel_height * camera.frame_width / camera.frame_height))
        frame_width, frame_height = camera.frame_width, camera.frame_height
        camera.reset_pixel_shape(pixel_height, pixel_width)
        camera.frame_width, camera.frame_height = frame_width, frame_height
        camera.reset()
        super().__init__(camera.pixel_array.copy())
        self.stretch_to_fit_height(height)
        self.stretch_to_fit_width(height * camera.frame_width / camera.frame_height)
        self.add_updater(lambda mob, dt: None)
        if not getattr(host, "_child_cache_disabled", False):
            previous_caching = config.disable_caching
            config.disable_caching = True
            host._child_cache_disabled = True

            def restore_cache():
                config.disable_caching = previous_caching
                host._child_cache_disabled = False
                host._child_restore_cache = None

            host._child_restore_cache = restore_cache
            warnings.warn("ChildView disables the CE host render cache", UserWarning, stacklevel=3)

    def update(self, dt=0, recursive=True):
        if not self.state.closed and any(
            view is self for view in getattr(self.state.host, "_child_views", ())
        ):
            self.state.advance(self.state.host.time)
            camera = self.state.child.camera
            camera.reset()
            camera.capture_mobjects(self.state.child.mobjects)
            self.pixel_array = camera.pixel_array.copy()
        return super().update(dt, recursive)

    @property
    def child(self):
        return self.state.child

    def close(self):
        try:
            self.state.close()
        finally:
            self.pixel_array[:] = 0
