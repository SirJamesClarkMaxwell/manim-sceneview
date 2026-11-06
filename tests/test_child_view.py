"""Kryteria D52: natywne rendery CE i GL w podprocesach, bez importu GL w pytest."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from test_scene_view import Clip, near, python

SCENES = Path(__file__).parent / "scenes"
ENGINES = ["ce", pytest.param("gl", marks=pytest.mark.gpu)]


def render(directory, engine, phase="normal", draws=1):
    directory.mkdir(parents=True, exist_ok=True)
    result_file = directory / "result.json"
    scene_file = SCENES / f"child_view_{engine}.py"
    if engine == "ce":
        command = [sys.executable, "-m", "manim", "render", "-ql", str(scene_file), "Host"]
    else:
        (directory / "custom_config.yml").write_text(
            f"directories:\n  cache: {(directory / 'cache').as_posix()}\n",
            encoding="utf-8",
            newline="\n",
        )
        command = [
            sys.executable,
            "-m",
            "manimlib",
            str(scene_file),
            "Host",
            "-w",
            "-l",
            "--video_dir",
            str(directory / "videos"),
        ]
    process = subprocess.run(
        command,
        cwd=directory,
        env={
            **os.environ,
            "CHILD_RESULT": str(result_file),
            "CHILD_PHASE": phase,
            "CHILD_HOST_DRAWS": str(draws),
            "PYTHONIOENCODING": "utf-8",
        },
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    log = process.stdout + process.stderr
    assert result_file.exists(), log
    result = json.loads(result_file.read_text(encoding="utf-8"))
    if phase in ("setup", "construct", "tear_down"):
        assert process.returncode != 0, log
        assert f"child {phase} sentinel" in log and "Traceback" in log, log
        assert "child_view_cases.py" in log, log
    elif phase in ("interrupt", "host_error"):
        assert process.returncode != 0 or (phase == "interrupt" and engine == "gl"), log
    else:
        assert process.returncode == 0, log
    files = [p for p in directory.rglob("Host.mp4") if "partial_movie_files" not in p.parts]
    return result, files, log


@pytest.fixture(scope="module", params=ENGINES)
def rendered(request, tmp_path_factory):
    engine = request.param
    directory = tmp_path_factory.mktemp(f"child-{engine}")
    result, files, log = render(directory, engine)
    assert len(files) == 1, files
    return engine, directory, result, Clip(files[0]), log


def test_01_steps_without_child_files(rendered):
    _, directory, result, clip, _ = rendered
    assert abs(result["steps"] - result["fps"] * result["child_time"]) <= 1
    assert not result["child_writer"]
    assert not result["other_engine_loaded"]
    assert not any("Stepped" in str(p) or p.name == "Child.mp4" for p in directory.rglob("*"))
    assert len(clip.frames) == round(4 * result["fps"])


def test_02_parallel_pixels(rendered):
    engine, _, result, clip, _ = rendered
    assert len(result["samples"]) == len(clip.frames)
    for index in (3, 8, 15, 25, len(clip.frames) - 2):
        sample = result["samples"][index]
        image = clip.frames[index]
        mask = (image[:, :, 0] > 180) & (image[:, :, 1] < 110) & (image[:, :, 2] < 110)
        ys, xs = np.nonzero(mask)
        assert len(xs), (index, sample)
        world = sample["world"]
        expected = [
            clip.width * (0.5 + world[0] / (8 * clip.width / clip.height)),
            clip.height * (0.5 - world[1] / 8),
        ]
        assert np.linalg.norm(np.array([xs.mean(), ys.mean()]) - expected) < 4, (index, sample)
        host_t = sample["host_time"] - (1 / result["fps"] if engine == "ce" else 0)
        host_x = -5 + 10 * min(host_t / 2, 1)
        assert near(clip.pixel(index / clip.fps, x=host_x, y=-3), (88, 196, 221), tolerance=45)
        # Pozycja raportowana przez dziecko zgadza się także z analityczną trajektorią.
        t = sample["child_time"]
        first_end = np.ceil(0.73 * result["fps"]) / result["fps"]
        child_x = -2 + 4 * min(t / 0.73, 1)
        child_y = min(max(t - first_end, 0) / 0.61, 1)
        expected_world = np.array(sample["center"]) + sample["scale"] * (
            np.array([child_x, child_y, 0]) - result["camera_center"]
        )
        assert np.allclose(world, expected_world), (index, sample, expected_world)


def test_03_frame_and_transparency(rendered):
    _, _, result, clip, _ = rendered
    assert result["samples"][0]["scale"] > result["samples"][-1]["scale"]
    assert result["samples"][-1]["center"][0] == pytest.approx(1)
    assert near(clip.pixel(3.5, x=-1, y=-0.3), (32, 48, 80), tolerance=8)
    assert near(clip.pixel(3.5, x=-4, y=0), (32, 48, 80), tolerance=8)


def test_04_wait_until(rendered):
    result = rendered[2]
    assert abs(result["transition"] - 2.5) <= 1 / result["fps"] + 1e-8


def test_05_clock_and_dt(rendered):
    result = rendered[2]
    assert result["duplicate_ok"]
    assert np.allclose(np.diff([0, *result["times"]]), 1 / result["fps"])
    assert result["times"][0] == pytest.approx(1 / result["fps"])
    assert result["elapsed"] == pytest.approx(result["child_time"])
    assert result["times"][-1] == pytest.approx(result["child_time"])


def test_06_rng(rendered, tmp_path):
    engine, _, result, _, _ = rendered
    alternate, _, _ = render(tmp_path, engine, draws=3)
    assert result["rng_ok"] and alternate["rng_ok"]
    assert result["draws"] == alternate["draws"]
    baseline, _, _ = render(tmp_path / "baseline", engine, phase="baseline")
    assert result["host_draws"] == baseline["host_draws"]


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize(
    "phase", ["setup", "construct", "tear_down", "remove", "interrupt", "unfinished", "host_error"]
)
def test_07_lifecycle(tmp_path, engine, phase):
    result, files, _ = render(tmp_path, engine, phase)
    assert result["closed"] and result["dead"]
    assert result["profile_restored"] and result["trace_restored"]
    assert result["resources"] == 0
    if engine == "gl":
        assert result["gpu_released"]
    assert result["cleaned"]
    if phase in ("remove", "unfinished"):
        assert result["teardown_calls"] == 1
    if phase == "remove":
        assert result["remove_calls"] > 0
        clip = Clip(files[0])
        assert near(clip.pixel(0.4), (32, 48, 80), tolerance=8)


def test_08_host_wait_and_final_image(rendered):
    _, _, result, clip, _ = rendered
    assert result["closed"] and result["dead"] and result["cleaned"]
    assert result["samples"][-1]["child_time"] == result["samples"][-5]["child_time"]
    assert any(sample["child_time"] > 2 for sample in result["samples"] if sample["host_time"] > 2)
    sample = result["samples"][-1]
    assert near(clip.pixel(3.9, *sample["world"][:2]), (252, 98, 85), tolerance=60)


def test_09_configured_camera(rendered):
    result = rendered[2]
    assert result["camera_height"] == pytest.approx(6)
    assert result["camera_center"] == pytest.approx([1, 0, 0])
    assert result["camera_alpha"] == 0
    if result["engine"] == "ce":
        assert result["camera_background"] == "#00FF00"
    else:
        assert result["camera_background"] == [0, 1, 0]


def test_10_cache(rendered):
    engine, directory, result, clip, log = rendered
    if engine == "gl":
        assert "Using cached data" not in log
        return
    assert log.count("UserWarning: ChildView disables the CE host render cache") == 1
    assert result["cache_during"]
    assert result["cache_before"] == result["cache_after"]
    stamps = {p: p.stat().st_mtime_ns for p in directory.rglob("uncached_*.mp4")}
    assert stamps
    second, files, log = render(directory, engine)
    assert second["steps"] == result["steps"]
    assert second["draws"] == result["draws"]
    assert "Using cached data" not in log
    assert all(path.stat().st_mtime_ns > stamp for path, stamp in stamps.items())
    assert np.array_equal(Clip(files[0]).frames[-1], clip.frames[-1])


@pytest.mark.parametrize("engine", ENGINES)
def test_12_readme(engine):
    text = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
    assert "ChildView(self, Child" in text
    assert ("from manim import" if engine == "ce" else "from manimlib import") in text
    for term in (
        "MovingCameraScene",
        "ThreeDScene",
        "between",
        "nested",
        "audio",
        "sections",
        "cache",
    ):
        assert term in text


def test_factory_validation_and_lazy_import(tmp_path):
    (tmp_path / "custom_config.yml").write_text(
        f"directories:\n  cache: {(tmp_path / 'cache').as_posix()}\n", encoding="utf-8"
    )
    python(
        """
