"""Zwykła scena jako krokowane dziecko gospodarza, bez importu silników."""

import math
import random
import sys
from contextlib import contextmanager
from functools import wraps

import numpy as np

from manimsceneview.engine import engine_of


def rng_state():
    return random.getstate(), np.random.get_state()


def restore_rng(state):
    random.setstate(state[0])
    np.random.set_state(state[1])


@contextmanager
def isolated_rng(state):
    host_state = rng_state()
    restore_rng(state)
    try:
        yield
    finally:
        restore_rng(host_state)


class ChildState:
    """Wspólny właściciel dziecka i greenleta, także w kopiach animowanej geometrii."""

    def __init__(self, host):
        from greenlet import greenlet

        self.host = host
        self.child = None
        self.closed = False
        self.steps = 0
        self.times = []
        self.last_host_time = None
        self.task = greenlet(self.execute)
        self.child_rng = rng_state()

    def __deepcopy__(self, memo):
        return self

    def execute(self):
        try:
            self.child.setup()
            self.child.construct()
        finally:
            self.child.tear_down()

    def advance(self, host_time):
        if self.closed or self.task.dead or host_time == self.last_host_time:
            return
        self.last_host_time = host_time
        with isolated_rng(self.child_rng):
            try:
                self.task.switch()
            finally:
                self.child_rng = rng_state()

    def close(self):
        from greenlet import GreenletExit

        if self.closed:
            return
        self.closed = True
        with isolated_rng(self.child_rng):
            if not self.task.dead:
                self.task.throw(GreenletExit)


def watch_render_exit(host, close_all):
    """Domknięcie już trwającego renderu, również przy wyjątku między play()."""
    frame = sys._getframe(1)
    while frame is not None:
        if frame.f_locals.get("self") is host and frame.f_code.co_name in ("render", "run"):
            break
        frame = frame.f_back
    if frame is None:
        return
    previous = sys.gettrace()
    previous_local = frame.f_trace
    previous_lines = frame.f_trace_lines

    def on_exit(current, event, arg):
        nonlocal previous_local
        if previous_local is not None:
            previous_local = previous_local(current, event, arg)
        if event == "return":
            sys.settrace(previous)
            current.f_trace = previous_local
            current.f_trace_lines = previous_lines
            close_all()
            return previous_local
        return on_exit

    def on_call(current, event, arg):
        return previous(current, event, arg) if previous is not None else None

    # Jedna aktywna ramka stosu, bez zdarzeń linii i bez podmiany kodu silnika.
    frame.f_trace = on_exit
    frame.f_trace_lines = previous_local is not None and previous_lines
    sys.settrace(on_call)


def register(host, view):
    """Zaczepy na instancji zachowują oryginały, w tym metody klasy autora."""
    if not hasattr(host, "_child_views"):
        host._child_views = []
        original_add = host.add
        original_remove = host.remove
        adding = False
        original_tear_down = host.tear_down

        def close_all():
            from contextlib import ExitStack

            views, host._child_views = host._child_views, []
            with ExitStack() as closing:
                for child_view in views:
                    closing.callback(child_view.close)

        def add(*mobjects):
            nonlocal adding
            previous = adding
            adding = True
            try:
                return original_add(*mobjects)
            finally:
                adding = previous

        def remove(*mobjects):
            removed = {id(member) for mob in mobjects for member in mob.get_family()}
            try:
                for child_view in tuple(host._child_views):
                    if not adding and id(child_view) in removed:
                        child_view.close()
                        host._child_views.remove(child_view)
            finally:
                result = original_remove(*mobjects)
            return result

        def tear_down(*args, **kwargs):
            try:
                close_all()
            finally:
                result = original_tear_down(*args, **kwargs)
            return result

        def finish_render():
            try:
                close_all()
            finally:
                restore_cache = getattr(host, "_child_restore_cache", None)
                if restore_cache is not None:
                    restore_cache()

        def guard(method):
            @wraps(method)
            def guarded(*args, **kwargs):
                try:
                    return method(*args, **kwargs)
                finally:
                    finish_render()

            return guarded

        host.add = add
        host.remove = remove
        host.tear_down = tear_down
        for name in ("render", "run"):
            if hasattr(host, name):
                setattr(host, name, guard(getattr(host, name)))
        watch_render_exit(host, finish_render)
    host._child_views.append(view)


def ChildView(host, child_class, *, height=4.0):
    """Mobject dziecka tego samego silnika, wysokość w jednostkach gospodarza."""
    engine = engine_of(host)
    if not isinstance(child_class, type) or engine_of(child_class) != engine:
        raise TypeError("ChildView host and child_class must use the same Manim engine")
    if getattr(host, "_child_state", None) is not None:
        raise TypeError("Nested ChildView is unsupported")
    if not math.isfinite(height) or height <= 0:
        raise ValueError("ChildView height must be finite and positive")
    # Greenlet oraz silnik importujemy dopiero po walidacji publicznego API.
    if engine == "ce":
        from manimsceneview._child_ce import ChildViewCE

        view = ChildViewCE(host, child_class, height=height)
    else:
        from manimsceneview._child_gl import ChildViewGL

        view = ChildViewGL(host, child_class, height=height)
    register(host, view)
    return view
