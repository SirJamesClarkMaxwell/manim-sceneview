"""Wspólne scenariusze testów; silnik przekazuje wyłącznie moduł sceny."""

import atexit
import gc
import json
import os
import random
import sys
from pathlib import Path

import numpy as np

from manimsceneview import ChildView
from manimsceneview.child_view import rng_state


def same_rng(a, b):
    return (
        a[0] == b[0]
        and a[1][0] == b[1][0]
        and np.array_equal(a[1][1], b[1][1])
        and a[1][2:] == b[1][2:]
    )


def install_cases(namespace, engine, manim):
    Scene = manim.Scene
    Square, Dot, Group = (getattr(manim, name) for name in ("Square", "Dot", "Group"))
    RED, BLUE, RIGHT, UP, linear = (
        getattr(manim, name) for name in ("RED", "BLUE", "RIGHT", "UP", "linear")
    )
    ConfiguredChild = namespace["ConfiguredChild"]
    gc.disable()
    phase = os.environ.get("CHILD_PHASE", "normal")
    output = Path(os.environ["CHILD_RESULT"])

    class Child(ConfiguredChild):
        def setup(self):
            super().setup()
            if phase == "setup":
                raise ValueError("child setup sentinel")

        def construct(self):
            if phase == "construct":
                raise ValueError("child construct sentinel")
            self.elapsed = 0.0
            self.draws = []
            self.square = Square(
                side_length=0.7, fill_color=RED, fill_opacity=1, stroke_width=0
            ).move_to([-2, 0, 0])
            self.add(self.square)

            def tick(mob, dt):
                self.elapsed += dt
                if dt:
                    self.draws.append([random.random(), float(np.random.random())])

            marker = Dot(radius=0.03, fill_color=BLUE).move_to([-3, 2, 0])
            marker.add_updater(tick)
            self.add(marker)
            if phase in ("remove", "interrupt", "unfinished", "host_error"):
                self.wait_until(lambda: False)
                return
            self.play(self.square.animate.shift(4 * RIGHT), run_time=0.73, rate_func=linear)
            self.play(self.square.animate.shift(UP), run_time=0.61, rate_func=linear)
            self.wait(0.47)
            self.wait_until(lambda: self.host.time >= 2.5)
            self.transition = self.host.time
            self.wait(0.4)

        def tear_down(self):
            self.cleaned = True
            super().tear_down()
            if phase == "tear_down":
                raise ValueError("child tear_down sentinel")

    class Host(Scene):
        def construct(self):
            random.seed(42)
            np.random.seed(42)
            self.original_remove_calls = 0
            self.original_teardown_calls = 0
            self.samples = []
            self.rng_ok = True
            self.duplicate_ok = True
            self.host_draws = []
            self.last_rng_time = None
            if engine == "ce":
                self.camera.background_color = "#203050"
            if engine == "gl":
                self.camera.background_rgba[:] = [32 / 255, 48 / 255, 80 / 255, 1]
            if phase == "baseline":
                self.dot = Dot(fill_color=BLUE).move_to([-5, -3, 0])
                self.dot.add_updater(lambda mob, dt: None)
                self.add(self.dot)
                self.play(self.dot.animate.shift(10 * RIGHT), run_time=2, rate_func=linear)
                self.wait(2)
                self.save_result()
                return
            self.cache_before = manim.config.disable_caching if engine == "ce" else None
            self.previous_profile = sys.getprofile()
            self.previous_trace = sys.gettrace()
            before = rng_state()
            self.view = ChildView(self, Child, height=4)
            self.rng_ok &= same_rng(before, rng_state())
            self.cache_during = manim.config.disable_caching if engine == "ce" else None
            if engine == "gl":
                import OpenGL.GL as gl

                self.gl_objects = [
                    (
                        gl.glIsTexture
                        if hasattr(r, "build_mipmaps")
                        else gl.glIsFramebuffer
                        if hasattr(r, "color_attachments")
                        else gl.glIsRenderbuffer,
                        r.glo,
                    )
                    for r in self.view.resources
                ]
            atexit.register(self.save_result)
            self.group = Group(self.view) if phase == "remove" else self.view
            self.add(self.group)
            # Ponowne add w GL używa remove do porządkowania; nie może zamknąć dziecka.
            self.add(self.group)
            writer = self.renderer.file_writer if engine == "ce" else self.file_writer
            original_write = writer.write_frame

            def write_frame(*args, **kwargs):
                child = self.view.child
                camera = child.camera
                scale = self.view.get_height() / (
                    camera.frame_height if engine == "ce" else child.frame.get_height()
                )
                camera_center = camera.frame_center if engine == "ce" else child.frame.get_center()
                world = self.view.get_center() + scale * (child.square.get_center() - camera_center)
                self.samples.append(
                    {
                        "host_time": self.time,
                        "child_time": child.time,
                        "world": world.tolist(),
                        "scale": scale,
                        "center": self.view.get_center().tolist(),
                    }
                )
                return original_write(*args, **kwargs)

            if phase == "normal":
                writer.write_frame = write_frame
            self.dot = Dot(fill_color=BLUE).move_to([-5, -3, 0])
            self.add(self.dot)
            if phase in ("setup", "construct", "tear_down"):
                self.wait(4)
            elif phase == "remove":
                self.wait(0.3)
                self.remove(self.group)
                assert self.view.state.closed and self.view.state.task.dead
                assert not any(
                    self.view is member for mob in self.mobjects for member in mob.get_family()
                )
                self.wait(0.2)
            elif phase in ("interrupt", "unfinished", "host_error"):
                if phase == "interrupt":

                    def interrupt(mob, dt):
                        if self.time >= 0.3:
                            raise KeyboardInterrupt("host interrupt sentinel")

                    self.dot.add_updater(interrupt)
                self.wait(0.6)
                if phase == "host_error":
                    raise RuntimeError("host between plays sentinel")
            else:
                self.play(
                    self.dot.animate.shift(10 * RIGHT),
                    self.view.animate.scale(0.7).shift(RIGHT + UP),
                    run_time=2,
                    rate_func=linear,
                )
                self.wait(2)
                assert self.view.state.task.dead
            self.save_result()

        def update_mobjects(self, dt):
            before = rng_state()
            super().update_mobjects(dt)
            if hasattr(self, "view"):
                self.rng_ok &= same_rng(before, rng_state())
                state = self.view.state
                old = state.steps
                state.advance(self.time)
                self.duplicate_ok &= old == state.steps
            if hasattr(self, "host_draws") and self.time != self.last_rng_time:
                self.last_rng_time = self.time
                for _ in range(int(os.environ.get("CHILD_HOST_DRAWS", "1"))):
                    self.host_draws.append([random.random(), float(np.random.random())])

        def remove(self, *mobjects):
            self.original_remove_calls = getattr(self, "original_remove_calls", 0) + 1
            return super().remove(*mobjects)

        def tear_down(self):
            self.original_teardown_calls += 1
            self.save_result()
            return super().tear_down()

        def save_result(self):
            if not hasattr(self, "view"):
                output.write_text(json.dumps({"host_draws": self.host_draws}), encoding="utf-8")
                return
            view = self.view
            child, state = view.child, view.state
            camera = child.camera
            result = {
                "engine": engine,
                "phase": phase,
                "steps": state.steps,
                "times": state.times,
                "child_time": child.time,
                "elapsed": getattr(child, "elapsed", 0),
                "transition": getattr(child, "transition", None),
                "fps": self.camera.frame_rate if engine == "ce" else self.camera.fps,
                "closed": state.closed,
                "dead": state.task.dead,
                "cleaned": getattr(child, "cleaned", False),
                "rng_ok": self.rng_ok,
                "duplicate_ok": self.duplicate_ok,
                "draws": getattr(child, "draws", []),
                "host_draws": self.host_draws,
                "samples": self.samples,
                "child_writer": hasattr(child.renderer if engine == "ce" else child, "file_writer"),
                "camera_height": camera.frame_height
                if engine == "ce"
                else child.frame.get_height(),
                "camera_center": list(
                    camera.frame_center if engine == "ce" else child.frame.get_center()
                ),
                "camera_background": (
                    camera.background_color.to_hex()
                    if engine == "ce"
                    else camera.background_rgba[:3]
                ),
                "camera_alpha": camera.background_opacity
                if engine == "ce"
                else camera.background_rgba[3],
                "cache_before": self.cache_before,
                "cache_during": self.cache_during,
                "cache_after": manim.config.disable_caching if engine == "ce" else None,
                "resources": len(getattr(view, "resources", [])),
                "gpu_released": (
                    not any(check(name) for check, name in self.gl_objects)
                    if engine == "gl" and state.closed
                    else None
                ),
                "profile_restored": sys.getprofile() is self.previous_profile,
                "trace_restored": sys.gettrace() is self.previous_trace,
                "remove_calls": self.original_remove_calls,
                "teardown_calls": self.original_teardown_calls,
                "other_engine_loaded": ("manimlib" if engine == "ce" else "manim") in sys.modules,
            }
            output.write_text(json.dumps(result, default=float), encoding="utf-8", newline="\n")

    # Natywne loadery wybierają klasy zadeklarowane w module pliku wejściowego.
    for name, cls in (("Child", Child), ("Host", Host)):
        cls.__module__ = namespace["__name__"]
        namespace[name] = cls
