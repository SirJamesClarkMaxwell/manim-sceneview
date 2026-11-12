"""Render CE gallery media; optionally render GL variants (without GIFs).

Run from any directory: python tools/examples.py [name] [--gl].
Requires ffmpeg on PATH. Scratch output lives in .example-media/.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / ".example-media"
GIF = (
    "fps=12,scale=640:-1:flags=lanczos,split[a][b];"
    "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5"
    ":diff_mode=rectangle"
)
SCENES = {
    "01_video": "Video",
    "02_playback": "Control",
    "03_grid": "Grid",
    "04_child": "Host",
    "05_sliders": "Sliders",
    "06_scrub": "Scrub",
}


def render(script, scene, gl=False):
    """Render one named scene and return its movie path."""
    if gl:
        MEDIA.mkdir(parents=True, exist_ok=True)
        config = MEDIA / "gl.yml"
        config.write_text(
            f"directories:\n  cache: {(MEDIA / 'cache').as_posix()}\n", encoding="utf-8"
        )
        command = [
            sys.executable,
            "-m",
            "manimlib",
            str(script),
            scene,
            "-w",
            "-m",
            "--config_file",
            str(config),
            "--video_dir",
            str(MEDIA / "gl"),
        ]
    else:
        command = [
            sys.executable,
            "-m",
            "manim",
            "render",
            "-qm",
            "--disable_caching",
            "--progress_bar",
            "none",
            "--media_dir",
            str(MEDIA),
            str(script),
            scene,
        ]
    subprocess.run(command, cwd=ROOT, check=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return (
        MEDIA / "gl" / f"{scene}.mp4"
        if gl
        else MEDIA / "videos" / script.stem / "720p30" / f"{scene}.mp4"
    )


def main():
    """Render the shared clip first, then the selected gallery examples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", default="")
    parser.add_argument("--gl", action="store_true")
    args = parser.parse_args()
    selected = [stem for stem in SCENES if args.name in stem]
    if not selected:
        parser.error("no matching example")
    source = render(ROOT / "examples/clips.py", "Source")
    target = ROOT / "media/videos/clips/720p30/Source.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    for stem in selected:
        script = ROOT / "examples" / f"{stem}.py"
        movie = render(script, SCENES[stem])
        shutil.copyfile(movie, script.with_suffix(".mp4"))
        subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(movie),
                "-vf",
                GIF,
                str(script.with_suffix(".gif")),
            ],
            check=True,
        )
        assert script.with_suffix(".gif").stat().st_size <= 3_000_000, stem
        gl_script = ROOT / "examples/gl" / script.name
        if args.gl and gl_script.exists():
            shutil.copyfile(render(gl_script, SCENES[stem], gl=True), gl_script.with_suffix(".mp4"))


if __name__ == "__main__":
    main()
