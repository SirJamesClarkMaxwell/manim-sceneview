# Contributing

Use Python 3.11 or newer. From the repository root:

```sh
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The `gpu` marker identifies tests requiring a real OpenGL context for manimgl.
`uv run pytest -m "not gpu"` runs only CPU tests; the full release check includes GPU tests.
Documentation blocks and examples execute in tests, including their scene renders.

Run `uv run python tools/examples.py` to regenerate CE MP4s and GIFs beside their code;
add `--gl` for GL movies or a filename substring to select examples. ffmpeg must be on PATH.
Scratch renders go to the ignored `.example-media/` directory. Inspect the resulting media
before submitting changes. Keep README gallery links in sync with numbered examples.

User-facing docs, examples and tools use English. Comments and docstrings inside `src/`
use Polish. Do not include examples, docs, tests or media in package build artifacts.
