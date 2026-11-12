"""Execute documentation and example code; substitute only the shared clip path."""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import manimsceneview

ROOT = Path(__file__).resolve().parents[1]
CLIP = "media/videos/clips/720p30/Source.mp4"
FENCE = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)


def cases():
    found = []
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        for index, code in enumerate(FENCE.findall(path.read_text(encoding="utf-8"))):
            found.append(
                pytest.param(
                    code,
                    id=f"{path.stem}-{index}",
                    marks=pytest.mark.gpu if "from manimlib" in code else (),
                )
            )
    for path in sorted((ROOT / "examples").rglob("*.py")):
        code = path.read_text(encoding="utf-8")
        found.append(
            pytest.param(
                code,
                id=path.relative_to(ROOT).as_posix(),
                marks=pytest.mark.gpu if "from manimlib" in code else (),
            )
        )
    return found


def run(command, cwd):
    result = subprocess.run(
        command,
        check=False,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture(scope="session")
def docs_clip(tmp_path_factory):
    directory = tmp_path_factory.mktemp("docs-clip")
    run(
        [
            sys.executable,
            "-m",
            "manim",
            "render",
            "-r",
            "160,90",
            "--fps",
            "6",
            "--disable_caching",
            "--media_dir",
            str(directory),
            str(ROOT / "examples/clips.py"),
            "Source",
        ],
        directory,
    )
    return next(directory.glob("videos/clips/*/Source.mp4"))


@pytest.mark.parametrize("code", cases())
def test_code_runs(code, docs_clip, tmp_path):
    # Keep published paths copy-pasteable; replace only this shared clip with the fixture.
    code = code.replace(CLIP, docs_clip.as_posix())
    tree = ast.parse(code)
    names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    gl = "from manimlib" in code
    # Child scenes are also exercised alone: their host is themselves in this case.
    setup = """
for cls in SCENES:
    original = cls.construct
    def construct(self, original=original):
        if not hasattr(self, "host"):
            self.host = self
        if not hasattr(self, "k"):
            self.k = ValueTracker(0.5)
        original(self)
    cls.construct = construct
"""
    code += "\nfrom " + ("manimlib" if gl else "manim") + " import ValueTracker\n"
    code += "SCENES = [" + ", ".join(names) + "]\n" + setup
    script = tmp_path / "snippet.py"
    if gl:
        script.write_text(code, encoding="utf-8")
        (tmp_path / "custom_config.yml").write_text(
            f"directories:\n  cache: {(tmp_path / 'cache').as_posix()}\n"
            "camera:\n  resolution: '(160, 90)'\n  fps: 6\n",
            encoding="utf-8",
        )
        for name in names:
            run(
                [
                    sys.executable,
                    "-m",
                    "manimlib",
                    str(script),
                    name,
                    "-w",
                    "--video_dir",
                    str(tmp_path / "videos"),
                ],
                tmp_path,
            )
    else:
        code += """
from manim import tempconfig
with tempconfig({"dry_run": True, "disable_caching": True, "pixel_width": 160,
                 "pixel_height": 90, "frame_rate": 6, "progress_bar": "none"}):
    for cls in SCENES:
        cls().render()
"""
        script.write_text(code, encoding="utf-8")
        run([sys.executable, str(script)], tmp_path)


def test_gallery_links_and_coverage():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    gallery = readme.split("## Gallery", 1)[1].split("## Documentation", 1)[0]
    links = re.findall(r'(?:href|src)="([^"]+)"', gallery)
    for link in links:
        relative = link.split("/main/", 1)[-1] if link.startswith("https://") else link
        assert (ROOT / relative).is_file(), link
    for path in (ROOT / "examples").glob("[0-9][0-9]_*.py"):
        for suffix in (".py", ".gif", ".mp4"):
            assert f"examples/{path.stem}{suffix}" in gallery


def test_api_covers_public_names():
    api = (ROOT / "docs/api.md").read_text(encoding="utf-8")
    for name in manimsceneview.__all__:
        assert re.search(rf"\b{name}\b", api)
