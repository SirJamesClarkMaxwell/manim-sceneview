"""Adapter GPU ChildView dla manimgl 1.7.2."""

import random

import numpy as np
import OpenGL.GL as gl
from manimlib import Camera, ImageMobject, Mobject, Rectangle, Scene
from manimlib.config import manim_config
from manimlib.utils.dict_ops import merge_dicts_recursively

from manimsceneview.child_view import ChildState, isolated_rng, rng_state


class SharedCamera(Camera):
    """Oddzielne FBO, ten sam kontekst: bez przełączania kontekstu systemowego."""

    def __init__(self, ctx, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)

    def init_context(self):
        pass

    def refresh_uniforms(self):
        super().refresh_uniforms()
        # GL zakłada FRAME_SHAPE; własny kadr dziecka wymaga obu wymiarów projekcji.
        scale = self.frame.get_scale()
        self.uniforms["frame_rescale_factors"] = (
            2 * scale / self.frame.get_width(),
            2 * scale / self.frame.get_height(),
            scale / self.frame.get_focal_distance(),
        )


class WriterlessScene(Scene):
    """Dolna część MRO zastępuje wyłącznie inicjalizację silnika 1.7.2."""

    def tear_down(self):
        pass

    def __init__(self, *, camera_config=None, **kwargs):
        # Scene.__init__ zawsze tworzy writer; zachowujemy konstruktor klasy autora.
        host = self.host
        self.window = None
        self.camera_config = merge_dicts_recursively(
            manim_config.camera,
            self.default_camera_config,
            camera_config or {},
            {"fps": host.camera.fps, "background_opacity": 0},
        )
        self.camera = SharedCamera(host.camera.ctx, samples=0, **self.camera_config)
        self.frame = self.camera.frame
        self.frame.reorient(*self.default_frame_orientation)
        self.frame.make_orientation_default()
        self.mobjects = [self.frame]
        self.render_groups = []
        self.id_to_mobject_map = {}
        self.time = self.skip_time = 0.0
        self.num_plays = 0
        self.skip_animations = self.original_skipping_status = False
        self.start_at_animation_number = self.end_at_animation_number = None
        self.presenter_mode = self.hold_on_wait = False
        self.show_animation_progress = self.leave_progress_bars = False
        self.always_update_mobjects = True
        self.preview_while_skipping = False
        self.default_wait_time = 1.0
        self.undo_stack, self.redo_stack = [], []
        self.quit_interaction = False
        if self.random_seed is not None:
            random.seed(self.random_seed)
            np.random.seed(self.random_seed)


class StepAdapter:
    def __init__(self, owner, host):
        self.owner = self._child_state = owner
        self.host = host
        super().__init__()

    def pre_play(self):
        pass

    def post_play(self):
        self.num_plays += 1

    def get_time_progression(self, run_time, **kwargs):
        # Każda animacja kończy się na pierwszej pełnej klatce po swoim run_time.
        count = int(np.ceil(run_time * self.camera.fps - 1e-9))
        return np.arange(1, count + 1) / self.camera.fps

    def update_frame(self, dt=0, force_draw=False):
        self.increment_time(dt)
        self.update_mobjects(dt)
        self.owner.steps += 1
        self.owner.times.append(self.time)

    def emit_frame(self):
        from greenlet import getcurrent

        getcurrent().parent.switch()

    def run(self):
        raise RuntimeError("Child.run() is unsupported")


class FrameTexture(ImageMobject):
    def __init__(self, texture):
        self.texture = texture
        Mobject.__init__(self)

    def init_points(self):
        pass

    def init_shader_wrapper(self, ctx):
        Mobject.init_shader_wrapper(self, ctx)
        self.shader_wrapper.add_texture("Texture", self.texture)


class DrawBridge:
    """Wrapper respektuje grupowanie Scene.assemble_render_groups bez zmian upstreamu."""

    def __init__(self, view):
        self.view = view

    def __deepcopy__(self, memo):
        return self

    def get_id(self):
        return id(self)

    def release(self):
        pass

    def read_in(self, data):
        pass

    def update_program_uniforms(self, uniforms):
        self.uniforms = uniforms

    def pre_render(self):
        pass

    def render(self):
        self.view.draw(self.uniforms)


