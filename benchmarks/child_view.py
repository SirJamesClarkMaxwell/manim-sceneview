"""Pomiar D52: 720p30, 5 s, 20 mobjectów, bez progu wydajności.

Uruchomienie: .venv/Scripts/python.exe benchmarks/child_view.py
Wyniki i logi trafiają do .tmp/child-view-benchmark (albo --output).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter

SCENE = """from ENGINE import BLUE, RED, RIGHT, Circle, Scene, Square, linear
from manimsceneview import ChildView

class Child(Scene):
    def construct(self):
        square = Square(side_length=0.8, fill_color=RED, fill_opacity=1,
                        stroke_width=0).shift(-3 * RIGHT)
        markers = [Circle(radius=0.08, fill_color=BLUE, fill_opacity=1,
                          stroke_width=0).move_to([-5 + i * 0.5, 2, 0])
                   for i in range(19)]
        self.add(square, *markers)
        self.play(square.animate.shift(6 * RIGHT), run_time=5, rate_func=linear)

class Host(Scene):
    def construct(self):
        view = ChildView(self, Child, height=4)
        self.add(view)
        self.wait(5)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".tmp/child-view-benchmark",
    )
    parser.add_argument("--engine", choices=("ce", "gl", "both"), default="both")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for engine in ("ce", "gl") if args.engine == "both" else (args.engine,):
        directory = output / engine
        directory.mkdir(exist_ok=True)
        scene = directory / "benchmark_scene.py"
        scene.write_text(
            SCENE.replace("ENGINE", "manim" if engine == "ce" else "manimlib"),
            encoding="utf-8",
            newline="\n",
        )
        if engine == "gl":
            (directory / "custom_config.yml").write_text(
                f'camera:\n  resolution: "(1280, 720)"\n  fps: 30\n'
                f"directories:\n  cache: {(directory / 'cache').as_posix()}\n",
                encoding="utf-8",
                newline="\n",
            )
        results[engine] = {}
        for name in ("Host", "Child"):
            if engine == "ce":
                command = [
                    sys.executable,
                    "-m",
                    "manim",
                    "render",
                    "-qm",
                    "--disable_caching",
                    str(scene),
                    name,
                ]
            else:
                command = [
                    sys.executable,
                    "-m",
                    "manimlib",
                    str(scene),
                    name,
                    "-w",
                    "--video_dir",
                    str(directory / "videos"),
                ]
            started = perf_counter()
            completed = subprocess.run(
                command,
                cwd=directory,
                capture_output=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                encoding="utf-8",
                errors="replace",
                timeout=600,
                check=False,
            )
            elapsed = perf_counter() - started
            log = completed.stdout + completed.stderr
            (directory / f"{name}.log").write_text(log, encoding="utf-8", newline="\n")
            if completed.returncode:
                raise RuntimeError(f"{engine} {name}: {log}")
            # Sprawdzamy warunki pomiaru, nie jego wydajność.
            import av

            movies = [
                p for p in directory.rglob(f"{name}.mp4") if "partial_movie_files" not in p.parts
            ]
            assert len(movies) == 1, movies
            with av.open(str(movies[0])) as movie:
                stream = movie.streams.video[0]
                assert (stream.width, stream.height) == (1280, 720)
                assert float(stream.average_rate) == 30
                assert sum(1 for _ in movie.decode(stream)) == 150
            results[engine][name] = {"seconds": elapsed, "command": command}
    (output / "result.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8", newline="\n"
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
