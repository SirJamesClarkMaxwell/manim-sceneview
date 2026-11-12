"""Render przykładów i kryteria obrazu 11d/8(b,c), bez importu silników w pytest."""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from test_child_view import ENGINES
from test_scene_view import Clip


@pytest.mark.parametrize("engine", ENGINES)
def test_slider_examples(tmp_path, engine):
    examples = Path(__file__).parents[1] / "examples"
    folder = examples if engine == "ce" else examples / "gl"
    (tmp_path / "custom_config.yml").write_text(
        f"camera:\n  background_color: '#000000'\ndirectories:\n  cache: {(tmp_path / 'cache').as_posix()}\n",
        encoding="utf-8",
    )
    clips = {}
    for name, scene_file in (
        ("Source", examples / "clips.py"),
        ("Sliders", folder / "05_sliders.py"),
        ("Scrub", folder / "06_scrub.py"),
    ):
        render_engine = "ce" if name == "Source" else engine
        command = (
            [sys.executable, "-m", "manim", "render", "-ql", str(scene_file), name]
            if render_engine == "ce"
            else [sys.executable, "-m", "manimlib", str(scene_file), name, "-w", "-l"]
        )
        result = subprocess.run(
            command,
            check=False,
            cwd=tmp_path,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        files = [p for p in tmp_path.rglob(f"{name}.mp4") if "partial_movie_files" not in p.parts]
        assert len(files) == 1, files
        clips[name] = Clip(files[0])
    sliders = clips["Sliders"]
    first, second = (sliders.frames[round(t * sliders.fps)] for t in (0.75, 2.3))
    changes = []
    for left, right in ((0.12, 0.48), (0.52, 0.88)):
        region = np.s_[
            round(sliders.height * 0.33) : round(sliders.height * 0.65),
            round(sliders.width * left) : round(sliders.width * right),
        ]
        changes.append(float(np.abs(first[region].astype(float) - second[region]).mean()))
    assert min(changes) > 1, changes
    source, scrub = clips["Source"], clips["Scrub"]
    frame = scrub.frames[round(4.4 * scrub.fps)]
    # Widok ma wysokość 4, środek y=0,5; kamera gospodarza ma wysokość 8.
    y0, y1 = round(scrub.height * 0.1875), round(scrub.height * 0.6875)
    x0, x1 = round(scrub.width * 0.25), round(scrub.width * 0.75)
    actual = frame[y0:y1, x0:x1]
    actual_mask = (actual[:, :, 0] > 150) & (actual[:, :, 1] < 120) & (actual[:, :, 2] < 120)
    assert actual_mask.sum() > 20
    errors = []
    foreground_errors = []
    distances = []
    for index in (round(source.fps) - 1, round(source.fps), round(source.fps) + 1):
        expected = np.asarray(Image.fromarray(source.frames[index]).resize((x1 - x0, y1 - y0)))
        errors.append(float(np.abs(actual.astype(float) - expected).mean()))
        expected_mask = (
            (expected[:, :, 0] > 150) & (expected[:, :, 1] < 120) & (expected[:, :, 2] < 120)
        )
        assert expected_mask.sum() > 20
        foreground_errors.append(
            float(np.abs(actual.astype(float) - expected)[actual_mask | expected_mask].mean())
        )
        distances.append(
            float(
                np.linalg.norm(
                    np.argwhere(actual_mask).mean(axis=0) - np.argwhere(expected_mask).mean(axis=0)
                )
            )
        )
    best = int(np.argmin(foreground_errors))
    assert errors[best] < 4, errors
    assert foreground_errors[best] < 15, foreground_errors
    assert distances[best] < 2, distances
    print(
        f"{engine}: child region MAE={changes}; scrub MAE={errors[best]:.4f}, "
        f"foreground MAE={foreground_errors[best]:.4f}, displacement={distances[best]:.4f}px"
    )