class ChildViewGL(Rectangle):
    def __init__(self, host, child_class, *, height):
        self.state = ChildState(host)
        state = self.state
        self.resources = []
        self.bridge = DrawBridge(self)
        state_before = rng_state()
        ctx = host.camera.ctx
        fbo, viewport = ctx.fbo, ctx.viewport
        try:
            bases = (
                (StepAdapter, child_class, WriterlessScene)
                if child_class is not Scene
                else (StepAdapter, WriterlessScene)
            )
            stepped = type("Stepped" + child_class.__name__, bases, {})
            with isolated_rng(state_before):
                state.child = stepped(state, host)
                state.child_rng = rng_state()
        finally:
            fbo.use()
            ctx.viewport = viewport
        camera = state.child.camera
        for framebuffer in (camera.fbo_for_files, camera.draw_fbo):
            self.resources.extend(
                [*framebuffer.color_attachments, framebuffer.depth_attachment, framebuffer]
            )
        self.image = FrameTexture(camera.fbo.color_attachments[0])
        super().__init__(
            width=height * camera.frame.get_width() / camera.frame.get_height(),
            height=height,
            stroke_opacity=0,
        )
        self.add_updater(lambda mob, dt: None)

    @property
    def child(self):
        return self.state.child

    def update(self, dt=0, recurse=True):
        # Animacja ramki zawiesza updatery; kopie animacji nie krokują dziecka.
        if any(view is self for view in getattr(self.state.host, "_child_views", ())):
            self.state.advance(self.state.host.time)
        return super().update(dt, recurse)

    def get_shader_wrapper(self, ctx):
        self.shader_wrapper = self.bridge
        return self.shader_wrapper

    def draw(self, uniforms):
        if self.state.closed:
            return
        camera = self.child.camera
        ctx = self.state.host.camera.ctx
        # Zapisujemy FBO i viewport przed offscreen; kontekst pozostaje ten sam.
        fbo, viewport = ctx.fbo, ctx.viewport
        flags = (gl.GL_BLEND, gl.GL_DEPTH_TEST, gl.GL_CLIP_DISTANCE0, gl.GL_SCISSOR_TEST)
        enabled = [gl.glIsEnabled(flag) for flag in flags]
        blend = [
            int(gl.glGetIntegerv(key))
            for key in (
                gl.GL_BLEND_SRC_RGB,
                gl.GL_BLEND_DST_RGB,
                gl.GL_BLEND_SRC_ALPHA,
                gl.GL_BLEND_DST_ALPHA,
            )
        ]
        equations = [
            int(gl.glGetIntegerv(key))
            for key in (gl.GL_BLEND_EQUATION_RGB, gl.GL_BLEND_EQUATION_ALPHA)
        ]
        try:
            camera.capture(*self.child.render_groups)
            fbo.use()
            ctx.viewport = viewport
            # Początek FBO jest na dole, odwrotnie niż w ImageMobject.
            self.image.data["point"][:] = self.get_corner_points()
            self.image.data["im_coords"][:] = [(0, 1), (0, 0), (1, 1), (1, 0), (1, 1), (0, 0)]
            self.image.note_changed_data()
            self.image.render(ctx, uniforms)
            ctx.finish()
        finally:
            fbo.use()
            ctx.viewport = viewport
            for flag, value in zip(flags, enabled):
                (gl.glEnable if value else gl.glDisable)(flag)
            gl.glBlendFuncSeparate(*blend)
            gl.glBlendEquationSeparate(*equations)

    def get_corner_points(self):
        from manimlib import DL, DR, UL, UR

        return [self.get_corner(d) for d in (UL, DL, UR, DR, UR, DL)]

    def close(self):
        if self.state.closed:
            return
        try:
            self.state.close()
        finally:
            release_wrappers(self.image)
            for mob in [*self.child.mobjects, *self.child.render_groups]:
                release_wrappers(mob)
            for resource in reversed(self.resources):
                resource.release()
            self.resources.clear()


def release_wrappers(mob):
    for member in mob.get_family():
        wrappers = [member.shader_wrapper, *getattr(member, "shader_wrappers", [])]
        for wrapper in {id(w): w for w in wrappers if w is not None}.values():
            wrapper.release()
        member.shader_wrapper = None
        member.shader_wrappers = []
