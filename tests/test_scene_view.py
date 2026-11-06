"""`SceneView` — klatki gotowego klipu w scenie-gospodarzu (CE i manimgl).

Render gospodarza natywnym rendererem (`manim render`, `manimgl`) w osobnym procesie, próbki
pikseli z klatek wyjścia. Silniki importowane tylko w podprocesach: manimgl przy imporcie parsuje
`sys.argv` i zakończyłby proces pytesta.
"""

import os
import subprocess
import sys
from pathlib import Path

import av
import numpy as np
import pytest

from manimsceneview import FrameSource
from manimsceneview.scene_view import Playback

SCENES_DIR = Path(__file__).parent / "scenes"
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
BLACK = (0, 0, 0)


def segments_clip(path: Path, fps: int = 30) -> Path:
    """2 s: czerwony, zielony, niebieski, biały — po 0,5 s."""
    per = fps // 2
    with av.open(str(path), "w") as out:
        stream = out.add_stream("mpeg4", rate=fps)
        stream.width, stream.height = 64, 36
        stream.pix_fmt = "yuv420p"
        for index in range(4 * per):
            array = np.zeros((36, 64, 3), np.uint8)
            array[:] = COLORS[index // per]
            for packet in stream.encode(av.VideoFrame.from_ndarray(array, format="rgb24")):
                out.mux(packet)
        for packet in stream.encode():
            out.mux(packet)
    return path


def near(actual, expected, tolerance: int = 60) -> bool:
    return all(abs(int(a) - e) <= tolerance for a, e in zip(actual, expected, strict=False))


def python(code: str, clip: Path | None = None, cwd: Path | None = None) -> str:
    if cwd is not None:
        # Także test importu GL potrzebuje zapisywalnego cache poza profilem użytkownika.
        (cwd / "custom_config.yml").write_text(
            f"directories:\n  cache: {(cwd / 'cache').as_posix()}\n", encoding="utf-8"
        )
    env = {**os.environ, "MANIMSCENEVIEW_TEST_CLIP": str(clip or "")}
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout


# --- czas → klatka ------------------------------------------------------------------------


@pytest.mark.parametrize("fps", [24, 60])
def test_frame_source_boundaries_loop_and_seek(tmp_path: Path, fps: int) -> None:
    source = FrameSource(segments_clip(tmp_path / "c.mp4", fps))
    per = fps // 2
    # Granica 0,5 s ± ε: ostatnia klatka czerwieni i pierwsza zieleni.
    assert source.index_at(0.5 - 1e-3) == per - 1
    assert source.index_at(0.5) == per
    assert near(source.rgba(0.5 - 1e-3)[5, 5], COLORS[0])
    assert near(source.rgba(0.5)[5, 5], COLORS[1])
    # Koniec bez pętli: ostatnia klatka; cofnięcie czasu po końcu działa.
    assert near(source.rgba(9.0)[5, 5], COLORS[3])
    assert near(source.rgba(0.1)[5, 5], COLORS[0])
    looped = FrameSource(source.file, loop=True)
    assert near(looped.rgba(2.6)[5, 5], COLORS[1])


def test_playback_clock_pause_seek_and_rate() -> None:
    clock = [10.0]
    playback = Playback(source=None, clock=lambda: clock[0], rate=2.0)
    assert playback.now() == 0  # start przy pierwszym odczycie
    clock[0] = 11.0
    assert playback.now() == 2.0
    playback.pause()
    clock[0] = 15.0
    assert playback.now() == 2.0
    playback.resume()
    clock[0] = 15.5
    assert playback.now() == 3.0
    playback.seek(0.25)
    assert playback.now() == 0.25
    clock[0] = 16.0
    assert playback.now() == 1.25


# --- import i wybór silnika ------------------------------------------------------------------

ENGINE_SCENES = """
import os, sys
from manimsceneview import SceneView
clip = os.environ["MANIMSCENEVIEW_TEST_CLIP"]

def host(base):
    # Bez __init__ sceny: wybór silnika patrzy tylko na klasę, widok czyta `scene.time`
    # (w CE to właściwość renderera — atrybut klasy ją przesłania).
    class Host(base):
        time = 0.0
        def __init__(self):
            pass
    return Host()
"""


def test_import_loads_no_engine() -> None:
    python(
        "import sys, manimsceneview\n"
        "loaded = {name.split('.')[0] for name in sys.modules}\n"
        "bad = loaded & {'manimcue', 'imgui_bundle', 'manim', 'manimlib'}\n"
        "assert not bad, bad\n"
    )


def test_ce_view_does_not_load_manimlib(tmp_path: Path) -> None:
    clip = segments_clip(tmp_path / "clip.mp4")
    python(
        ENGINE_SCENES + "import manim\n"
        "view = SceneView(host(manim.Scene), clip, height=2)\n"
        "assert isinstance(view, manim.ImageMobject)\n"
        "assert 'manimlib' not in sys.modules\n",
        clip,
        tmp_path,
    )


def test_gl_view_does_not_load_manim(tmp_path: Path) -> None:
    clip = segments_clip(tmp_path / "clip.mp4")
    python(
        ENGINE_SCENES + "import manimlib\n"
        "view = SceneView(host(manimlib.Scene), clip, height=2)\n"
        "assert isinstance(view, manimlib.ImageMobject)\n"
        "assert 'manim' not in sys.modules\n",
        clip,
        tmp_path,
    )


def test_engine_detected_with_both_engines_imported(tmp_path: Path) -> None:
    clip = segments_clip(tmp_path / "clip.mp4")
    python(
        ENGINE_SCENES + "import manim, manimlib\n"
        "ce = SceneView(host(manim.Scene), clip)\n"
        "gl = SceneView(host(manimlib.Scene), clip)\n"
        "assert isinstance(ce, manim.ImageMobject) and not isinstance(ce, manimlib.ImageMobject)\n"
        "assert isinstance(gl, manimlib.ImageMobject) and not isinstance(gl, manim.ImageMobject)\n",
        clip,
        tmp_path,
    )


def test_missing_engine_names_the_extras() -> None:
    python(
        "import sys\n"
        "sys.modules['manim'] = sys.modules['manimlib'] = None  # jak bez zainstalowanych silników\n"
        "from manimsceneview import SceneView\n"
        "try:\n"
        "    SceneView(object(), 'clip.mp4')\n"
        "except ImportError as error:\n"
        "    assert 'manim-sceneview[ce]' in str(error) and 'manim-sceneview[gl]' in str(error)\n"
        "else:\n"
        "    raise AssertionError('no ImportError')\n"
    )


def test_non_scene_host_is_a_type_error() -> None:
    python(
        "from manimsceneview import SceneView\n"
        "try:\n"
        "    SceneView(object(), 'clip.mp4')\n"
        "except TypeError as error:\n"
        "    assert 'object' in str(error)\n"
        "else:\n"
        "    raise AssertionError('no TypeError')\n"
    )


# --- render gospodarza ---------------------------------------------------------------------


def render(tmp_path: Path, engine: str, scene: str, clip: Path) -> Path:
    if engine == "ce":
        scene_file = SCENES_DIR / "scene_view_ce.py"
        command = [sys.executable, "-m", "manim", "render", "-ql", str(scene_file), scene]
    else:
        # manimgl czyta custom_config.yml z katalogu roboczego: czarne tło jak w CE,
        # cache poza katalogiem użytkownika.
        cache = (tmp_path / "cache").as_posix()
        (tmp_path / "custom_config.yml").write_text(
            f"camera:\n  background_color: '#000000'\ndirectories:\n  cache: {cache}\n",
            encoding="utf-8",
        )
        scene_file = SCENES_DIR / "scene_view_gl.py"
        command = [sys.executable, "-m", "manimlib", str(scene_file), scene, "-w", "-l"]
        command += ["--video_dir", str(tmp_path / "videos")]
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        env={**os.environ, "MANIMSCENEVIEW_TEST_CLIP": str(clip)},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    outputs = [
        path for path in tmp_path.rglob(f"{scene}.mp4") if "partial_movie_files" not in path.parts
    ]
    assert len(outputs) == 1, outputs
    return outputs[0]


class Clip:
    """Klatki wyjścia gospodarza po czasie i piksel w punkcie sceny (jednostki Manima)."""

    def __init__(self, file: Path) -> None:
        with av.open(str(file)) as container:
            stream = container.streams.video[0]
            self.fps = float(stream.average_rate)
            self.frames = [frame.to_ndarray(format="rgb24") for frame in container.decode(stream)]
        self.height, self.width = self.frames[0].shape[:2]

    def pixel(self, t: float, x: float = 0.0, y: float = 0.0):
        frame = self.frames[min(round(t * self.fps), len(self.frames) - 1)]
        frame_width = 8.0 * self.width / self.height
        px = int((0.5 + x / frame_width) * (self.width - 1))
        py = int((0.5 - y / 8.0) * (self.height - 1))
        return tuple(frame[py, px])


def check_timeline(file: Path) -> None:
    clip = Clip(file)
    red, green, blue = COLORS[:3]
    faded = clip.pixel(0.25)
    assert 50 < faded[0] < 210 and faded[1] < 50 and faded[2] < 50, faded  # FadeIn w połowie
    assert near(clip.pixel(0.75), green)  # zwykłe wait — wideo gra
    # Po przesunięciu i skali widok jest w x = 3, a stare miejsce to tło.
    assert near(clip.pixel(2.25, x=3), red)  # pętla: 2,25 s → 0,25 s klipu
    assert near(clip.pixel(2.25), BLACK)
    assert near(clip.pixel(2.75, x=3), green)
    assert near(clip.pixel(3.25, x=3), blue)  # pauza od 3,0 s → 1,0 s klipu
    # Wznowienie: 3,75 s gospodarza to 1,25 s klipu (pauza nie przesuwa materiału).
    assert near(clip.pixel(3.75, x=3), blue)


def check_two_views(file: Path) -> None:
    clip = Clip(file)
    assert near(clip.pixel(0.25, x=-3), COLORS[0])  # 0,25 s klipu
    assert near(clip.pixel(0.25, x=3), COLORS[2])  # 1,25 s klipu


def test_scene_view_ce_timeline(tmp_path: Path) -> None:
    clip = segments_clip(tmp_path / "clip.mp4")
    check_timeline(render(tmp_path, "ce", "ViewTimingCE", clip))


@pytest.mark.gpu
def test_scene_view_gl_timeline(tmp_path: Path) -> None:
    clip = segments_clip(tmp_path / "clip.mp4")
    check_timeline(render(tmp_path, "gl", "ViewTimingGL", clip))


def test_two_views_ce(tmp_path: Path) -> None:
    clip = segments_clip(tmp_path / "clip.mp4")
    check_two_views(render(tmp_path, "ce", "TwoViewsCE", clip))


@pytest.mark.gpu
def test_two_views_gl(tmp_path: Path) -> None:
    clip = segments_clip(tmp_path / "clip.mp4")
    check_two_views(render(tmp_path, "gl", "TwoViewsGL", clip))


def test_ce_cache_follows_new_source_render(tmp_path: Path) -> None:
    """Nowy render źródła pod tą samą ścieżką: drugi render gospodarza nie bierze starego klipu.

    CE przed `Wait` woła `update_mobjects(0)`, więc hash zawiera klatki widoczne na starcie
    `play()`. Zmieniony jest tylko segment, który prawy widok osiąga dopiero w trakcie `wait` —
    bez klucza źródła w `playback_id` hash byłby ten sam i CE wziąłby stary klip z cache.
    """
    clip = segments_clip(tmp_path / "clip.mp4")
    file = render(tmp_path, "ce", "TwoViewsCE", clip)
    assert near(Clip(file).pixel(0.75, x=3), COLORS[3])  # 1,75 s klipu
    # Identyczny render ma użyć segmentów CE bez ponownego zapisu.
    segments = list((tmp_path / "media").rglob("partial_movie_files/**/*.mp4"))
    assert segments
    stamps = {path: path.stat().st_mtime_ns for path in segments}
    file = render(tmp_path, "ce", "TwoViewsCE", clip)
    assert {path: path.stat().st_mtime_ns for path in segments} == stamps
    assert set((tmp_path / "media").rglob("partial_movie_files/**/*.mp4")) == set(segments)
    assert near(Clip(file).pixel(0.75, x=3), COLORS[3])
    original = COLORS[:]
    COLORS[3] = (0, 255, 0)
    try:
        segments_clip(clip)
        file = render(tmp_path, "ce", "TwoViewsCE", clip)
        assert near(Clip(file).pixel(0.75, x=3), COLORS[3])
    finally:
        COLORS[:] = original