import sys
from manimsceneview import ChildView
assert 'greenlet' not in sys.modules
import manim, manimlib
host = object.__new__(manim.Scene)
for child in (manimlib.Scene, object):
    try:
        ChildView(host, child)
    except TypeError:
        pass
    else:
        raise AssertionError('mixed engines accepted')
for height in (0, -1, float('nan'), float('inf')):
    try:
        ChildView(host, manim.Scene, height=height)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid height accepted')
""",
        cwd=tmp_path,
    )


def test_render_exit_preserves_trace_and_profiler():
    python("""
import cProfile
import sys
from manimsceneview.child_view import watch_render_exit

closed = []
events = []
def trace(frame, event, arg):
    events.append(event)
    return trace

class Host:
    def render(self, fail):
        watch_render_exit(self, lambda: closed.append(fail))
        if fail:
            raise RuntimeError('host sentinel')
        return 7

profiler = cProfile.Profile()
profiler.enable()
profile = sys.getprofile()
sys.settrace(trace)
try:
    assert Host().render(False) == 7
    assert sys.gettrace() is trace and sys.getprofile() is profile
    try:
        Host().render(True)
    except RuntimeError:
        pass
    else:
        raise AssertionError('no host exception')
    assert closed == [False, True]
    assert sys.gettrace() is trace and sys.getprofile() is profile
    assert events
finally:
    sys.settrace(None)
    profiler.disable()
""")
